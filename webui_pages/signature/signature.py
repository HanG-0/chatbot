import streamlit as st
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY
from PIL import Image
import io

from streamlit.elements.image import PILImage

from webui_pages.record_out import ApiRequest
from server.db.database_manager import (
    create_case_progress,
    check_user_signed,
    get_user_info,
    get_db_manager
)

def read_inform_template():
    """读取诉前调解告知书模板"""
    template_path = os.path.join("docs", "诉前调解告知书.md")
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

def format_inform_content(username, user_info):
    """格式化告知书内容"""
    template = read_inform_template()

    # 获取用户信息
    debt_project = user_info[5] if user_info and len(user_info) > 5 else "工商银行"
    current_date = datetime.now()
    month = current_date.month
    day = current_date.day

    # 替换模板中的变量
    content = template.replace("{username}", username)
    content = content.replace("{debt_project}", debt_project)
    content = content.replace("{month}", str(month))
    content = content.replace("{day}", str(day))

    return content

def generate_pdf(username, signature_image, user_info):
    """生成PDF文件"""
    db_manager = get_db_manager()
    
    # 生成文件名：用户名-年月日.pdf
    current_date = datetime.now()
    filename = f"{username}-{current_date.year}{current_date.month}{current_date.day}.pdf"
    filepath = os.path.join("contracts", filename)
    
    # 保存签名图片用于页面显示
    # 文件命名格式：username-年-月-日-image.png
    signature_filename = f"{username}-{current_date.year}-{current_date.month}-{current_date.day}-image.png"
    signature_filepath = os.path.join("contracts", "images", signature_filename)
    
    # 确保目录存在
    os.makedirs("contracts", exist_ok=True)
    os.makedirs(os.path.join("contracts", "images"), exist_ok=True)
    
    # 保存签名图片
    if signature_image:
        if signature_image.mode != 'RGB':
            signature_image = signature_image.convert('RGB')
        signature_image.save(signature_filepath)

    # 确保contracts目录存在
    os.makedirs("contracts", exist_ok=True)

    # 创建PDF文档
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)

    # 注册中文字体 - 尝试多种字体路径
    font_registered = False
    font_name = 'Helvetica'
    
    # 尝试的字体路径
    font_paths = [
        ('SimSun', 'SimSun.ttf'),
        ('SimSun', '/System/Library/Fonts/PingFang.ttc'),
        ('STSong', '/System/Library/Fonts/STHeiti Light.ttc'),
        ('STSong', '/System/Library/Fonts/STHeiti Medium.ttc'),
        ('STSong', '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'),
        ('STSong', 'C:/Windows/Fonts/simsun.ttc'),
        ('STSong', 'C:/Windows/Fonts/msyh.ttc'),
    ]
    
    for name, path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            font_name = name
            font_registered = True
            print(f"成功注册字体: {name} from {path}")
            break
        except Exception as e:
            print(f"字体注册失败 {path}: {e}")
            continue
    
    if not font_registered:
        print("Warning: 无法注册中文字体，使用默认字体")
    
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    if font_registered:
        style_normal.fontName = font_name
    style_normal.fontSize = 12
    style_normal.alignment = TA_JUSTIFY
    style_normal.leading = 20

    content = []

    # 添加告知书内容
    inform_text = format_inform_content(username, user_info)

    # 将markdown内容转换为纯文本并分块
    lines = inform_text.split('\n')
    for line in lines:
        if line.strip():
            if line.startswith('# '):
                # 标题
                style_heading = styles['Heading1']
                if font_registered:
                    style_heading.fontName = font_name
                style_heading.fontSize = 18
                content.append(Paragraph(line[2:], style_heading))
                content.append(Spacer(1, 0.5*cm))
            elif line.startswith('## '):
                # 副标题
                style_heading = styles['Heading2']
                if font_registered:
                    style_heading.fontName = font_name
                style_heading.fontSize = 14
                content.append(Paragraph(line[3:], style_heading))
                content.append(Spacer(1, 0.3*cm))
            elif line.startswith('    ') or line.startswith('\t'):
                # 缩进内容
                content.append(Paragraph(line.strip(), style_normal))
            else:
                # 普通段落
                content.append(Paragraph(line, style_normal))
        else:
            content.append(Spacer(1, 0.2*cm))

    # 添加签名区域
    content.append(Spacer(1, 1*cm))
    
    # 添加签名图片
    if signature_image:
        try:
            # 将签名图片转换为字节流（避免临时文件问题）
            from io import BytesIO
            
            # 创建字节流对象
            img_buffer = BytesIO()
            
            # 确保图片是RGB模式
            if signature_image.mode == 'RGBA':
                # 创建白色背景
                rgb_image = PILImage.new('RGB', signature_image.size, (255, 255, 255))
                rgb_image.paste(signature_image, mask=signature_image.split()[3])  # 使用alpha通道作为mask
                signature_image = rgb_image
            elif signature_image.mode != 'RGB':
                signature_image = signature_image.convert('RGB')
            
            # 保存到字节流
            signature_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)  # 重置指针到开头
            
            # 计算图片尺寸
            img_width = 4 * cm
            img_height = (signature_image.size[1] / signature_image.size[0]) * img_width
            
            # 使用字节流创建PDF图片
            from reportlab.platypus import Image as PDFImage
            pdf_img = PDFImage(img_buffer, width=img_width, height=img_height)
            content.append(pdf_img)
            
        except Exception as e:
            print(f"添加签名图片失败：{e}")
            # 即使签名图片添加失败，也继续生成PDF
            pass

    # 添加签署日期
    current_date = datetime.now()
    date_str = f"签署日期：{current_date.year}年{current_date.month}月{current_date.day}日"
    content.append(Paragraph(date_str, style_normal))

    # 生成PDF
    try:
        doc.build(content)
    except Exception as e:
        print(f"PDF生成错误：{e}")
        raise
    
    # 保存到数据库
    create_case_progress(username, "S0", filepath,signature_filepath, db_manager)
    
    return filepath

def signature_page(api: ApiRequest, is_lite: bool = None):
    """签名页面"""
    st.markdown('<h2 style="text-align: center;">诉前调解告知书</h2>', unsafe_allow_html=True)

    username = st.session_state.username

    # 检查用户是否已签署
    if check_user_signed(username):
        st.success("您已经开始调解流程")

        # 显示已签署的PDF
        user_info = get_user_info(username)
        
        # 从数据库获取最新的案件进度记录
        from server.db.database_manager import get_case_progress
        progress = get_case_progress(username)
        
        # 数据库字段顺序：id, user_id, status, contract_file, created_at, updated_at
        # contract_file 在索引3的位置
        if progress and progress[3]:
            filepath = progress[3]
            filename = os.path.basename(filepath)
        else:
            current_date = datetime.now()
            filename = f"{username}-{current_date.year}{current_date.month}{current_date.day}.pdf"
            filepath = os.path.join("contracts", filename)

        if os.path.exists(filepath):
            with open(filepath, "rb") as pdf_file:
                st.download_button(
                    label="下载已签署的告知书",
                    data=pdf_file,
                    file_name=filename,
                    mime="application/pdf"
                )

        # 显示内容
        st.markdown("---")
        user_info = get_user_info(username)
        inform_content = format_inform_content(username, user_info)
        st.markdown(inform_content)
        
        # 显示签名
        st.markdown("---")
        st.markdown('<h3 style="text-align: center;">您的签名</h3>', unsafe_allow_html=True)
        
        # 查找签名图片，使用新的命名规则：username-年-月-日-image.png
        import glob
        signature_pattern = os.path.join("contracts", "images", f"{username}-*-image.png")
        signature_files = glob.glob(signature_pattern)
        
        if signature_files:
            # 获取最新的签名文件
            latest_signature = max(signature_files, key=os.path.getmtime)
            st.image(latest_signature, width=400)
        else:
            st.info("签名图片未找到")
        
        return

    # 获取用户信息
    user_info = get_user_info(username)

    # 显示告知书内容
    with st.container():
        inform_content = format_inform_content(username, user_info)
        st.markdown(inform_content)

    st.markdown("---")

    # 签名区域
    st.markdown('<h3 style="text-align: center;">请在下方签名</h3>', unsafe_allow_html=True)

    # 使用 streamlit-drawable-canvas 组件
    from streamlit_drawable_canvas import st_canvas

    # 设置画布
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        background_image=None,
        update_streamlit=True,
        height=150,
        width=600,
        drawing_mode="freedraw",
        point_display_radius=0,
        key="canvas",
    )

    # 确认按钮
    if st.button("确认签署", type="primary"):
        if canvas_result.image_data is not None:
            try:
                # 获取签名图片
                import numpy as np
                from PIL import Image as PILImage

                # 将image_data转换为PIL Image
                image_data = canvas_result.image_data
                signature_image = PILImage.fromarray(image_data.astype('uint8'))

                # 转换为RGB模式（去除透明度）
                if signature_image.mode == 'RGBA':
                    signature_image = signature_image.convert('RGB')

                # 生成PDF
                generate_pdf(username, signature_image, user_info)

                st.success("签署成功！您已经开始调解流程")
                st.rerun()

            except Exception as e:
                st.error(f"签署失败：{str(e)}")
        else:
            st.warning("请先签名再确认")
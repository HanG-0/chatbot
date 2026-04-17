from __future__ import annotations
import os
import sys
from datetime import datetime
from typing import Optional
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from PIL import Image as PILImage
from io import BytesIO
from pydantic import BaseModel, Field

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from server.db.database_manager import (
    create_repayment_plan,
    update_repayment_plan,
    get_user_info,
    get_db_manager
)


class SignMediationAgreementInput(BaseModel):
    """Input schema for the mediation agreement signing tool - 完全兼容版本"""
    # 用户ID - 支持多种字段名
    user_name: str = Field(None, description="Username or borrower name (用户名或借款人姓名)")
    
    # 调解方案 - 支持多种字段名
    repayment_plan: str = Field(None, description="Specific mediation plan (具体调解方案)")
    mediation_plan: Optional[str] = Field(None, description="Mediation plan (调解方案)")
    
    # 金额相关 - 支持多种字段名
    down_payment_amount: float = Field(None, description="Down payment (首付)")
    
    # 分期相关 - 支持多种字段名
    installment_amount: float = Field(None, description="Installment amount (每期还款金额)")
    installment_period: int = Field(None, description="Installment period (分期数)")
    


def number_to_chinese(num):
    """将数字金额转换为中文大写"""
    if not num:
        return "零元整"
    
    try:
        num = float(num)
        integer_part = int(num)
        decimal_part = int(round((num - integer_part) * 100))
        
        digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
        units = ['', '拾', '佰', '仟', '万', '拾', '佰', '仟', '亿']
        
        if integer_part == 0:
            integer_str = "零"
        else:
            integer_str = ""
            for i, digit in enumerate(str(integer_part)):
                digit = int(digit)
                pos = len(str(integer_part)) - i - 1
                if digit != 0:
                    integer_str = digits[digit] + units[pos] + integer_str
                elif integer_str[-1] != '零':
                    integer_str += digits[digit]
        
        if decimal_part == 0:
            decimal_str = "整"
        else:
            decimal_str = f"{digits[decimal_part // 10]}角{digits[decimal_part % 10]}分"
        
        return f"{integer_str}元{decimal_str}"
    except:
        return f"{num}元整"


def read_agreement_template():
    """读取金融纠纷调解协议书模板"""
    template_path = os.path.join("docs", "金融纠纷调解协议书.md")
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


def format_agreement_content(user_id, user_info, repayment_plan_data):
    """格式化协议书内容"""
    template = read_agreement_template()
    
    # 获取当前日期
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    
    # 从user_info获取基本信息
    username = user_info[0] if user_info else user_id
    id_card = user_info[7] if user_info and len(user_info) > 7 and user_info[7] else "************"
    phone = user_info[3] if user_info and len(user_info) > 3 and user_info[3] else "***********"
    
    # 获取债务信息，确保都是 Decimal 类型
    loan_amount = Decimal(str(user_info[9])) if user_info and len(user_info) > 9 and user_info[9] is not None else Decimal('0.00')
    total_interest = Decimal(str(user_info[10])) if user_info and len(user_info) > 10 and user_info[10] is not None else Decimal('0.00')
    total_penalty = Decimal(str(user_info[11])) if user_info and len(user_info) > 11 and user_info[11] is not None else Decimal('0.00')
    total_debt = user_info[4] if user_info and len(user_info) > 4 and user_info[4] is not None else Decimal('0.00')
    debt_reason = user_info[8] if user_info and len(user_info) > 8 and user_info[8] else ""
    
    # 生成协议编号
    contract_no = f"NJ{year}{month:02d}{day:02d}{username[:3].upper()}001"
    
    # 将还款计划转换为文本格式
    repayment_plan_text = repayment_plan_data.get('repayment_plan', '')
    
    # 构建还款方案详情
    plan_details = []
    down_payment = repayment_plan_data.get('down_payment_amount')
    if down_payment:
        plan_details.append(f"- 首付金额：人民币{down_payment:.2f}元（于协议签署后3个工作日内支付）")
    
    installment_count = repayment_plan_data.get('installment_count')
    installment_amount = repayment_plan_data.get('installment_amount')
    if installment_count and installment_amount:
        plan_details.append(f"- 分期还款：{installment_count}期，每期人民币{installment_amount:.2f}元（自首期起，每月30日支付）")
    
    if plan_details:
        repayment_plan_text += "\n\n" + "\n".join(plan_details)
    
    # 替换模板变量
    content = template.replace("{contract_no}", contract_no)
    content = content.replace("{username}", username)
    content = content.replace("{id_card}", id_card)
    content = content.replace("{phone}", phone)
    content = content.replace("{year}", str(year))
    content = content.replace("{month}", str(month))
    content = content.replace("{day}", str(day))
    content = content.replace("{loan_amount}", str(loan_amount))
    content = content.replace("{total_interest}", str(total_interest))
    content = content.replace("{total_penalty}", str(total_penalty))
    content = content.replace("{total_debt}", str(total_debt))
    content = content.replace("{loan_amount_upper_case}", number_to_chinese(loan_amount))
    content = content.replace("{debt_reason}", debt_reason)
    content = content.replace("{repayment_plan}", repayment_plan_text)
    
    return content, contract_no


def find_signature_image(user_id):
    """查找用户的签名图片"""
    import glob
    
    # 查找签名图片：contracts/images/{username}-*-image.png
    signature_pattern = os.path.join("contracts", "images", f"{user_id}-*-image.png")
    signature_files = glob.glob(signature_pattern)
    
    if signature_files:
        # 获取最新的签名文件
        latest_signature = max(signature_files, key=os.path.getmtime)
        return latest_signature
    return None


def generate_pdf_with_signature(username, agreement_text, signature_image_path=None):
    """生成带签名的PDF文件"""
    current_date = datetime.now()
    filename = f"{username}-调解协议-{current_date.year}{current_date.month}{current_date.day}.pdf"
    filepath = os.path.join("contracts", "repayment", filename)
    
    # 确保目录存在
    os.makedirs("contracts", exist_ok=True)
    os.makedirs(os.path.join("contracts", "repayment"), exist_ok=True)
    
    # 注册中文字体
    font_registered = False
    font_name = 'Helvetica'
    
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
            break
        except:
            continue
    
    # 创建PDF文档
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    if font_registered:
        style_normal.fontName = font_name
    style_normal.fontSize = 11
    style_normal.alignment = TA_JUSTIFY
    style_normal.leading = 16
    
    style_heading = styles['Heading1']
    if font_registered:
        style_heading.fontName = font_name
    style_heading.fontSize = 16
    
    style_heading2 = styles['Heading2']
    if font_registered:
        style_heading2.fontName = font_name
    style_heading2.fontSize = 14
    
    # PDF内容元素列表
    pdf_elements = []
    
    # 将markdown内容转换为PDF元素
    lines = agreement_text.split('\n')
    in_table = False
    table_data = []
    
    for line in lines:
        if line.strip():
            if line.startswith('# '):
                # 主标题
                heading_text = line[2:].replace('**', '')
                pdf_elements.append(Paragraph(heading_text, style_heading))
                pdf_elements.append(Spacer(1, 0.3*cm))
            elif line.startswith('## '):
                # 副标题
                heading_text = line[3:].replace('**', '')
                pdf_elements.append(Paragraph(heading_text, style_heading2))
                pdf_elements.append(Spacer(1, 0.2*cm))
            elif line.startswith('|'):
                # 表格行
                if not in_table:
                    in_table = True
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                table_data.append(cells)
            elif line.startswith('---'):
                continue
            elif line.startswith('-') and not line.startswith('**'):
                # 列表项
                list_text = line[1:].strip()
                pdf_elements.append(Paragraph(f"• {list_text}", style_normal))
            else:
                # 普通段落
                if in_table:
                    # 表格结束，创建表格
                    in_table = False
                    if len(table_data) >= 2:
                        table = Table(table_data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), font_name if font_registered else 'Helvetica'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ]))
                        pdf_elements.append(table)
                        pdf_elements.append(Spacer(1, 0.3*cm))
                    table_data = []
                
                # 去除markdown格式
                clean_line = line.replace('**', '').strip()
                if clean_line:
                    pdf_elements.append(Paragraph(clean_line, style_normal))
                    pdf_elements.append(Spacer(1, 0.1*cm))
        else:
            pdf_elements.append(Spacer(1, 0.2*cm))
    
    # 处理最后可能的表格
    if in_table and len(table_data) >= 2:
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name if font_registered else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        pdf_elements.append(table)
        pdf_elements.append(Spacer(1, 0.3*cm))
    
    # 添加签名
    if signature_image_path and os.path.exists(signature_image_path):
        pdf_elements.append(Spacer(1, 0.5*cm))
        pdf_elements.append(Paragraph("签署页", style_heading2))
        pdf_elements.append(Spacer(1, 0.3*cm))
        
        try:
            sig_img = PILImage.open(signature_image_path)
            img_width = 5 * cm
            img_height = (sig_img.size[1] / sig_img.size[0]) * img_width
            
            from reportlab.platypus import Image as PDFImage
            pdf_img = PDFImage(signature_image_path, width=img_width, height=img_height)
            pdf_elements.append(pdf_img)
        except Exception as e:
            print(f"添加签名图片失败：{e}")
    
    # 生成PDF
    try:
        doc.build(pdf_elements)
        return filepath
    except Exception as e:
        print(f"PDF生成错误：{e}")
        raise


def sign_mediation_agreement(
    user_name: str = None,
    repayment_plan: str = None,
    down_payment_amount: float = None,
    installment_amount: float = None,
    installment_period: int = None,
) -> str:
    """
    调解协议签署与归档工具（完全兼容版本）
    
    功能描述：在用户完成首付或达成一致后，自动生成具有法律效力的《金融纠纷调解协议书》。
    
    输入参数（完全灵活，支持多种字段名）：
    - user_id/username: 用户ID或用户名
    - repayment_plan/mediation_plan: 调解方案
    - amount/total_debt: 总欠款金额
    - first_payment/down_payment: 首付金额
    - installment_amount: 每期还款金额
    - installment_period: 分期数
    - party_a: 甲方姓名
    - party_b/source: 乙方名称或欠款来源
    - reason: 欠款原因
    - overdue_days: 逾期天数
    
    返回结果：
    - 协议书文本内容
    """
    
    try:
        # 确定用户ID
        final_user_id = user_name
        if not final_user_id:
            return "错误：必须提供user_id或user_name参数"
        
        # 确定调解方案
        final_repayment_plan = repayment_plan
        
        # 确定首付
        final_down_payment = down_payment_amount
        
        # 获取数据库管理器
        db_manager = get_db_manager()
        
        # 获取用户信息
        user_info = get_user_info(final_user_id, db_manager)
        if not user_info:
            return f"错误：无法找到用户 {final_user_id} 的信息"
        
        # 构建还款计划数据
        repayment_plan_data = {
            'repayment_plan': final_repayment_plan or "已达成调解协议",
            'down_payment_amount': final_down_payment,
            'installment_count': installment_period,
            'installment_amount': installment_amount
        }
        
        # 添加额外的调解信息
        additional_parts = []

        if additional_parts:
            if final_repayment_plan:
                repayment_plan_data['repayment_plan'] = final_repayment_plan + "\n\n" + "；".join(additional_parts)
            else:
                repayment_plan_data['repayment_plan'] = "；".join(additional_parts)
        
        # 向repayment_plan表插入新记录
        plan_id = create_repayment_plan(
            user_id=final_user_id,
            repayment_plan=repayment_plan_data['repayment_plan'],
            down_payment_amount=repayment_plan_data['down_payment_amount'],
            installment_count=repayment_plan_data['installment_count'],
            installment_amount=repayment_plan_data['installment_amount'],
            status='pending_sign',
            db_manager=db_manager
        )
        
        if not plan_id:
            return f"错误：创建还款计划失败"
        
        # 查找用户的签名图片
        signature_image_path = find_signature_image(final_user_id)
        
        # 格式化协议书内容
        agreement_content, contract_no = format_agreement_content(final_user_id, user_info, repayment_plan_data)
        
        # 生成PDF文件
        try:
            pdf_filepath = generate_pdf_with_signature(final_user_id, agreement_content, signature_image_path)
        except Exception as e:
            print(f"PDF生成失败：{e}")
            pdf_filepath = None
        
        # 更新还款计划记录
        if pdf_filepath:
            update_repayment_plan(
                plan_id=plan_id,
                contract_file=pdf_filepath,
                signature_image=signature_image_path,
                status='signed' if signature_image_path else 'pending_sign',
                db_manager=db_manager
            )
        
        # 返回协议书文本内容
        result = f"""
金融纠纷调解协议书

协议编号：{contract_no}
调解机构：【模拟】南京大学附属律师事务所

{agreement_content}

---
协议已生成，文件路径：{pdf_filepath if pdf_filepath else 'PDF生成失败'}
还款计划记录ID：{plan_id}
状态：{'已签署' if signature_image_path else '待签署'}
"""
        
        return result
        
    except Exception as e:
        error_msg = f"调解协议签署工具执行失败：{str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # 测试工具 - 使用模型实际的参数格式
    test_result = sign_mediation_agreement(
        username="张三",
        amount=15500.0,
        source="招商银行",
        reason="生意失败资金周转困难",
        overdue_days=45,
        mediation_plan="分期X期/一次性还款/减免后还款"
    )
    print(test_result)
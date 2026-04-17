import streamlit as st
from sympy import false

from webui_pages.record_out import *
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import pandas as pd
from server.knowledge_base.utils import get_file_path, LOADER_DICT
from server.knowledge_base.kb_service.base import get_kb_details, get_kb_file_details
from typing import Literal, Dict, Tuple
from configs import (kbs_config,
                     EMBEDDING_MODEL, DEFAULT_VS_TYPE,
                     CHUNK_SIZE, OVERLAP_SIZE, ZH_TITLE_ENHANCE)
from server.utils import list_embed_models, list_online_embed_models
import os
import time

# SENTENCE_SIZE = 100

# cell_renderer = JsCode("""function(params) {if(params.value==true){return '✓'}else{return '×'}}""")


def config_aggrid(
        df: pd.DataFrame,
        columns: Dict[Tuple[str, str], Dict] = {},
        selection_mode: Literal["single", "multiple", "disabled"] = "single",
        use_checkbox: bool = False,
) -> GridOptionsBuilder:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("No", width=40)
    for (col, header), kw in columns.items():
        gb.configure_column(col, header, wrapHeaderText=True, **kw)
    gb.configure_selection(
        selection_mode=selection_mode,
        use_checkbox=use_checkbox,
        # pre_selected_rows=st.session_state.get("selected_rows", [0]),
    )
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=20
    )
    return gb


def file_exists(kb: str, selected_rows: List) -> Tuple[str, str]:
    """
    check whether a doc file exists in local knowledge base folder.
    return the file's name and path if it exists.
    """
    # 处理 DataFrame 或列表类型的 selected_rows
    if isinstance(selected_rows, pd.DataFrame):
        if selected_rows.empty:
            return "", ""
        selected_rows = selected_rows.to_dict('records')
    
    if selected_rows:
        file_name = selected_rows[0]["file_name"]
        file_path = get_file_path(kb, file_name)
        if os.path.isfile(file_path):
            return file_name, file_path
    return "", ""


def knowledge_base_page(api: ApiRequest, is_lite: bool = None):
    try:
        kb_list = {x["kb_name"]: x for x in get_kb_details()}
    except Exception as e:
        st.error(
            "获取知识库信息错误，请检查是否已按照 `README.md` 中 `4 知识库初始化与迁移` 步骤完成初始化或迁移，或是否为数据库连接错误。")
        st.stop()
    kb_names = list(kb_list.keys())

    if "selected_kb_name" in st.session_state and st.session_state["selected_kb_name"] in kb_names:
        selected_kb_index = kb_names.index(st.session_state["selected_kb_name"])
    else:
        selected_kb_index = 0

    if "selected_kb_info" not in st.session_state:
        st.session_state["selected_kb_info"] = ""

    # 添加刷新状态跟踪
    if "refresh_trigger" not in st.session_state:
        st.session_state["refresh_trigger"] = 0

    def format_selected_kb(kb_name: str) -> str:
        if kb := kb_list.get(kb_name):
            return f"{kb_name} ({kb['vs_type']} @ {kb['embed_model']})"
        else:
            return kb_name

    selected_kb = st.selectbox(
        "请选择或新建知识库：",
        kb_names + ["新建知识库"],
        format_func=format_selected_kb,
        index=selected_kb_index
    )

    if selected_kb == "新建知识库":
        with st.form("新建知识库"):

            kb_name = st.text_input(
                "新建知识库名称",
                placeholder="新知识库名称，不支持中文命名",
                key="kb_name",
            )
            kb_info = st.text_input(
                "知识库简介",
                placeholder="知识库简介，方便Agent查找",
                key="kb_info",
            )

            cols = st.columns(2)

            vs_types = list(kbs_config.keys())
            vs_type = cols[0].selectbox(
                "向量库类型",
                vs_types,
                index=vs_types.index(DEFAULT_VS_TYPE),
                key="vs_type",
            )

            if is_lite:
                embed_models = list_online_embed_models()
            else:
                embed_models = list_embed_models() + list_online_embed_models()

            embed_model = cols[1].selectbox(
                "Embedding 模型",
                embed_models,
                index=embed_models.index(EMBEDDING_MODEL),
                key="embed_model",
            )

            submit_create_kb = st.form_submit_button(
                "新建",
                # disabled=not bool(kb_name),
                use_container_width=True,
            )

        if submit_create_kb:
            if not kb_name or not kb_name.strip():
                st.error(f"知识库名称不能为空！")
            elif kb_name in kb_list:
                st.error(f"名为 {kb_name} 的知识库已经存在！")
            else:
                ret = api.create_knowledge_base(
                    knowledge_base_name=kb_name,
                    vector_store_type=vs_type,
                    embed_model=embed_model,
                )
                st.toast(ret.get("msg", " "))
                st.session_state["selected_kb_name"] = kb_name
                st.session_state["selected_kb_info"] = kb_info
                st.rerun()

    elif selected_kb:
        kb = selected_kb
        st.session_state["selected_kb_info"] = kb_list[kb]['kb_info']

        # 添加强制刷新按钮区域
        col_refresh, col_info = st.columns([1, 5])
        with col_refresh:
            if st.button("🔄 强制刷新表格", use_container_width=True, key="force_refresh_btn"):
                st.session_state["refresh_trigger"] += 1
                st.rerun()
        with col_info:
            st.caption(f"当前知识库: {kb} | 最后刷新时间: {time.strftime('%H:%M:%S')}")

        # 上传文件
        files = st.file_uploader("上传知识文件：",
                                 [i for ls in LOADER_DICT.values() for i in ls],
                                 accept_multiple_files=True,
                                 )
        kb_info = st.text_area("请输入知识库介绍:", value=st.session_state["selected_kb_info"], max_chars=None,
                               key=None,
                               help=None, on_change=None, args=None, kwargs=None)

        if kb_info != st.session_state["selected_kb_info"]:
            st.session_state["selected_kb_info"] = kb_info
            api.update_kb_info(kb, kb_info)

        # with st.sidebar:
        with st.expander(
                "文件处理配置",
                expanded=True,
        ):
            cols = st.columns(3)
            chunk_size = cols[0].number_input("单段文本最大长度：", 1, 1000, CHUNK_SIZE)
            chunk_overlap = cols[1].number_input("相邻文本重合长度：", 0, chunk_size, OVERLAP_SIZE)
            cols[2].write("")
            cols[2].write("")
            zh_title_enhance = cols[2].checkbox("开启中文标题加强", ZH_TITLE_ENHANCE)

        if st.button(
                "添加文件到知识库",
                # use_container_width=True,
                disabled=len(files) == 0,
        ):
            ret = api.upload_kb_docs(files,
                                     knowledge_base_name=kb,
                                     override=True,
                                     chunk_size=chunk_size,
                                     chunk_overlap=chunk_overlap,
                                     zh_title_enhance=zh_title_enhance)
            if msg := check_success_msg(ret):
                st.toast(msg, icon="✔")
            elif msg := check_error_msg(ret):
                st.toast(msg, icon="✖")
            # 上传后刷新表格
            st.session_state["refresh_trigger"] += 1
            st.rerun()

        st.divider()

        # 知识库详情
        # st.info("请选择文件，点击按钮进行操作。")
        # 每次刷新时重新获取数据
        doc_details = pd.DataFrame(get_kb_file_details(kb))
        print("最终的文档数据：" + '\n' + str(doc_details))
        selected_rows = []
        if not len(doc_details):
            st.info(f"知识库 `{kb}` 中暂无文件")
        else:
            st.write(f"知识库 `{kb}` 中已有文件:")
            st.info("知识库中包含源文件与向量库，请从下表中选择文件后操作")
            doc_details.drop(columns=["kb_name"], inplace=True)
            doc_details = doc_details[[
                "No", "file_name", "document_loader", "text_splitter", "docs_count", "in_folder", "in_db",
            ]]
            doc_details = doc_details.astype(str)
            doc_details["in_folder"] = doc_details["in_folder"].replace(True, "✓").replace(False, "×")
            doc_details["in_db"] = doc_details["in_db"].replace(True, "✓").replace(False, "×")
            gb = config_aggrid(
                doc_details,
                {
                    ("No", "序号"): {},
                    ("file_name", "文档名称"): {},
                    # ("file_ext", "文档类型"): {},
                    # ("file_version", "文档版本"): {},
                    ("document_loader", "文档加载器"): {},
                    ("docs_count", "文档数量"): {},
                    ("text_splitter", "分词器"): {},
                    # ("create_time", "创建时间"): {},
                    ("in_folder", "源文件"): {},
                    ("in_db", "向量库"): {},
                },
                "multiple",
            )

            # 使用更简单的 key 来避免序列化问题
            grid_key = f"aggrid_{kb}_{st.session_state['refresh_trigger']}"

            doc_grid = AgGrid(
                doc_details,
                gb.build(),
                columns_auto_size_mode="FIT_CONTENTS",
                theme="alpine",
                custom_css={
                    "#gridToolBar": {"display": "none"},
                },
                key=grid_key,
                allow_unsafe_jscode=False,
                enable_enterprise_modules=False,
                reload_data=True,  # 添加这个参数确保数据重载
                fit_columns_on_grid_load=True,  # 加载时自动适配列宽
            )

            selected_rows = doc_grid.get("selected_rows", [])
            # 确保 selected_rows 是列表格式
            if isinstance(selected_rows, pd.DataFrame):
                selected_rows = selected_rows.to_dict('records') if not selected_rows.empty else []

            cols = st.columns(4)
            file_name, file_path = file_exists(kb, selected_rows)
            print("file_name , file_path: "+ file_name, file_path)
            if file_path:
                with open(file_path, "rb") as fp:
                    cols[0].download_button(
                        "下载选中文档",
                        fp,
                        file_name=file_name,
                        use_container_width=True, )
            else:
                cols[0].download_button(
                    "下载选中文档",
                    "",
                    disabled=True,
                    use_container_width=True, )

            st.write()
            # 将文件分词并加载到向量库中
            if cols[1].button(
                    "重新添加至向量库" if selected_rows and any(row.get("in_db", False) for row in selected_rows) else "添加至向量库",
                    disabled=not file_exists(kb, selected_rows)[0],
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.update_kb_docs(kb,
                                   file_names=file_names,
                                   chunk_size=chunk_size,
                                   chunk_overlap=chunk_overlap,
                                   zh_title_enhance=zh_title_enhance)
                # 操作后刷新表格
                st.session_state["refresh_trigger"] += 1
                st.rerun()

            # 将文件从向量库中删除，但不删除文件本身。
            if cols[2].button(
                    "从向量库删除",
                    disabled=not (selected_rows and selected_rows[0]["in_db"]),
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.delete_kb_docs(kb, file_names=file_names)
                # 操作后刷新表格
                st.session_state["refresh_trigger"] += 1
                st.rerun()

            if cols[3].button(
                    "从知识库中删除",
                    type="primary",
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.delete_kb_docs(kb, file_names=file_names, delete_content=True)
                # 操作后刷新表格
                st.session_state["refresh_trigger"] += 1
                st.rerun()

        st.divider()

        st.write("文件内文档列表。双击进行修改，在删除列填入 Y 可删除对应行。")
        docs = []
        df = pd.DataFrame([], columns=["seq", "id", "content", "source"])
        if selected_rows:
            file_name = selected_rows[0]["file_name"]
            docs = api.search_kb_docs(knowledge_base_name=selected_kb, file_name=file_name)
            data = [
                {"seq": i + 1, "id": x["id"], "page_content": x["page_content"], "source": x["metadata"].get("source"),
                 "type": x["type"],
                 "metadata": json.dumps(x["metadata"], ensure_ascii=False),
                 "to_del": "",
                 } for i, x in enumerate(docs)]
            df = pd.DataFrame(data)

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_columns(["id", "source", "type", "metadata"], hide=True)
            gb.configure_column("seq", "No.", width=50)
            gb.configure_column("page_content", "内容", editable=True, autoHeight=True, wrapText=True, flex=1,
                                cellEditor="agLargeTextCellEditor", cellEditorPopup=True)
            gb.configure_column("to_del", "删除", editable=True, width=50, wrapHeaderText=True,
                                cellEditor="agCheckboxCellEditor", cellRender="agCheckboxCellRenderer")
            gb.configure_selection()

            # 为第二个表格也添加动态key
            edit_docs = AgGrid(df, gb.build(), allow_unsafe_jscode=True)

            if st.button("保存更改"):
                # origin_docs = {x["id"]: {"page_content": x["page_content"], "type": x["type"], "metadata": x["metadata"]} for x in docs}
                changed_docs = []
                for index, row in edit_docs.data.iterrows():
                    # origin_doc = origin_docs[row["id"]]
                    # if row["page_content"] != origin_doc["page_content"]:
                    if row["to_del"] not in ["Y", "y", 1]:
                        changed_docs.append({
                            "page_content": row["page_content"],
                            "type": row["type"],
                            "metadata": json.loads(row["metadata"]),
                        })

                if changed_docs:
                    if api.update_kb_docs(knowledge_base_name=selected_kb,
                                          file_names=[file_name],
                                          docs={file_name: changed_docs}):
                        st.toast("更新文档成功")
                        # 更新后刷新表格
                        st.session_state["refresh_trigger"] += 1
                        st.rerun()
                    else:
                        st.toast("更新文档失败")
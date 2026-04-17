import threading
from datetime import datetime
import time
import streamlit as st
from webui_pages.record_out import *
from streamlit_option_menu import option_menu
from webui_pages.dialogue.dialogue import dialogue_page
from webui_pages.knowledge_base.knowledge_base import knowledge_base_page
from webui_pages.login.login import login_page, save_db, username
from webui_pages.login.login import user_information_page
from webui_pages.signature.signature import signature_page
import os
import sys
from configs import VERSION
from server.utils import api_address

api = ApiRequest(base_url=api_address())
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'start_time' not in st.session_state:
    logger.info("start_time 已初始化")
    st.session_state.start_time = datetime.now()
my_time = st.session_state.start_time

if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        is_lite = "lite" in sys.argv
        st.set_page_config(
            "Langchain-Chatchat WebUI",
            os.path.join("img", "login_title.png"),
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/chatchat-space/Langchain-Chatchat',
                'Report a bug': "https://github.com/chatchat-space/Langchain-Chatchat/issues",
                'About': f"""欢迎使用 Langchain-Chatchat WebUI {VERSION}！"""
            }
        )
        sidebar = st.sidebar
        # 通过侧边栏添加菜单项和帮助链接等
        pages = {
            "签署协议": {
                "icon": "pen",
                "func": signature_page,
            },
            "对话": {
                "icon": "chat",
                "func": dialogue_page,
            },
            "知识库管理": {
                "icon": "hdd-stack",
                "func": knowledge_base_page,

            },
            "案件信息": {
                "icon": "hdd-stack",
                "func": user_information_page,
            },
        }

        with st.sidebar:
            # 侧边栏图标
            st.image(
                os.path.join(
                    "img",
                    "login_title.png"
                ),
                use_column_width=True
            )
            # 侧边栏图标(页面选择)
            options = list(pages)
            icons = [x["icon"] for x in pages.values()]
            
            # 检查用户是否已签署
            from server.db.database_manager import check_user_signed
            if 'username' in st.session_state:
                is_signed = check_user_signed(st.session_state.username)
            else:
                is_signed = False
            
            # 如果未签署，只能访问签署页面
            if not is_signed:
                options = ["签署协议"]
                icons = ["pen"]
                st.warning("请先签署诉前调解告知书，再进行其他操作")
            
            default_index = 0
            selected_page = option_menu(
                "",
                options=options,
                icons=icons,
                # menu_icon="chat-quote",
                default_index=default_index,
            )

        if selected_page in pages:
            pages[selected_page]["func"](api=api, is_lite=is_lite)


def my_function():
    global my_time
    # print(f"my_time是{my_time}")
    # print(f"开始时间{st.session_state.start_time}")
    end_time = datetime.now()
    # print(f"结束时间是{end_time}")
    time_difference = end_time - st.session_state.start_time
    if time_difference.seconds >= 10 and my_time != st.session_state.start_time:
        save_db(username)
        my_time = st.session_state.start_time
    while True:
        # my_function()
        time.sleep(10)  # 暂停十秒钟后再次执行


if 'thread' not in st.session_state:
    st.session_state.thread = threading.Thread(target=my_function)
    st.session_state.thread.start()

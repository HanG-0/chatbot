import json
import os
from decimal import Decimal

import streamlit as st
import pandas as pd

from get_predict_result import get_predict_result
from webui_pages.dialogue.dialogue import chat_box
from webui_pages.record.record_out import export2json
from webui_pages.record_out import ApiRequest
from dataclasses import dataclass
import dataclasses
from server.db.redis_manager import get_redis
from server.db.database_manager import (
    verify_user,
    get_user_info,
    save_mediation_record,
    get_db_manager
)

r = get_redis()

# 全局欠款信息
@dataclass
class BackgroundInfo:
    # 张三由于生意失败资金周转困难，从招商银行总共贷款了15000.00元，总利息为300.00元。逾期45天，总罚息为200.00元。目前共欠招商银行15500.00元。
    username:str
    debt_reason:str
    debt_source:str
    total_debt_origin:float
    total_interest:float
    delay_day:int
    total_penalty:float
    total_debt_all:float

    def update_from_user_info(self, user_info: tuple):
        """
        从数据库查询结果元组批量更新属性
        保持对象引用不变，只修改内部状态
        """
        # 按字段顺序映射: user_info 索引 → 属性名
        self.username = user_info[0]
        self.debt_reason = user_info[8]
        self.debt_source = user_info[5]
        self.total_debt_origin = user_info[9]
        self.total_interest = user_info[10]
        self.delay_day = user_info[6]
        self.total_penalty = user_info[11]
        self.total_debt_all = user_info[4]

    def to_json(self) -> str:
        """序列化为 JSON，将 Decimal 转换为 float"""
        data = dataclasses.asdict(self)
        # 将所有 Decimal 字段转换为 float
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return json.dumps(data, ensure_ascii=False)

username = ""
db_manager = get_db_manager()

def save_db(user_name):
    user_id = user_name
    content = export2json(chat_box)
    print("即将保存的聊天记录为：{}".format(content))
    list_str = json.dumps(content)
    is_success = get_predict_result()
    save_mediation_record(user_id, list_str, is_success, db_manager)


def login_page():
    st.image(os.path.join("img", "login_title.png"))
    with st.sidebar:
        st.title("登录")
        # 获取用户输入的用户名和密码
        global username
        username = st.text_input('用户名')
        id_card = st.text_input('身份证号')
        password = st.text_input('密码', type='password')

        # 验证用户凭据
        if st.button('登录'):
            result = verify_user(username,id_card, password, db_manager)
            if result:
                st.session_state.logged_in = True
                st.session_state.username = username
                user_info = get_user_info(username, db_manager)
                if user_info:
                    # 更新用户信息
                    background_info = BackgroundInfo("", "", "", 0, 0, 0, 0, 0)
                    background_info.update_from_user_info(user_info)
                    r.setex("background_info", 3000,background_info.to_json())
                    from configs.status_prompt import STATUS_PROMPT_TEMPLATES
                    st.session_state.prompt1 =  STATUS_PROMPT_TEMPLATES.get("S0").format(**dataclasses.asdict(background_info))

                else:
                    return None
            else:
                st.error('用户名或密码错误')


def user_information_page(api: ApiRequest, is_lite: bool = None):
    global username
    st.markdown('<h3 style="text-align: center;">案件信息</h3>', unsafe_allow_html=True)
    username = st.session_state.username
    user_info = get_user_info(username, db_manager)

    if user_info is not None:
        selected_columns = [0, 8, 5, 9, 10, 6, 11, 4]  # 指定你想要选择的8个列的索引
        selected_info = [user_info[i] for i in selected_columns]  # 根据索引从user_info中选择相应的列
        index = ['当事人信息', '欠款原因', '欠款项目', '欠款金额', '总利息', '逾期天数', '总罚息', '总欠款']
        user_series = pd.Series(selected_info, index=index)
        st.table(user_series)

    else:
        st.write("未找到用户信息")

    cols = st.columns(5)

    with cols[0]:
        pass
    with cols[1]:
        pass
    with cols[3]:
        pass
    with cols[4]:
        pass
    with cols[2]:
        if st.button('退出登录'):
            save_db(username)
            st.session_state.logged_in = False  # 退出登录状态
            chat_box.reset_history()
            st.session_state.run_once = True
            st.rerun()




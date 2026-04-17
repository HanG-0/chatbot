from typing import Callable
from streamlit_chatbox import *



def export2json(
        chat_box: ChatBox,
        chat_name: str = None,
        callback: Callable = None,
) -> list:
    chat_box.init_session()
    export_dict = []
    export_user = []

    history = chat_box.other_history(chat_name)

    for msg in history:
        if callable(callback):
            exported_msg = callback(msg)
        else:
            contents = [e.content for e in msg["elements"]]
            if msg["role"] == "user":
                content = " ".join(contents)
                export_dict.append({"user": content, "Assistant": ""})
                export_user.append(content)
            else:
                content = " ".join(contents)
                if export_dict:  # 检查export_dict是否为空
                    export_dict[-1]["Assistant"] = content
                else:
                    export_dict.append({"user": "", "Assistant": content})  # 初始化export_dict
    return export_dict


def export2user(
        chat_box: ChatBox,
        chat_name: str = None,
        callback: Callable = None,
) -> list:
    chat_box.init_session()
    export_user = []

    history = chat_box.other_history(chat_name)

    for msg in history:
        if callable(callback):
            exported_msg = callback(msg)
        else:
            contents = [e.content for e in msg["elements"]]
            if msg["role"] == "user":
                content = " ".join(contents)
                export_user.append(content)
    return export_user

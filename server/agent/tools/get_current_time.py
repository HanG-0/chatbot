from __future__ import annotations
import os
import sys

from pydantic import BaseModel, Field
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))


class GetCurrentTimeInput(BaseModel):
    """Input schema for getting current time tool (英文版)"""
    # 这个工具不需要参数，但需要定义一个虚拟字段来避免 LangChain 解析错误
    dummy: str = Field(default="", description="虚拟字段，此工具不需要参数")


def get_current_time(dummy:str) -> str:
    """
    获取当前时间的工具

    功能描述：返回当前的系统时间，包括日期和时间信息。

    输入参数：
    - 无参数

    返回结果：
    - 当前时间信息（格式化后的字符串）
    """

    try:
        # 获取当前时间
        now = datetime.now()

        # 格式化输出
        formatted_time = now.strftime("%Y年%m月%d日 %H:%M:%S")
        weekday = now.strftime("%A")

        # 星期几的中文映射
        weekday_map = {
            "Monday": "星期一",
            "Tuesday": "星期二",
            "Wednesday": "星期三",
            "Thursday": "星期四",
            "Friday": "星期五",
            "Saturday": "星期六",
            "Sunday": "星期日"
        }
        weekday_cn = weekday_map.get(weekday, weekday)

        # 构建返回结果
        result = f"""
当前时间信息
================
日期时间：{formatted_time}
星期：{weekday_cn}
时间戳：{now.timestamp()}
"""

        return result.strip()

    except Exception as e:
        return f"获取当前时间时发生错误: {str(e)}"
from __future__ import annotations
import os
import sys
import random
from typing import Optional

from pydantic import BaseModel, Field

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from server.db.database_manager import get_user_info, get_db_manager


class GetPenaltyReductionInput(BaseModel):
    """Input schema for getting penalty reduction tool (英文版)"""
    user_id: str = Field(description="User ID or username of the borrower (借款人用户ID或用户名)")


def get_penalty_reduction(
    user_id: str
) -> str:
    """
    获取用户罚息减免金额的工具

    功能描述：根据用户的罚息总额，计算可能的减免金额（罚息的10%-50%之间随机）。

    输入参数：
    - user_id: 用户ID或用户名

    返回结果：
    - 减免金额信息（包括原罚息、减免比例、减免金额）
    """

    try:
        # 获取数据库管理器
        db_manager = get_db_manager()

        # 获取用户信息
        user_info = get_user_info(account=user_id, db_manager=db_manager)

        if user_info is None:
            return f"错误：未找到用户ID为 {user_id} 的用户信息"

        # 根据表结构，total_penalty是第12个字段（索引11）
        # user_info字段顺序：name(0), account(1), password(2), phone(3),
        # total_debt(4), debt_project(5), overdue_days(6), id_card(7),
        # debt_reason(8), loan_amount(9), total_interest(10), total_penalty(11)

        try:
            total_penalty = float(user_info[11]) if user_info[11] is not None else 0.0
        except (IndexError, TypeError, ValueError) as e:
            return f"错误：无法获取用户 {user_id} 的罚息信息 - {str(e)}"

        # 如果罚息为0或为负数，无法减免
        if total_penalty <= 0:
            return f"用户 {user_id} 的罚息金额为 {total_penalty:.2f} 元，无法进行减免"

        # 随机生成10%-50%的减免比例
        reduction_rate = random.uniform(0.1, 0.5)
        reduction_percentage = reduction_rate * 100

        # 计算减免金额
        reduction_amount = total_penalty * reduction_rate

        # 计算减免后需要支付的金额
        remaining_penalty = total_penalty - reduction_amount

        # 格式化输出结果
        result = f"""
                罚息减免信息
                ================
                用户：{user_info[0]} (ID: {user_id})
                原罚息金额：{total_penalty:.2f} 元
                减免比例：{reduction_percentage:.1f}%
                减免金额：{reduction_amount:.2f} 元
                减免后需支付罚息：{remaining_penalty:.2f} 元
                
                注意：此减免金额为系统计算建议值，最终减免金额以实际协商结果为准。
                 """
        return result.strip()

    except Exception as e:
        return f"计算罚息减免金额时发生错误: {str(e)}"
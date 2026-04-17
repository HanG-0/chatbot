from __future__ import annotations
import os
import sys
from typing import Optional

from pydantic import BaseModel, Field
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from server.db.database_manager import (
    mark_repayment_as_signed,
    get_db_manager
)


class MarkRepaymentSignedInput(BaseModel):
    """Input schema for marking repayment as signed tool (英文版)"""
    user_id: str = Field(description="User ID of the borrower (借款人用户ID)")


def mark_repayment_signed(
    user_id: str
) -> str:
    """
    标记还款计划为已签署/已还款的工具

    功能描述：将用户对应的还款计划状态修改为signed，表示用户已经完成还款。

    输入参数：
    - user_id: 用户ID

    返回结果：
    - 操作结果信息
    """

    try:
        # 获取数据库管理器
        db_manager = get_db_manager()

        # 标记还款计划为已签署
        success = mark_repayment_as_signed(
            user_id=user_id,
            db_manager=db_manager
        )

        if success:
            result = f"""
还款计划状态更新

用户：{user_id}
操作：将还款计划状态更新为已签署
状态：已签署 (signed)
时间：{datetime.now()}
结果：成功！

系统已将用户 {user_id} 的还款计划标记为已签署，这表示用户已经按照调解协议完成了还款义务。
"""
        else:
            result = f"""
还款计划状态更新

用户：{user_id}
操作：将还款计划状态更新为已签署
状态：失败
时间：{sys.get('当前时间') if '当前时间' in sys.get else '未知'}
结果：未能更新还款计划状态为已签署

系统未能将用户 {user_id} 的还款计划标记为已签署，请稍后重试。
"""

        return result

    except Exception as e:
        error_msg = f"标记还款为已签署工具执行失败：{str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # 测试工具
    test_result = mark_repayment_signed(user_id="zhangsan")
    print(test_result)
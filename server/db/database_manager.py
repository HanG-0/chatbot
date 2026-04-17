"""
统一的数据库操作模块
提供用户认证和调解记录管理的统一接口
"""
import mysql.connector
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager
import json

from configs import logger
from dotenv import find_dotenv,load_dotenv
import os
env_file = find_dotenv()
load_dotenv(env_file)

class DatabaseConfig:
    """数据库配置类"""
    def __init__(
        self,
        host: str = os.getenv("MYSQL_HOST", "localhost"),
        database: str = os.getenv("MYSQL_DATABASE", "chatbot"),
        user: str = os.getenv("MYSQL_USER", "root"),
        password: str = os.getenv("MYSQL_PASSWORD", "root"),
    ):
        self.host = host
        self.database = database
        self.user = user
        self.password = password


class DatabaseManager:
    """数据库管理器 - 提供统一的数据库操作接口"""
    
    _instance = None
    _config = None
    
    def __new__(cls, config: Optional[DatabaseConfig] = None):
        """单例模式确保只有一个数据库管理器实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = config or DatabaseConfig()
            cls._instance._connection = None
        return cls._instance
    
    @property
    def connection(self):
        """获取数据库连接（懒加载）"""
        if self._connection is None or not self._connection.is_connected():
            self._connection = mysql.connector.connect(
                host=self._config.host,
                database=self._config.database,
                user=self._config.user,
                password=self._config.password
            )
            logger.info("数据库连接已建立")
        return self._connection
    
    @property
    def cursor(self):
        """获取数据库游标"""
        return self.connection.cursor()
    
    def commit(self):
        """提交事务"""
        self.connection.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None
            logger.info("数据库连接已关闭")
    
    @contextmanager
    def get_cursor(self):
        """上下文管理器：自动获取和关闭游标"""
        cursor = self.cursor
        try:
            yield cursor
        finally:
            pass  # 游标由连接管理器自动关闭


# ==================== 用户认证相关操作 ====================

def verify_user(account: str,id_card:str, password: str, db_manager: DatabaseManager = None) -> Optional[Tuple]:
    """
    验证用户登录凭证
    
    Args:
        account: 用户名
        password: 密码
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        如果验证成功，返回用户信息元组；否则返回 None
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            query = "SELECT * FROM user_info WHERE account = %s AND password = %s AND id_card = %s"
            cursor.execute(query, (account, password,id_card))
            result = cursor.fetchone()
            
            if result:
                logger.info(f"用户 {account} 登录成功")
            else:
                logger.warning(f"用户 {account} 登录失败：用户名或密码或身份证错误")
            
            return result
    except mysql.connector.Error as e:
        logger.error(f"验证用户时发生错误: {e}")
        return None


def get_user_info(account: str, db_manager: DatabaseManager = None) -> Optional[Tuple]:
    """
    获取用户信息
    
    Args:
        account: 用户名
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        用户信息元组，如果不存在则返回 None
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            query = "SELECT * FROM user_info WHERE account = %s"
            cursor.execute(query, (account,))
            result = cursor.fetchone()
            return result
    except mysql.connector.Error as e:
        logger.error(f"获取用户信息时发生错误: {e}")
        return None


# ==================== 调解记录相关操作 ====================

def save_mediation_record(
    user_id: str,
    content: str,
    is_success: bool,
    db_manager: DatabaseManager = None
) -> bool:
    """
    保存调解记录
    
    Args:
        user_id: 用户ID
        content: 对话内容JSON字符串
        is_success: 预测是否成功
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        保存成功返回 True，失败返回 False
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            sql = "INSERT INTO mediation_record (content, is_success, user_id) VALUES (%s, %s, %s)"
            cursor.execute(sql, (content, is_success, user_id))
            db_manager.commit()
            logger.info(f"成功保存用户 {user_id} 的调解记录")
            return True
    except mysql.connector.Error as e:
        logger.error(f"保存调解记录时发生错误: {e}")
        return False


def get_mediation_records(
    user_id: Optional[str] = None,
    limit: int = 100,
    db_manager: DatabaseManager = None
) -> List[Dict[str, Any]]:
    """
    获取调解记录
    
    Args:
        user_id: 用户ID（可选，为None则获取所有记录）
        limit: 返回记录的最大数量
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        调解记录列表，每个记录是一个字典
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            if user_id:
                query = """
                    SELECT id, user_id, content, is_success, created_at 
                    FROM mediation_record 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                cursor.execute(query, (user_id, limit))
            else:
                query = """
                    SELECT id, user_id, content, is_success, created_at 
                    FROM mediation_record 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            records = []
            columns = ['id', 'user_id', 'content', 'is_success', 'created_at']
            
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # 尝试解析JSON内容
                try:
                    record['content'] = json.loads(record['content'])
                except (json.JSONDecodeError, TypeError):
                    pass
                records.append(record)
            
            return records
    except mysql.connector.Error as e:
        logger.error(f"获取调解记录时发生错误: {e}")
        return []


# ==================== 调解案件进度相关操作 ====================

def create_case_progress(
    user_id: str,
    status: str,
    contract_file: str = None,
    image_file:str = None,
    db_manager: DatabaseManager = None
) -> bool:
    """
    创建调解案件进度记录
    
    Args:
        user_id: 用户ID
        status: 调解状态
        contract_file: 合同文件路径（可选）
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        创建成功返回 True，失败返回 False
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            sql = "INSERT INTO mediation_case_progress (user_id, status, contract_file,image_file) VALUES (%s, %s, %s,%s)"
            cursor.execute(sql, (user_id, status, contract_file,image_file))
            db_manager.commit()
            logger.info(f"成功创建用户 {user_id} 的案件进度记录，状态：{status}")
            return True
    except mysql.connector.Error as e:
        logger.error(f"创建案件进度记录时发生错误: {e}")
        return False


def get_case_progress(
    user_id: str,
    db_manager: DatabaseManager = None
) -> Optional[Tuple]:
    """
    获取用户案件进度记录
    
    Args:
        user_id: 用户ID
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        案件进度记录元组，如果不存在则返回 None
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            query = "SELECT * FROM mediation_case_progress WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result
    except mysql.connector.Error as e:
        logger.error(f"获取案件进度记录时发生错误: {e}")
        return None


def check_user_signed(user_id: str, db_manager: DatabaseManager = None) -> bool:
    """
    检查用户是否已签署协议
    
    Args:
        user_id: 用户ID
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        已签署返回 True，未签署返回 False
    """
    progress = get_case_progress(user_id, db_manager)
    return progress is not None
    

def update_case_progress(
    user_id: str,
    status: str,
    db_manager: DatabaseManager = None
) -> bool:
    """
    更新用户案件进度记录的状态
    
    Args:
        user_id: 用户ID
        status: 新状态（如 S0, S1, S2, S3）
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        更新成功返回 True，失败返回 False
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            sql = "UPDATE mediation_case_progress SET status = %s WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
            cursor.execute(sql, (status, user_id))
            db_manager.commit()
            logger.info(f"成功更新用户 {user_id} 的案件进度状态为：{status}")
            return True
    except mysql.connector.Error as e:
        logger.error(f"更新案件进度状态时发生错误: {e}")
        return False


# ==================== 还款计划相关操作 ====================

def create_repayment_plan(
    user_id: str,
    repayment_plan: str,
    down_payment_amount: float = None,
    installment_count: int = None,
    installment_amount: float = None,
    status: str = 'pending_sign',
    db_manager: DatabaseManager = None
) -> int:
    """
    创建还款计划记录
    
    Args:
        user_id: 用户ID
        repayment_plan: 具体调解方案，文本形式
        down_payment_amount: 首付金额（可选）
        installment_count: 分期数量（可选）
        installment_amount: 每期还款金额（可选）
        status: 状态（默认为 pending_sign）
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        创建成功返回记录ID，失败返回 None
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            sql = """
                INSERT INTO repayment_plan
                (user_id, repayment_plan, down_payment_amount, installment_count, installment_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, repayment_plan, down_payment_amount,
                            installment_count, installment_amount, status))
            db_manager.commit()
            record_id = cursor.lastrowid
            logger.info(f"成功创建用户 {user_id} 的还款计划，ID：{record_id}")
            return record_id
    except mysql.connector.Error as e:
        logger.error(f"创建还款计划时发生错误: {e}")
        return None


def update_repayment_plan(
    plan_id: int,
    contract_file: str = None,
    signature_image: str = None,
    status: str = None,
    db_manager: DatabaseManager = None
) -> bool:
    """
    更新还款计划记录
    
    Args:
        plan_id: 还款计划ID
        contract_file: 协议文件路径（可选）
        signature_image: 签名图片路径（可选）
        status: 状态（可选）
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        更新成功返回 True，失败返回 False
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            # 动态构建更新SQL
            update_fields = []
            values = []
            
            if contract_file is not None:
                update_fields.append("contract_file = %s")
                values.append(contract_file)
            
            if signature_image is not None:
                update_fields.append("signature_image = %s")
                values.append(signature_image)
            
            if status is not None:
                update_fields.append("status = %s")
                values.append(status)
            
            if not update_fields:
                return True
            
            values.append(plan_id)
            sql = f"UPDATE repayment_plan SET {', '.join(update_fields)} WHERE id = %s"
            
            cursor.execute(sql, values)
            db_manager.commit()
            logger.info(f"成功更新还款计划，ID：{plan_id}")
            return True
    except mysql.connector.Error as e:
        logger.error(f"更新还款计划时发生错误: {e}")
        return False


def get_repayment_plan(
    user_id: str,
    db_manager: DatabaseManager = None
) -> Optional[Tuple]:
    """
    获取用户最新的还款计划
    
    Args:
        user_id: 用户ID
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        还款计划记录元组，如果不存在则返回 None
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            query = "SELECT * FROM repayment_plan WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result
    except mysql.connector.Error as e:
        logger.error(f"获取还款计划时发生错误: {e}")
        return None


def mark_repayment_as_signed(
    user_id: str,
    db_manager: DatabaseManager = None
) -> bool:
    """
    将用户的还款计划状态标记为已签署/已还款
    
    Args:
        user_id: 用户ID
        db_manager: 数据库管理器实例（可选）
    
    Returns:
        更新成功返回 True，失败返回 False
    """
    if db_manager is None:
        db_manager = DatabaseManager()
    
    try:
        with db_manager.get_cursor() as cursor:
            sql = """
                UPDATE repayment_plan
                SET status = 'signed'
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(sql, (user_id,))
            db_manager.commit()
            logger.info(f"成功将用户 {user_id} 的还款计划状态更新为已签署")
            return True
    except mysql.connector.Error as e:
        logger.error(f"更新还款计划状态为已签署时发生错误: {e}")
        return False


# ==================== 便捷函数 ====================

def get_db_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """
    获取数据库管理器实例（便捷函数）
    
    Args:
        config: 数据库配置（可选）
    
    Returns:
        DatabaseManager 实例
    """
    return DatabaseManager(config)


def close_db_connection(db_manager: DatabaseManager):
    """
    关闭数据库连接（便捷函数）
    
    Args:
        db_manager: 数据库管理器实例
    """
    db_manager.close()
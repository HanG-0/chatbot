"""
测试数据库管理模块
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db.database_manager import (
    DatabaseConfig,
    DatabaseManager,
    verify_user,
    get_user_info,
    save_mediation_record,
    get_mediation_records,
    get_db_manager,
    close_db_connection
)


def test_database_manager():
    """测试数据库管理器基本功能"""
    print("=" * 50)
    print("测试数据库管理器")
    print("=" * 50)

    # 测试配置类
    print("\n1. 测试数据库配置类...")
    config = DatabaseConfig(
        host='localhost',
        database='chatbot',
        user='root',
        password='root'
    )
    print(f"   配置创建成功: {config.host}, {config.database}")

    # 测试单例模式
    print("\n2. 测试单例模式...")
    db1 = DatabaseManager(config)
    db2 = DatabaseManager(config)
    print(f"   db1 和 db2 是否为同一实例: {db1 is db2}")

    # 测试连接
    print("\n3. 测试数据库连接...")
    try:
        conn = db1.connection
        print(f"   数据库连接成功: {conn.is_connected()}")
    except Exception as e:
        print(f"   数据库连接失败: {e}")
        return False

    # 测试游标
    print("\n4. 测试游标...")
    try:
        cursor = db1.cursor
        print(f"   游标创建成功: {cursor}")
    except Exception as e:
        print(f"   游标创建失败: {e}")
        return False

    # 关闭连接
    print("\n5. 测试关闭连接...")
    db1.close()
    print("   数据库连接已关闭")

    return True


def test_user_operations():
    """测试用户操作"""
    print("\n" + "=" * 50)
    print("测试用户操作")
    print("=" * 50)

    db_manager = get_db_manager()

    # 测试用户验证
    print("\n1. 测试用户验证...")
    result = verify_user('zhangsan', '123456', db_manager)
    if result:
        print(f"   用户验证成功: {result[0]}")  # 姓名
    else:
        print("   用户验证失败")

    # 测试获取用户信息
    print("\n2. 测试获取用户信息...")
    user_info = get_user_info('zhangsan', db_manager)
    if user_info:
        print(f"   获取用户信息成功，姓名: {user_info[0]}")
    else:
        print("   获取用户信息失败")

    close_db_connection(db_manager)
    return True


def test_mediation_record_operations():
    """测试调解记录操作"""
    print("\n" + "=" * 50)
    print("测试调解记录操作")
    print("=" * 50)

    db_manager = get_db_manager()

    # 测试保存调解记录
    print("\n1. 测试保存调解记录...")
    test_content = '[{"user": "测试消息", "Assistant": ""}]'
    success = save_mediation_record('test_user', test_content, True, db_manager)
    print(f"   保存调解记录: {'成功' if success else '失败'}")

    # 测试获取调解记录
    print("\n2. 测试获取调解记录...")
    records = get_mediation_records('test_user', limit=5, db_manager=db_manager)
    print(f"   获取到 {len(records)} 条记录")
    if records:
        print(f"   最新记录ID: {records[0]['id']}")

    # 测试获取所有调解记录
    print("\n3. 测试获取所有调解记录...")
    all_records = get_mediation_records(limit=5, db_manager=db_manager)
    print(f"   获取到 {len(all_records)} 条记录")

    close_db_connection(db_manager)
    return True


def main():
    """主测试函数"""
    print("\n开始测试数据库管理模块...\n")

    try:
        # 运行所有测试
        test_database_manager()
        test_user_operations()
        test_mediation_record_operations()

        print("\n" + "=" * 50)
        print("所有测试完成！")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
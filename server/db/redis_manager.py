# utils/redis_manager.py
import redis
import atexit
import os
from typing import Optional
from contextlib import contextmanager

# ================= 配置 =================
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'decode_responses': True,  # ✅ 自动 bytes → str
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
}

# ================= 单例连接池 =================
class _RedisManager:
    """Redis 连接管理器（单例模式）"""

    _instance: Optional['redis.ConnectionPool'] = None
    _client: Optional['redis.Redis'] = None
    _initialized = False

    @classmethod
    def get_pool(cls) -> redis.ConnectionPool:
        """获取全局连接池（线程安全）"""
        if cls._instance is None:
            cls._instance = redis.ConnectionPool(**REDIS_CONFIG)
        return cls._instance

    @classmethod
    def get_client(cls) -> redis.Redis:
        """获取 Redis 客户端（从连接池获取，线程安全）"""
        if cls._client is None:
            cls._client = redis.Redis(connection_pool=cls.get_pool())
        return cls._client

    @classmethod
    def close(cls):
        """关闭连接池，释放资源"""
        if cls._instance:
            cls._instance.disconnect()
            cls._instance = None
            cls._client = None
            print("🔌 Redis 连接已关闭")

# ================= 初始化 & 自动清理 =================
def _init_redis():
    """初始化并注册退出清理"""
    if not _RedisManager._initialized:
        # 预连接测试（可选，失败不阻塞）
        try:
            client = _RedisManager.get_client()
            client.ping()
            print(f"✅ Redis 连接成功: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
        except redis.ConnectionError as e:
            print(f"⚠️ Redis 连接警告: {e}")

        # 注册程序退出时的清理函数
        atexit.register(_RedisManager.close)
        _RedisManager._initialized = True

# 模块导入时自动初始化
_init_redis()

# ================= 对外接口 =================
def get_redis() -> redis.Redis:
    """
    获取 Redis 客户端实例
    用法: r = get_redis(); r.set('key', 'value')
    """
    return _RedisManager.get_client()

@contextmanager
def redis_pipeline():
    """
    上下文管理器：自动执行/关闭 pipeline
    用法:
        with redis_pipeline() as pipe:
            pipe.set('a', '1').set('b', '2')
    """
    r = get_redis()
    pipe = r.pipeline()
    try:
        yield pipe
        pipe.execute()
    except Exception:
        pipe.reset()
        raise

# ================= 便捷函数（可选） =================
def setex(key: str, value: str, ttl: int) -> bool:
    """设置带过期时间的字符串"""
    return get_redis().setex(key, ttl, value)

def get_json(key: str) -> Optional[dict]:
    """获取并自动解析 JSON"""
    import json
    data = get_redis().get(key)
    return json.loads(data) if data else None

def set_json(key: str, value: dict, ttl: Optional[int] = None) -> bool:
    """序列化并存储 JSON"""
    import json
    r = get_redis()
    data = json.dumps(value, ensure_ascii=False)
    return r.setex(key, ttl, data) if ttl else r.set(key, data)
"""
配置管理模块
负责读写配置文件，线程安全
"""

import configparser
import threading
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"
MASTER_KEY_PATH = Path(__file__).parent / "master_key.ini"
CONFIG_LOCK = threading.Lock()


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()

    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH, encoding="utf-8")
    else:
        # 创建默认配置
        config["DEFAULT"] = {
            "api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "poll_interval": "30",
            "max_retries": "3",
            "timeout": "600",
        }
        save_config(config)

    return config


def load_master_key():
    """加载密钥文件"""
    config = configparser.ConfigParser()

    if MASTER_KEY_PATH.exists():
        config.read(MASTER_KEY_PATH, encoding="utf-8")
    else:
        config["DEFAULT"] = {
            "api_key": "",
        }
        save_master_key(config)

    return config


def save_config(config):
    """保存配置文件"""
    with CONFIG_LOCK:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            config.write(f)


def save_master_key(config):
    """保存密钥文件"""
    with CONFIG_LOCK:
        with MASTER_KEY_PATH.open("w", encoding="utf-8") as f:
            config.write(f)


def get_api_key():
    """获取 API Key"""
    master_key = load_master_key()
    api_key = master_key.get("DEFAULT", "api_key", fallback="")
    if api_key:
        print(f"[Ark-Seedance] 从 {MASTER_KEY_PATH} 读取到 API Key (长度: {len(api_key)})")
    else:
        print(f"[Ark-Seedance] {MASTER_KEY_PATH} 中未找到 API Key")
    return api_key


def save_api_key(api_key):
    """保存 API Key 到 master_key.ini"""
    master_key = load_master_key()
    master_key["DEFAULT"]["api_key"] = api_key
    save_master_key(master_key)
    print(f"[Ark-Seedance] API Key 已写入 {MASTER_KEY_PATH} (长度: {len(api_key)})")


def get_api_base_url():
    """获取 API Base URL"""
    config = load_config()
    return config.get("DEFAULT", "api_base_url", fallback="https://ark.cn-beijing.volces.com/api/v3")


def save_api_base_url(base_url):
    """保存 API Base URL 到 config.ini"""
    config = load_config()
    config["DEFAULT"]["api_base_url"] = base_url
    save_config(config)
    print(f"[Ark-Seedance] API Base URL 已写入 {CONFIG_PATH}: {base_url}")


def get_poll_interval():
    """获取轮询间隔（秒）"""
    config = load_config()
    return config.getint("DEFAULT", "poll_interval", fallback=30)


def get_max_retries():
    """获取最大重试次数"""
    config = load_config()
    return config.getint("DEFAULT", "max_retries", fallback=3)


def get_timeout():
    """获取请求超时（秒）"""
    config = load_config()
    return config.getint("DEFAULT", "timeout", fallback=600)


# ── TOS 配置 ────────────────────────────────────────────────────────────

def get_tos_config():
    """
    获取完整 TOS 配置。
    非敏感配置从 config.ini[TOS] 读取，
    AK/SK 从 master_key.ini[TOS] 读取。
    """
    config = load_config()
    master = load_master_key()
    return {
        "tos_access_key": master.get("TOS", "tos_access_key", fallback=""),
        "tos_secret_key": master.get("TOS", "tos_secret_key", fallback=""),
        "tos_endpoint": config.get("TOS", "tos_endpoint", fallback="tos-cn-beijing.volces.com"),
        "tos_region": config.get("TOS", "tos_region", fallback="cn-beijing"),
        "tos_bucket": config.get("TOS", "tos_bucket", fallback=""),
        "url_expires": config.getint("TOS", "url_expires", fallback=3600),
    }


def save_tos_config(access_key=None, secret_key=None, endpoint=None,
                    region=None, bucket=None, url_expires=None):
    """
    保存 TOS 配置。
    AK/SK 写入 master_key.ini[TOS]，其他写入 config.ini[TOS]。
    仅传入非 None 的字段会被更新。
    """
    with CONFIG_LOCK:
        # 保存非敏感配置到 config.ini
        config = load_config()
        if "TOS" not in config:
            config["TOS"] = {}
        if endpoint is not None:
            config["TOS"]["tos_endpoint"] = str(endpoint)
        if region is not None:
            config["TOS"]["tos_region"] = str(region)
        if bucket is not None:
            config["TOS"]["tos_bucket"] = str(bucket)
        if url_expires is not None:
            config["TOS"]["url_expires"] = str(int(url_expires))

        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            config.write(f)

        # 保存敏感配置到 master_key.ini
        if access_key is not None or secret_key is not None:
            master = load_master_key()
            if "TOS" not in master:
                master["TOS"] = {}
            if access_key is not None:
                master["TOS"]["tos_access_key"] = str(access_key)
            if secret_key is not None:
                master["TOS"]["tos_secret_key"] = str(secret_key)
            with MASTER_KEY_PATH.open("w", encoding="utf-8") as f:
                master.write(f)


def get_tos_access_key():
    """获取 TOS Access Key"""
    master = load_master_key()
    key = master.get("TOS", "tos_access_key", fallback="")
    if key:
        print(f"[Ark-Seedance] 从 {MASTER_KEY_PATH} 读取到 TOS Access Key (长度: {len(key)})")
    return key


def get_tos_secret_key():
    """获取 TOS Secret Key"""
    master = load_master_key()
    key = master.get("TOS", "tos_secret_key", fallback="")
    return key


def get_tos_endpoint():
    """获取 TOS Endpoint"""
    config = load_config()
    return config.get("TOS", "tos_endpoint", fallback="tos-cn-beijing.volces.com")


def get_tos_region():
    """获取 TOS Region"""
    config = load_config()
    return config.get("TOS", "tos_region", fallback="cn-beijing")


def get_tos_bucket():
    """获取 TOS Bucket 名称"""
    config = load_config()
    return config.get("TOS", "tos_bucket", fallback="")


def get_tos_url_expires():
    """获取预签名 URL 过期时间（秒）"""
    config = load_config()
    return config.getint("TOS", "url_expires", fallback=3600)

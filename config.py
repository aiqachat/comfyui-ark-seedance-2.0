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

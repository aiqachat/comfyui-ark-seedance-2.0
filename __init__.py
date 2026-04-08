"""
ComfyUI Seedance 2.0 视频生成插件
支持火山方舟 Seedance 系列视频生成模型
"""

import importlib
import sys
from pathlib import Path

# 节点自动发现
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _discover_nodes():
    """扫描当前目录下所有 .py 文件并导入节点类"""
    current_dir = Path(__file__).parent

    for py_file in current_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        module_name = py_file.stem
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)

            # 查找 NODE_CLASS_MAPPINGS
            if hasattr(module, "NODE_CLASS_MAPPINGS"):
                NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)

            # 查找 NODE_DISPLAY_NAME_MAPPINGS
            if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS"):
                NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)

        except Exception as e:
            print(f"[Ark-Seedance] 警告: 加载节点文件 {py_file.name} 失败: {e}")


# Web 扩展
WEB_DIRECTORY = "./web"


def __getattr__(name):
    """延迟加载以支持更新机制"""
    if name == "NODE_CLASS_MAPPINGS":
        _discover_nodes()
        return NODE_CLASS_MAPPINGS
    elif name == "NODE_DISPLAY_NAME_MAPPINGS":
        _discover_nodes()
        return NODE_DISPLAY_NAME_MAPPINGS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# 立即发现节点
_discover_nodes()

print(f"[Ark-Seedance] [OK] 成功加载 {len(NODE_CLASS_MAPPINGS)} 个节点")

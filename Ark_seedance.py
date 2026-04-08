"""
Ark Seedance 视频生成节点
支持文生视频、图生视频、多模态参考生视频
"""

import json
import time

import numpy as np
import torch
from PIL import Image

try:
    from .config import get_api_key, get_poll_interval
    from .seedance_client import SeedanceClient
except ImportError:
    from config import get_api_key, get_poll_interval
    from seedance_client import SeedanceClient


class ArkSeedanceVideoGen:
    """Seedance 视频生成节点 - 创建任务"""

    DISPLAY_NAME = "Ark Seedance 视频生成"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("任务ID",)
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "提示词": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "rows": 8,
                        "placeholder": "输入视频生成提示词（支持中英文，建议中文不超过500字）",
                    },
                ),
                "模型": (
                    [
                        "doubao-seedance-2-0-260128",
                        "doubao-seedance-2-0-fast-260128",
                    ],
                    {"default": "doubao-seedance-2-0-260128"},
                ),
                "分辨率": (
                    ["480p", "720p"],
                    {"default": "720p"},
                ),
                "宽高比": (
                    ["自适应", "16:9", "4:3", "1:1", "3:4", "9:16", "21:9"],
                    {"default": "自适应"},
                ),
                "时长": (
                    ["智能", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
                    {"default": "智能"},
                ),
                "生成音频": (
                    "BOOLEAN",
                    {"default": True, "label_on": "生成音频", "label_off": "不生成音频"},
                ),
                "水印": (
                    "BOOLEAN",
                    {"default": False, "label_on": "带水印", "label_off": "无水印"},
                ),
                "返回尾帧": (
                    "BOOLEAN",
                    {"default": False, "label_on": "返回尾帧", "label_off": "不返回尾帧"},
                ),
            },
            "optional": {
                "图片_1": ("IMAGE",),
                "图片_2": ("IMAGE",),
                "图片_3": ("IMAGE",),
                "图片_4": ("IMAGE",),
                "图片_5": ("IMAGE",),
                "图片_6": ("IMAGE",),
                "图片_7": ("IMAGE",),
                "图片_8": ("IMAGE",),
                "图片_9": ("IMAGE",),
                "图片用途": (
                    ["参考图", "首帧", "首尾帧"],
                    {"default": "参考图"},
                ),
                "种子": (
                    "INT",
                    {
                        "default": -1,
                        "min": -1,
                        "max": 2**32 - 1,
                        "step": 1,
                        "control_after_generate": "randomize",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": get_api_key(),
                        "placeholder": "留空则使用配置文件中的 API Key",
                    },
                ),
            },
        }

    # 图片用途中文到 API role 的映射
    _MODE_MAP = {
        "参考图": "reference_image",
        "首帧": "first_frame",
        "首尾帧": "first_last_frame",
    }

    # 宽高比中文到 API 值的映射
    _RATIO_MAP = {
        "自适应": "adaptive",
    }

    def run(
        self,
        提示词,
        模型,
        分辨率,
        宽高比,
        时长,
        生成音频,
        水印,
        返回尾帧,
        图片_1=None,
        图片_2=None,
        图片_3=None,
        图片_4=None,
        图片_5=None,
        图片_6=None,
        图片_7=None,
        图片_8=None,
        图片_9=None,
        图片用途="参考图",
        种子=-1,
        api_key="",
    ):
        """执行视频生成任务"""

        try:
            # 初始化客户端
            client = SeedanceClient(api_key=api_key if api_key else None)

            # 处理 duration 参数："智能" -> -1
            if 时长 == "智能":
                duration_value = -1
                print("[Ark-Seedance] 时长: 智能指定（-1）")
            else:
                duration_value = int(时长)
            
            # 验证 duration 是否适合当前模型
            self._validate_duration_for_model(duration_value, 模型)

            # 收集所有非空的图像输入
            image_inputs = [图片_1, 图片_2, 图片_3, 图片_4, 图片_5, 
                           图片_6, 图片_7, 图片_8, 图片_9]
            
            # 处理图片输入
            image_list = []
            for img in image_inputs:
                if img is not None:
                    pil_img = self._tensor_to_pil(img)
                    image_list.append(pil_img)

            # 根据用户选择的模式确定图片角色
            api_mode = self._MODE_MAP.get(图片用途, "reference_image")
            roles_list = self._get_roles_by_mode(api_mode, len(image_list))
            
            print(f"[Ark-Seedance] 使用 {len(image_list)} 张图片，模式: {图片用途}")

            # 构建 content
            content = SeedanceClient.build_content(
                text=提示词 if 提示词 else None,
                images=image_list if image_list else None,
                image_roles=roles_list if roles_list else None,
            )

            # 检查 content 是否为空
            if not content:
                raise ValueError("必须提供至少文本或图片作为输入")

            # 宽高比映射
            ratio_value = self._RATIO_MAP.get(宽高比, 宽高比)

            # 构建可选参数
            kwargs = {
                "resolution": 分辨率,
                "ratio": ratio_value,
                "duration": duration_value,
                "generate_audio": 生成音频,
                "watermark": 水印,
                "return_last_frame": 返回尾帧,
            }

            if 种子 != -1:
                kwargs["seed"] = 种子

            # 创建任务
            result = client.create_task(model=模型, content=content, **kwargs)
            task_id = result.get("id", "")

            print(f"[Ark-Seedance] 任务创建成功: {task_id}")

            return (task_id,)

        except Exception as e:
            print(f"[Ark-Seedance] [ERROR] 创建任务失败: {e}")
            raise ValueError(f"创建任务失败: {e}")

    def _get_roles_by_mode(self, mode, image_count):
        """
        根据用户选择的模式返回对应的角色列表
        
        模式说明：
        - first_frame: 首帧模式（所有图都作为首帧）
        - first_last_frame: 首尾帧模式（第1张为首帧，第2张为尾帧，其余为参考图）
        - reference_image: 参考图模式（所有图都作为参考图）
        """
        if image_count == 0:
            return None
            
        if mode == "first_frame":
            if image_count < 1:
                raise ValueError("首帧模式至少需要1张图片")
            return ["first_frame"] * image_count
        elif mode == "first_last_frame":
            if image_count < 2:
                raise ValueError("首尾帧模式需要至少2张图片（首帧+尾帧）")
            roles = ["first_frame", "last_frame"] + ["reference_image"] * (image_count - 2)
            return roles[:image_count]
        elif mode == "reference_image":
            return ["reference_image"] * image_count
        else:
            raise ValueError(f"不支持的模式: {mode}")

    def _validate_duration_for_model(self, duration, model):
        """验证时长是否适合当前模型（2.0 系列：智能 或 4-15 秒）"""
        if duration == -1:
            return
        if duration < 4 or duration > 15:
            raise ValueError(f"模型 {model} 支持的时长范围：4-15 秒")

    def _tensor_to_pil(self, image_tensor):
        """将 ComfyUI Tensor 转为 PIL Image"""
        if len(image_tensor.shape) > 3:
            image_tensor = image_tensor[0]

        array = np.clip(image_tensor.cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(array)


NODE_CLASS_MAPPINGS = {"ArkSeedanceVideoGen": ArkSeedanceVideoGen}
NODE_DISPLAY_NAME_MAPPINGS = {"ArkSeedanceVideoGen": "Ark Seedance 视频生成"}

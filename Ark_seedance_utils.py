"""
Ark Seedance 辅助工具节点
提供图像编码、Base64 转换等功能
"""

import base64
import io

import numpy as np
import torch
from PIL import Image

try:
    from .seedance_client import SeedanceClient
except ImportError:
    from seedance_client import SeedanceClient


class ArkSeedanceImageEncode:
    """图像编码节点 - 将 ComfyUI 图像转为 Base64"""

    DISPLAY_NAME = "Ark Seedance 图像编码"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("base64图像",)
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance/工具"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
            },
        }

    def run(self, 图像):
        """将图像转为 Base64"""
        try:
            # 处理批量图像
            if len(图像.shape) > 3:
                # 多张图像
                base64_list = []
                for i in range(图像.shape[0]):
                    pil_img = self._tensor_to_pil(图像[i])
                    b64 = SeedanceClient.image_to_base64(pil_img)
                    base64_list.append(b64)

                # 合并为多行字符串（每行一个 base64）
                result = "\n".join(base64_list)
                print(f"[Ark-Seedance] 编码 {len(base64_list)} 张图像")
            else:
                # 单张图像
                pil_img = self._tensor_to_pil(图像)
                result = SeedanceClient.image_to_base64(pil_img)
                print("[Ark-Seedance] 编码 1 张图像")

            return (result,)

        except Exception as e:
            print(f"[Ark-Seedance] [ERROR] 图像编码失败: {e}")
            raise ValueError(f"图像编码失败: {e}")

    def _tensor_to_pil(self, image_tensor):
        """将 ComfyUI Tensor 转为 PIL Image"""
        array = np.clip(image_tensor.cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(array)


class ArkSeedanceImageDecode:
    """图像解码节点 - 将 Base64 转为 ComfyUI 图像"""

    DISPLAY_NAME = "Ark Seedance 图像解码"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance/工具"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base64图像": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "rows": 8,
                        "placeholder": "输入 Base64 编码的图像（支持多行，每行一个）",
                    },
                ),
            },
        }

    def run(self, base64图像):
        """将 Base64 转为图像"""
        try:
            # 分割多行
            lines = [line.strip() for line in base64图像.split("\n") if line.strip()]

            tensors = []
            for b64 in lines:
                # 移除 data URI 前缀
                if "," in b64:
                    b64 = b64.split(",", 1)[1]

                # 解码
                img_bytes = base64.b64decode(b64)
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

                # 转为 tensor
                img_array = np.array(pil_img).astype(np.float32) / 255.0
                tensor = torch.from_numpy(img_array).unsqueeze(0)
                tensors.append(tensor)

            # 合并
            result = torch.cat(tensors, dim=0)
            print(f"[Ark-Seedance] 解码 {len(tensors)} 张图像")

            return (result,)

        except Exception as e:
            print(f"[Ark-Seedance] [ERROR] 图像解码失败: {e}")
            raise ValueError(f"图像解码失败: {e}")


class ArkSeedancePromptBuilder:
    """提示词构建节点 - 帮助构建多模态提示词"""

    DISPLAY_NAME = "Ark Seedance 提示词构建"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("content_json",)
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance/工具"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文本": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "rows": 6,
                        "placeholder": "输入文本提示词",
                    },
                ),
            },
            "optional": {
                "图片数量": (
                    "INT",
                    {"default": 0, "min": 0, "max": 9, "step": 1},
                ),
                "图片角色": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "rows": 3,
                        "placeholder": "图片角色（每行一个）：first_frame, last_frame, reference_image",
                    },
                ),
                "包含视频": (
                    "BOOLEAN",
                    {"default": False, "label_on": "包含视频", "label_off": "不包含视频"},
                ),
                "包含音频": (
                    "BOOLEAN",
                    {"default": False, "label_on": "包含音频", "label_off": "不包含音频"},
                ),
            },
        }

    def run(
        self,
        文本,
        图片数量=0,
        图片角色="",
        包含视频=False,
        包含音频=False,
    ):
        """构建 content JSON"""
        try:
            content = []

            # 添加文本
            if 文本:
                content.append({"type": "text", "text": 文本})

            # 添加图片占位符
            if 图片数量 > 0:
                roles = [r.strip() for r in 图片角色.split("\n") if r.strip()]
                for i in range(图片数量):
                    role = roles[i] if i < len(roles) else "reference_image"
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": "{IMAGE_URL_" + str(i + 1) + "}"},
                            "role": role,
                        }
                    )

            # 添加视频占位符
            if 包含视频:
                content.append(
                    {
                        "type": "video_url",
                        "video_url": {"url": "{VIDEO_URL}"},
                        "role": "reference_video",
                    }
                )

            # 添加音频占位符
            if 包含音频:
                content.append(
                    {
                        "type": "audio_url",
                        "audio_url": {"url": "{AUDIO_URL}"},
                        "role": "reference_audio",
                    }
                )

            import json

            result = json.dumps(content, ensure_ascii=False, indent=2)
            print(f"[Ark-Seedance] 构建 content: {len(content)} 个元素")

            return (result,)

        except Exception as e:
            print(f"[Ark-Seedance] [ERROR] 构建提示词失败: {e}")
            raise ValueError(f"构建提示词失败: {e}")


NODE_CLASS_MAPPINGS = {
    "ArkSeedanceImageEncode": ArkSeedanceImageEncode,
    "ArkSeedanceImageDecode": ArkSeedanceImageDecode,
    "ArkSeedancePromptBuilder": ArkSeedancePromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArkSeedanceImageEncode": "Ark Seedance 图像编码",
    "ArkSeedanceImageDecode": "Ark Seedance 图像解码",
    "ArkSeedancePromptBuilder": "Ark Seedance 提示词构建",
}

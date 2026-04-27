"""
Ark Seedance 任务查询节点
查询视频生成任务状态并下载结果
"""

import io
import time
from fractions import Fraction

import numpy as np
import torch
from PIL import Image

try:
    from .config import get_api_base_url, get_api_key, get_poll_interval
    from .seedance_client import SeedanceClient
except ImportError:
    from config import get_api_base_url, get_api_key, get_poll_interval
    from seedance_client import SeedanceClient

# 导入 ComfyUI 内置的 Video 类型
try:
    from comfy_api.latest._input_impl.video_types import VideoFromFile, VideoFromComponents
    from comfy_api.latest._util.video_types import VideoComponents
    HAS_COMFY_VIDEO = True
except ImportError:
    HAS_COMFY_VIDEO = False
    print("[Ark-Seedance] [WARN] 无法导入 ComfyUI Video 类型，视频输出可能不可用")


def _create_empty_video():
    """创建一个最小的空 Video 对象作为占位符"""
    if HAS_COMFY_VIDEO:
        components = VideoComponents(
            images=torch.zeros((1, 64, 64, 3)),
            audio=None,
            frame_rate=Fraction(24),
        )
        return VideoFromComponents(components)
    return None


class ArkSeedanceQueryTask:
    """Seedance 任务查询节点"""

    DISPLAY_NAME = "Ark Seedance 任务查询"
    RETURN_TYPES = ("STRING", "VIDEO", "STRING", "IMAGE")
    RETURN_NAMES = ("状态", "视频", "视频链接", "尾帧")
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "任务ID": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "输入任务 ID",
                    },
                ),
                "自动轮询": (
                    "BOOLEAN",
                    {"default": True, "label_on": "自动轮询", "label_off": "单次查询"},
                ),
                "轮询间隔": (
                    "INT",
                    {"default": 30, "min": 5, "max": 300, "step": 5},
                ),
                "最大等待": (
                    "INT",
                    {"default": 3600, "min": 60, "max": 7200, "step": 60},
                ),
                "api_key": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": get_api_key(),
                        "placeholder": "输入 API Key（自动保存）",
                    },
                ),
                "base_url": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": get_api_base_url(),
                        "placeholder": "API Base URL（默认使用火山方舟官方地址）",
                    },
                ),
            },
        }

    def run(
        self,
        任务ID,
        自动轮询,
        轮询间隔,
        最大等待,
        api_key="",
        base_url="",
    ):
        """查询任务状态"""

        try:
            # 初始化客户端
            client = SeedanceClient(
                api_key=api_key if api_key else None,
                base_url=base_url if base_url else None,
            )

            if not 任务ID:
                raise ValueError("任务 ID 不能为空")

            # 查询或轮询任务
            if 自动轮询:
                print(f"[Ark-Seedance] 开始轮询任务: {任务ID}")
                result = client.poll_task(任务ID, poll_interval=轮询间隔, max_wait=最大等待)
            else:
                print(f"[Ark-Seedance] 查询任务: {任务ID}")
                result = client.get_task_status(任务ID)

            status = result.get("status", "unknown")
            print(f"[Ark-Seedance] 任务状态: {status}")

            # 如果任务成功，下载视频
            video_result = None
            video_url = ""
            last_frame = None

            if status == "succeeded":
                video_url = result.get("content", {}).get("video_url", "")

                if video_url:
                    try:
                        print(f"[Ark-Seedance] 下载视频: {video_url}")
                        video_content = client.download_video(video_url)

                        # 直接用 BytesIO 创建 ComfyUI VideoFromFile 对象
                        # 无需临时文件，无需手动提取帧
                        video_buffer = io.BytesIO(video_content)
                        video_result = VideoFromFile(video_buffer)
                        print(f"[Ark-Seedance] 视频加载成功 ({len(video_content)} bytes)")

                    except Exception as e:
                        print(f"[Ark-Seedance] [WARN] 视频下载/处理失败: {e}")
                        video_result = None

                # 尝试提取尾帧（独立于主视频，失败不影响主流程）
                if result.get("content", {}).get("last_frame_url"):
                    try:
                        last_frame_url = result["content"]["last_frame_url"]
                        last_frame_content = client.download_video(last_frame_url)
                        last_frame = self._bytes_to_tensor(last_frame_content)
                        print("[Ark-Seedance] 成功提取尾帧")
                    except Exception as e:
                        print(f"[Ark-Seedance] [WARN] 尾帧提取失败: {e}")
                        last_frame = None

            elif status == "failed":
                error_info = result.get("error", {})
                error_msg = error_info.get("message", "未知错误")
                print(f"[Ark-Seedance] [ERROR] 任务失败: {error_msg}")

            elif status == "expired":
                print("[Ark-Seedance] [WARN] 任务已过期")

            # 确保返回值不为 None
            if video_result is None:
                print("[Ark-Seedance] [WARN] 视频为空，返回占位 Video")
                video_result = _create_empty_video()

            if last_frame is None:
                last_frame = torch.zeros((1, 64, 64, 3))

            return (status, video_result, video_url, last_frame)

        except Exception as e:
            print(f"[Ark-Seedance] [ERROR] 查询任务失败: {e}")
            raise ValueError(f"查询任务失败: {e}")

    def _bytes_to_tensor(self, img_bytes):
        """从图片字节流转为 ComfyUI IMAGE Tensor (1, H, W, 3)"""
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_array = np.array(pil_img).astype(np.float32) / 255.0
        return torch.from_numpy(img_array).unsqueeze(0)


NODE_CLASS_MAPPINGS = {"ArkSeedanceQueryTask": ArkSeedanceQueryTask}
NODE_DISPLAY_NAME_MAPPINGS = {"ArkSeedanceQueryTask": "Ark Seedance 任务查询"}

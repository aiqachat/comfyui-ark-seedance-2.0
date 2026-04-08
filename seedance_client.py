"""
Seedance API 客户端
封装火山方舟视频生成 API 调用
"""

import base64
import io
import json
import time
from pathlib import Path

import requests
from PIL import Image

try:
    from .config import get_api_base_url, get_api_key, get_max_retries, get_timeout, save_api_key
except ImportError:
    from config import get_api_base_url, get_api_key, get_max_retries, get_timeout, save_api_key


class SeedanceClient:
    """Seedance 视频生成 API 客户端"""

    def __init__(self, api_key=None, base_url=None):
        # 如果用户提供了新的 API Key，保存到配置文件
        if api_key and api_key.strip():
            save_api_key(api_key.strip())
            self.api_key = api_key.strip()
            print(f"[Ark-Seedance] 使用用户输入的 API Key (长度: {len(self.api_key)})，已保存到 master_key.ini")
        else:
            print(f"[Ark-Seedance] 节点未输入 API Key (收到值: {repr(api_key)})，尝试从配置文件读取...")
            self.api_key = get_api_key()
        
        self.base_url = (base_url or get_api_base_url()).rstrip("/")
        self.max_retries = get_max_retries()
        self.timeout = get_timeout()

        if not self.api_key:
            raise ValueError("API Key 未配置，请在节点中输入 API Key 或在 master_key.ini 中设置 api_key")

    def _make_request(self, method, url, **kwargs):
        """发送 HTTP 请求，支持重试"""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"[Ark-Seedance] [WARN] 请求失败 (尝试 {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise last_error or Exception("请求失败")

    def create_task(self, model, content, **kwargs):
        """
        创建视频生成任务

        Args:
            model: 模型 ID
            content: 内容列表（文本、图片、视频、音频）
            **kwargs: 可选参数（resolution, ratio, duration, seed 等）

        Returns:
            dict: 包含任务 ID 的响应
        """
        url = f"{self.base_url}/contents/generations/tasks"

        payload = {
            "model": model,
            "content": content,
        }

        # 添加可选参数
        optional_params = [
            "resolution",
            "ratio",
            "duration",
            "frames",
            "generate_audio",
            "seed",
            "watermark",
            "service_tier",
            "execution_expires_after",
            "return_last_frame",
            "callback_url",
            "draft",
            "tools",
            "safety_identifier",
        ]

        for param in optional_params:
            if param in kwargs and kwargs[param] is not None:
                payload[param] = kwargs[param]

        print(f"[Ark-Seedance] 创建任务: model={model}")

        response = self._make_request("POST", url, json=payload)
        return response.json()

    def get_task_status(self, task_id):
        """
        查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态和结果
        """
        url = f"{self.base_url}/contents/generations/tasks/{task_id}"

        response = self._make_request("GET", url)
        return response.json()

    def poll_task(self, task_id, poll_interval=30, max_wait=3600):
        """
        轮询查询任务直到完成

        Args:
            task_id: 任务 ID
            poll_interval: 轮询间隔（秒）
            max_wait: 最大等待时间（秒）

        Returns:
            dict: 最终任务状态
        """
        start_time = time.time()
        print(f"[Ark-Seedance] 开始轮询任务: {task_id}")

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"任务超时 ({max_wait}秒)")

            result = self.get_task_status(task_id)
            status = result.get("status", "unknown")

            print(f"[Ark-Seedance] 任务状态: {status} (已等待 {int(elapsed)}秒)")

            if status in ("succeeded", "failed", "expired", "cancelled"):
                return result

            time.sleep(poll_interval)

    def download_video(self, url, save_path=None):
        """
        下载生成的视频

        Args:
            url: 视频 URL
            save_path: 保存路径（可选）

        Returns:
            bytes: 视频内容
        """
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)
            print(f"[Ark-Seedance] 视频已保存: {save_path}")

        return response.content

    @staticmethod
    def image_to_base64(image):
        """
        将 PIL Image 或 numpy array 转为 base64

        Args:
            image: PIL Image 或 numpy array

        Returns:
            str: base64 编码的图片
        """
        if isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            # numpy array
            import numpy as np

            img_array = (image * 255.0).clip(0, 255).astype(np.uint8)
            img = Image.fromarray(img_array)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def build_content(
        text=None,
        images=None,
        image_roles=None,
        video_urls=None,
        video_roles=None,
        audio_urls=None,
        audio_roles=None,
    ):
        """
        构建 API 所需的 content 参数

        Args:
            text: 文本提示词
            images: 图片列表（PIL Image 或 numpy array 或 URL 字符串）
            image_roles: 图片角色列表（与 images 对应）
            video_urls: 视频 URL 列表
            video_roles: 视频角色列表（默认 reference_video）
            audio_urls: 音频 URL 列表
            audio_roles: 音频角色列表（默认 reference_audio）

        Returns:
            list: content 数组
        """
        content = []

        # 添加文本
        if text:
            content.append({"type": "text", "text": text})

        # 添加图片
        if images:
            roles = image_roles or ["reference_image"] * len(images)
            for img, role in zip(images, roles):
                if isinstance(img, str):
                    # URL 或 base64
                    if img.startswith("http://") or img.startswith("https://") or img.startswith("data:"):
                        image_url = img
                    elif img.startswith("asset://"):
                        image_url = img
                    else:
                        # 假设是文件路径
                        img_path = Path(img)
                        if img_path.exists():
                            from PIL import Image as PILImage

                            pil_img = PILImage.open(img_path).convert("RGB")
                            image_url = SeedanceClient.image_to_base64(pil_img)
                        else:
                            image_url = img
                else:
                    # PIL Image 或 numpy array
                    image_url = SeedanceClient.image_to_base64(img)

                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                        "role": role,
                    }
                )

        # 添加视频
        if video_urls:
            roles = video_roles or ["reference_video"] * len(video_urls)
            for video_url, role in zip(video_urls, roles):
                content.append(
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url},
                        "role": role,
                    }
                )

        # 添加音频
        if audio_urls:
            roles = audio_roles or ["reference_audio"] * len(audio_urls)
            for audio_url, role in zip(audio_urls, roles):
                content.append(
                    {
                        "type": "audio_url",
                        "audio_url": {"url": audio_url},
                        "role": role,
                    }
                )

        return content

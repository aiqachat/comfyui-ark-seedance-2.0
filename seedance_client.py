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
    from .config import get_api_base_url, get_api_key, get_max_retries, get_timeout, save_api_base_url, save_api_key
except ImportError:
    from config import get_api_base_url, get_api_key, get_max_retries, get_timeout, save_api_base_url, save_api_key


DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class SeedanceClient:
    """Seedance 视频生成 API 客户端"""

    # 常见 API 错误码 → 中文提示
    _ERROR_MESSAGES = {
        "InputImageSensitiveContentDetected.PrivacyInformation": "输入图片包含真实人脸，触发隐私保护限制。请使用不含真人面孔的图片，或在火山方舟控制台检查内容审核设置。",
        "InputImageSensitiveContentDetected": "输入图片包含敏感内容，被安全审核拦截。请更换图片后重试。",
        "InputTextSensitiveContentDetected": "输入文本包含敏感内容，被安全审核拦截。请修改提示词后重试。",
        "OutputVideoSensitiveContentDetected": "生成的视频包含敏感内容，被安全审核拦截。请修改提示词后重试。",
        "InvalidParameter": "请求参数无效，请检查输入参数是否符合模型要求。",
        "RateLimitExceeded": "请求过于频繁，已超出速率限制。请稍后再试。",
        "InsufficientBalance": "账户余额不足。请前往火山方舟控制台充值。",
        "ModelNotFound": "指定的模型不存在或未开通。请检查模型 ID 是否正确。",
        "Unauthorized": "API Key 无效或已过期。请检查 API Key 是否正确。",
    }

    def __init__(self, api_key=None, base_url=None):
        # 如果用户提供了新的 API Key，保存到配置文件
        if api_key and api_key.strip():
            save_api_key(api_key.strip())
            self.api_key = api_key.strip()
            print(f"[Ark-Seedance] 使用用户输入的 API Key (长度: {len(self.api_key)})，已保存到 master_key.ini")
        else:
            print(f"[Ark-Seedance] 节点未输入 API Key (收到值: {repr(api_key)})，尝试从配置文件读取...")
            self.api_key = get_api_key()
        
        # 如果用户提供了新的 Base URL，保存到配置文件
        if base_url and base_url.strip():
            self.base_url = base_url.strip().rstrip("/")
            saved_url = get_api_base_url()
            if self.base_url != saved_url.rstrip("/"):
                save_api_base_url(self.base_url)
                print(f"[Ark-Seedance] Base URL 已更新并保存到 config.ini")
        else:
            self.base_url = get_api_base_url().rstrip("/")

        self.max_retries = get_max_retries()
        self.timeout = get_timeout()
        self._is_default_api = self._check_is_default_api()

        if self._is_default_api:
            print(f"[Ark-Seedance] 使用官方 API: {self.base_url}")
        else:
            print(f"[Ark-Seedance] 使用第三方 API: {self.base_url}")

        if not self.api_key:
            raise ValueError("API Key 未配置，请在节点中输入 API Key 或在 master_key.ini 中设置 api_key")

    def _check_is_default_api(self):
        """判断是否使用火山方舟官方 API"""
        return "ark.cn-beijing.volces.com" in self.base_url

    def _get_friendly_error(self, error_code, api_message):
        """根据 API 错误码返回友好的中文提示"""
        # 精确匹配
        if error_code in self._ERROR_MESSAGES:
            return self._ERROR_MESSAGES[error_code]
        # 前缀匹配（如 InputImageSensitiveContentDetected.XXX）
        for key, msg in self._ERROR_MESSAGES.items():
            if error_code.startswith(key):
                return msg
        # 使用 API 原始消息
        if api_message:
            return f"API 错误: {api_message}"
        return ""

    def _make_request(self, method, url, **kwargs):
        """发送 HTTP 请求，支持重试"""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        last_error = None
        last_error_message = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                # 解析 API 返回的详细错误信息
                error_body = ""
                api_error_code = ""
                api_error_msg = ""
                try:
                    error_body = e.response.text
                    error_data = json.loads(error_body)
                    api_error_code = error_data.get("error", {}).get("code", "")
                    api_error_msg = error_data.get("error", {}).get("message", "")
                except Exception:
                    pass

                last_error = e
                friendly_msg = self._get_friendly_error(api_error_code, api_error_msg)
                last_error_message = friendly_msg or str(e)

                print(f"[Ark-Seedance] [WARN] 请求失败 (尝试 {attempt}/{self.max_retries}): {e}")
                if error_body:
                    print(f"[Ark-Seedance] [WARN] API 错误详情: {error_body}")
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
            except requests.exceptions.RequestException as e:
                last_error = e
                last_error_message = str(e)
                print(f"[Ark-Seedance] [WARN] 请求失败 (尝试 {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise RuntimeError(last_error_message) from last_error

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
        if self._is_default_api:
            return self._create_task_default(model, content, **kwargs)
        else:
            return self._create_task_thirdparty(model, content, **kwargs)

    def _create_task_default(self, model, content, **kwargs):
        """官方 API 请求格式"""
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

        self._log_create_task(model, payload)
        response = self._make_request("POST", url, json=payload)
        return response.json()

    def _create_task_thirdparty(self, model, content, **kwargs):
        """第三方 API 请求格式 — 使用 content 字段包裹原生参数"""
        url = f"{self.base_url}/video/generations"

        payload = {
            "model": model,
            "content": content,
        }

        # 添加可选参数（与第三方 API 兼容的参数）
        optional_params = [
            "resolution",
            "ratio",
            "duration",
            "seed",
            "generate_audio",
            "watermark",
            "return_last_frame",
            "service_tier",
            "stream",
            "callback_url",
        ]

        for param in optional_params:
            if param in kwargs and kwargs[param] is not None:
                payload[param] = kwargs[param]

        self._log_create_task(model, payload)
        response = self._make_request("POST", url, json=payload)
        return response.json()

    def _log_create_task(self, model, payload):
        """打印创建任务的调试日志"""
        debug_payload = json.loads(json.dumps(payload))
        if "content" in debug_payload:
            for item in debug_payload["content"]:
                if item.get("type") == "image_url" and "image_url" in item:
                    url_val = item["image_url"].get("url", "")
                    if url_val.startswith("data:"):
                        item["image_url"]["url"] = f"data:image/...;base64,[{len(url_val)}chars]"
        print(f"[Ark-Seedance] 创建任务: model={model}")
        print(f"[Ark-Seedance] 请求 payload: {json.dumps(debug_payload, ensure_ascii=False, indent=2)}")

    def get_task_status(self, task_id):
        """
        查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态和结果
        """
        if self._is_default_api:
            url = f"{self.base_url}/contents/generations/tasks/{task_id}"
        else:
            url = f"{self.base_url}/video/generations/{task_id}"

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
            print(f"[SeedanceClient] [DEBUG] 接收到 video_urls: {video_urls}")
            roles = video_roles or ["reference_video"] * len(video_urls)
            for video_url, role in zip(video_urls, roles):
                print(f"[SeedanceClient] [DEBUG] 添加视频: {video_url[:80]}... role={role}")
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

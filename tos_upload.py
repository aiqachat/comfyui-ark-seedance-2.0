"""
Ark Seedance TOS 上传节点
将视频/音频/图片上传到火山引擎 TOS 并返回预签名 URL
"""

import mimetypes
import os
import tempfile
import uuid
from datetime import date

import numpy as np
import torch
from PIL import Image

# 导入 ComfyUI Video 类型
try:
    from comfy_api.latest._input_impl.video_types import VideoFromFile, VideoFromComponents
    HAS_COMFY_VIDEO = True
except ImportError:
    HAS_COMFY_VIDEO = False

try:
    from .config import (
        get_tos_access_key,
        get_tos_bucket,
        get_tos_config,
        get_tos_endpoint,
        get_tos_region,
        get_tos_secret_key,
        get_tos_url_expires,
        save_tos_config,
    )
except ImportError:
    from config import (
        get_tos_access_key,
        get_tos_bucket,
        get_tos_config,
        get_tos_endpoint,
        get_tos_region,
        get_tos_secret_key,
        get_tos_url_expires,
        save_tos_config,
    )

VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff")
_NONE_CHOICE = "(none)"


def _import_tos():
    """延迟导入 tos SDK，未安装时给出友好提示"""
    try:
        import tos
        return tos
    except ImportError:
        raise ImportError(
            "TOS SDK 未安装。请运行 `pip install tos` 安装火山引擎 TOS Python SDK。"
        )


def _list_input_files(extensions):
    """扫描 ComfyUI/input/ 目录，返回匹配扩展名的文件列表（含 (none) 选项）"""
    try:
        import folder_paths
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
            and f.lower().endswith(extensions)
        ]
        return [_NONE_CHOICE] + sorted(files)
    except Exception:
        return [_NONE_CHOICE]


def _is_url(value):
    """判断字符串是否为 http(s) URL"""
    if not value or not isinstance(value, str):
        return False
    v = value.strip().strip('"').strip("'")
    return v.startswith("http://") or v.startswith("https://")


def _get_input_dir():
    """获取 ComfyUI/input/ 目录路径"""
    try:
        import folder_paths
        return folder_paths.get_input_directory()
    except Exception:
        return os.path.join(os.getcwd(), "input")


def _resolve_file(dropdown_value, override_value):
    """
    解析媒体文件来源。
    优先级：override_value (非空) > dropdown_value (非 (none))
    返回：文件绝对路径或 URL 字符串，若无有效输入则返回 None
    """
    # 优先使用 override
    if override_value and override_value.strip():
        val = override_value.strip().strip('"').strip("'")
        if _is_url(val):
            return val
        if os.path.isfile(val):
            return val
        # 尝试作为 input/ 目录下的相对路径
        input_dir = _get_input_dir()
        candidate = os.path.join(input_dir, val)
        if os.path.isfile(candidate):
            return candidate
        print(f"[Ark-TosUpload] 警告: override 路径不存在: {val!r}")
        return None

    # 回退到 dropdown
    if dropdown_value and dropdown_value != _NONE_CHOICE:
        input_dir = _get_input_dir()
        path = os.path.join(input_dir, dropdown_value)
        if os.path.isfile(path):
            return path
        print(f"[Ark-TosUpload] 警告: 文件不存在: {path!r}")
        return None

    return None


def _build_object_key(filename):
    """
    生成 TOS Object Key，格式: seedance/{YYYYMMDD}/{uuid12}-{原始文件名}
    """
    safe_name = os.path.basename(filename)
    prefix = date.today().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:12]
    return f"seedance/{prefix}/{unique_id}-{safe_name}"


def _upload_to_tos(client, bucket, file_path, object_key):
    """上传本地文件到 TOS"""
    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        if file_path.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            mime = "video/mp4"
        elif file_path.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg")):
            mime = "audio/mpeg"
        else:
            mime = "application/octet-stream"

    print(f"[Ark-TosUpload] 上传: {os.path.basename(file_path)} -> {object_key} ({mime})")
    client.put_object_from_file(bucket, object_key, file_path)
    print(f"[Ark-TosUpload] 上传成功: {object_key}")
    return object_key


def _get_presigned_url(client, bucket, object_key, expires):
    """生成 GET 预签名 URL"""
    try:
        # 导入 HttpMethodType 枚举
        from tos.enum import HttpMethodType
        http_method = HttpMethodType.Http_Method_Get
        
        url_result = client.pre_signed_url(
            http_method=http_method,
            bucket=bucket,
            key=object_key,
            expires=int(expires),
        )
        
        # 根据 TOS SDK 测试代码，返回对象有 .signed_url 属性
        if hasattr(url_result, 'signed_url'):
            url = url_result.signed_url
            print(f"[Ark-TosUpload] 预签名 URL 生成成功")
            return url
        else:
            # 兜底处理
            print(f"[Ark-TosUpload] [WARN] 返回值类型: {type(url_result)}")
            return str(url_result)
        
    except Exception as e:
        print(f"[Ark-TosUpload] [ERROR] 生成预签名 URL 失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def _upload_image_tensor(client, bucket, tensor, index, expires):
    """
    将 ComfyUI IMAGE tensor 保存为临时 PNG 并上传到 TOS。
    tensor 格式: (H,W,3) 或 (N,H,W,3)
    """
    if tensor is None:
        return None
    if tensor.dim() == 4:
        tensor = tensor[0]

    arr = np.clip(tensor.cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    pil_img = Image.fromarray(arr, "RGB")

    filename = f"image_{index}.png"
    object_key = _build_object_key(filename)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        pil_img.save(tmp_path, format="PNG")

    try:
        _upload_to_tos(client, bucket, tmp_path, object_key)
        url = _get_presigned_url(client, bucket, object_key, expires)
        return url
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _extract_video_path_from_video_object(video_obj):
    """
    从 ComfyUI VIDEO 对象提取文件路径。
    支持 VideoFromFile 和 VideoFromComponents。
    返回临时文件路径（如果数据在内存中）或直接返回原路径。
    """
    if not HAS_COMFY_VIDEO:
        return None

    # VideoFromFile: 包含文件路径或 BytesIO
    if isinstance(video_obj, VideoFromFile):
        # 使用 get_stream_source() 方法获取文件源
        source = video_obj.get_stream_source()
        
        # 检查是否是字符串路径
        if isinstance(source, str):
            return source
        
        # 检查是否是 BytesIO 对象
        if hasattr(source, 'read'):
            # BytesIO 对象，需要保存到临时文件
            filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            with open(tmp_path, 'wb') as f:
                f.write(source.read())
                source.seek(0)  # 重置指针
            print(f"[Ark-TosUpload] VIDEO 对象已保存为临时文件: {tmp_path}")
            return tmp_path
        
        print(f"[Ark-TosUpload] [WARN] VideoFromFile 返回未知类型: {type(source)}")
        return None

    # VideoFromComponents: 包含 VideoComponents
    if isinstance(video_obj, VideoFromComponents):
        print(f"[Ark-TosUpload] [WARN] VideoFromComponents 暂不支持直接提取路径，请改用 'Load Video' 节点")
        return None

    return None


class ArkTosUpload:
    """
    Ark Seedance TOS 上传节点
    --------------------------
    将视频/音频/图片上传到火山引擎 TOS 并返回预签名 URL。

    视频输入（三种方式，优先级从高到低）：
      1. VIDEO 类型输入：直接连接 "Load Video" 等节点的 VIDEO 输出
      2. COMBO 下拉选择：选择 ComfyUI/input/ 下的视频文件
      3. 路径/URL 输入：手动填写视频绝对路径或 http(s) URL

    音频输入（两种方式）：
      1. COMBO 下拉选择：选择 ComfyUI/input/ 下的音频文件
      2. 路径/URL 输入：手动填写音频绝对路径或 http(s) URL

    图片输入：
      - IMAGE tensor：连接 LoadImage 等节点的 IMAGE 输出

    预签名 URL 可直接接入 ArkSeedanceVideoGen 的视频URL/音频URL/图片URL 输入。
    """

    DISPLAY_NAME = "Ark Seedance TOS 上传"
    RETURN_TYPES = ("STRING",) * 15
    RETURN_NAMES = (
        "视频URL_1", "视频URL_2", "视频URL_3",
        "音频URL_1", "音频URL_2", "音频URL_3",
        "图片URL_1", "图片URL_2", "图片URL_3",
        "图片URL_4", "图片URL_5", "图片URL_6",
        "图片URL_7", "图片URL_8", "图片URL_9",
    )
    FUNCTION = "run"
    CATEGORY = "Ark/Seedance/工具"

    @classmethod
    def INPUT_TYPES(cls):
        video_files = _list_input_files(VIDEO_EXTS)
        audio_files = _list_input_files(AUDIO_EXTS)

        video_tip = "选择 ComfyUI/input/ 下的视频文件，或在路径字段填入绝对路径/URL，或连接 VIDEO 类型"
        audio_tip = "选择 ComfyUI/input/ 下的音频文件，或在路径字段填入绝对路径/URL"

        tos = get_tos_config()
        return {
            "required": {
                "tos_bucket": ("STRING", {
                    "multiline": False,
                    "default": tos.get("tos_bucket", ""),
                    "placeholder": "TOS Bucket 名称",
                }),
                "url_expires": ("INT", {
                    "default": tos.get("url_expires", 3600),
                    "min": 60,
                    "max": 604800,
                    "step": 60,
                    "tooltip": "预签名 URL 过期时间（秒），默认 3600",
                }),
            },
            "optional": {
                # TOS 凭证（覆盖默认配置）
                "tos_access_key": ("STRING", {
                    "multiline": False,
                    "default": tos.get("tos_access_key", ""),
                    "placeholder": "TOS Access Key（留空则使用配置默认值）",
                }),
                "tos_secret_key": ("STRING", {
                    "multiline": False,
                    "default": tos.get("tos_secret_key", ""),
                    "placeholder": "TOS Secret Key（留空则使用配置默认值）",
                }),
                "tos_endpoint": ("STRING", {
                    "multiline": False,
                    "default": tos.get("tos_endpoint", "tos-cn-beijing.volces.com"),
                    "placeholder": "TOS Endpoint",
                }),
                "tos_region": ("STRING", {
                    "multiline": False,
                    "default": tos.get("tos_region", "cn-beijing"),
                    "placeholder": "TOS Region",
                }),

                # 视频输入（3 个槽位）- 支持三种输入方式
                # 1. COMBO 下拉选择
                "视频_1": (video_files, {"default": _NONE_CHOICE, "tooltip": video_tip}),
                "视频路径_1": ("STRING", {"multiline": False, "default": "", "placeholder": "视频绝对路径或 http(s) URL"}),
                # 2. VIDEO 类型输入（来自 Load Video 节点）
                "视频输入_1": ("VIDEO", {"tooltip": "连接 VIDEO 类型输出，如 'Load Video' 节点"}),
                "视频_2": (video_files, {"default": _NONE_CHOICE, "tooltip": video_tip}),
                "视频路径_2": ("STRING", {"multiline": False, "default": "", "placeholder": "视频绝对路径或 http(s) URL"}),
                "视频输入_2": ("VIDEO", {"tooltip": "连接 VIDEO 类型输出，如 'Load Video' 节点"}),
                "视频_3": (video_files, {"default": _NONE_CHOICE, "tooltip": video_tip}),
                "视频路径_3": ("STRING", {"multiline": False, "default": "", "placeholder": "视频绝对路径或 http(s) URL"}),
                "视频输入_3": ("VIDEO", {"tooltip": "连接 VIDEO 类型输出，如 'Load Video' 节点"}),

                # 音频输入（3 个槽位）
                "音频_1": (audio_files, {"default": _NONE_CHOICE, "tooltip": audio_tip}),
                "音频路径_1": ("STRING", {"multiline": False, "default": "", "placeholder": "音频绝对路径或 http(s) URL"}),
                "音频_2": (audio_files, {"default": _NONE_CHOICE, "tooltip": audio_tip}),
                "音频路径_2": ("STRING", {"multiline": False, "default": "", "placeholder": "音频绝对路径或 http(s) URL"}),
                "音频_3": (audio_files, {"default": _NONE_CHOICE, "tooltip": audio_tip}),
                "音频路径_3": ("STRING", {"multiline": False, "default": "", "placeholder": "音频绝对路径或 http(s) URL"}),

                # 图片输入（9 个槽位）
                "图片_1": ("IMAGE",), "图片_2": ("IMAGE",), "图片_3": ("IMAGE",),
                "图片_4": ("IMAGE",), "图片_5": ("IMAGE",), "图片_6": ("IMAGE",),
                "图片_7": ("IMAGE",), "图片_8": ("IMAGE",), "图片_9": ("IMAGE",),
            },
        }

    def run(
        self,
        tos_bucket,
        url_expires,
        tos_access_key="",
        tos_secret_key="",
        tos_endpoint="",
        tos_region="",
        视频_1=_NONE_CHOICE, 视频路径_1="", 视频输入_1=None,
        视频_2=_NONE_CHOICE, 视频路径_2="", 视频输入_2=None,
        视频_3=_NONE_CHOICE, 视频路径_3="", 视频输入_3=None,
        音频_1=_NONE_CHOICE, 音频路径_1="",
        音频_2=_NONE_CHOICE, 音频路径_2="",
        音频_3=_NONE_CHOICE, 音频路径_3="",
        图片_1=None, 图片_2=None, 图片_3=None,
        图片_4=None, 图片_5=None, 图片_6=None,
        图片_7=None, 图片_8=None, 图片_9=None,
    ):
        """执行上传"""

        tos = _import_tos()

        # 收集凭证（节点输入优先，回退配置）
        ak = tos_access_key.strip() if tos_access_key else get_tos_access_key()
        sk = tos_secret_key.strip() if tos_secret_key else get_tos_secret_key()
        ep = tos_endpoint.strip() if tos_endpoint else get_tos_endpoint()
        rg = tos_region.strip() if tos_region else get_tos_region()
        bucket = tos_bucket.strip()

        # 验证凭证
        missing = []
        if not ak:
            missing.append("tos_access_key")
        if not sk:
            missing.append("tos_secret_key")
        if not bucket:
            missing.append("tos_bucket")
        if not ep:
            missing.append("tos_endpoint")
        if not rg:
            missing.append("tos_region")
        if missing:
            raise ValueError(
                f"TOS 配置不完整，缺少: {', '.join(missing)}。"
                "请在节点中输入或在 config.ini / master_key.ini 中配置。"
            )

        # 保存用户输入的配置到配置文件（用于下次自动填充）
        print(f"[Ark-TosUpload] 保存 TOS 配置到配置文件...")
        save_tos_config(
            access_key=ak,
            secret_key=sk,
            endpoint=ep,
            region=rg,
            bucket=bucket,
            url_expires=url_expires,
        )

        print(f"[Ark-TosUpload] 初始化 TOS 客户端: region={rg}, endpoint={ep}, bucket={bucket}")
        try:
            client = tos.TosClientV2(ak, sk, ep, rg)
        except Exception as e:
            raise RuntimeError(f"TOS 客户端初始化失败: {e}")

        # 辅助：上传单个文件/URL
        def _process_file(dropdown, override, media_type):
            """
            处理单个文件输入。
            返回 URL 字符串或 None。
            """
            source = _resolve_file(dropdown, override)
            if source is None:
                return None

            # URL 直接透传
            if _is_url(source):
                print(f"[Ark-TosUpload] {media_type}: URL 透传 → {source}")
                return source

            # 本地文件上传
            if not os.path.isfile(source):
                print(f"[Ark-TosUpload] 警告: 文件不存在，跳过: {source}")
                return None

            object_key = _build_object_key(os.path.basename(source))
            try:
                _upload_to_tos(client, bucket, source, object_key)
                url = _get_presigned_url(client, bucket, object_key, url_expires)
                return url
            except Exception as e:
                print(f"[Ark-TosUpload] 上传失败 {source}: {e}")
                return None

        # 辅助：处理 VIDEO 类型输入
        def _process_video_object(video_obj, media_type):
            """
            处理 VIDEO 类型对象。
            返回 URL 字符串或 None。
            """
            if video_obj is None:
                return None

            # 从 VIDEO 对象提取文件路径
            file_path = _extract_video_path_from_video_object(video_obj)
            if file_path is None:
                print(f"[Ark-TosUpload] {media_type}: 无法从 VIDEO 对象提取文件路径")
                return None

            # 上传到 TOS
            if not os.path.isfile(file_path):
                print(f"[Ark-TosUpload] {media_type}: 临时文件不存在: {file_path}")
                return None

            object_key = _build_object_key(os.path.basename(file_path))
            try:
                _upload_to_tos(client, bucket, file_path, object_key)
                url = _get_presigned_url(client, bucket, object_key, url_expires)
                
                # 清理临时文件（如果是从 BytesIO 创建的）
                if file_path.startswith(tempfile.gettempdir()):
                    try:
                        os.remove(file_path)
                        print(f"[Ark-TosUpload] {media_type}: 已清理临时文件: {file_path}")
                    except OSError:
                        pass
                
                return url
            except Exception as e:
                print(f"[Ark-TosUpload] {media_type} 上传失败: {e}")
                return None

        # 处理视频（3 个槽位）- 优先使用 VIDEO 输入，其次使用 dropdown/override
        video_results = []
        video_inputs = [
            (视频_1, 视频路径_1, 视频输入_1, "视频_1"),
            (视频_2, 视频路径_2, 视频输入_2, "视频_2"),
            (视频_3, 视频路径_3, 视频输入_3, "视频_3"),
        ]
        
        for i, (dd, ov, video_obj, name) in enumerate(video_inputs, 1):
            # 优先处理 VIDEO 对象
            if video_obj is not None and HAS_COMFY_VIDEO:
                url = _process_video_object(video_obj, name)
                if url:
                    video_results.append(url)
                    continue
            
            # 回退到 dropdown/override
            url = _process_file(dd, ov, name)
            video_results.append(url or "")

        # 处理音频（3 个槽位）
        audio_results = []
        for i, (dd, ov) in enumerate([
            (音频_1, 音频路径_1),
            (音频_2, 音频路径_2),
            (音频_3, 音频路径_3),
        ], 1):
            url = _process_file(dd, ov, f"音频_{i}")
            audio_results.append(url or "")

        # 处理图片（9 个槽位）
        image_tensors = [图片_1, 图片_2, 图片_3, 图片_4, 图片_5, 图片_6, 图片_7, 图片_8, 图片_9]
        image_results = []
        for i, tensor in enumerate(image_tensors, 1):
            if tensor is None:
                image_results.append("")
                continue
            try:
                url = _upload_image_tensor(client, bucket, tensor, i, url_expires)
                image_results.append(url or "")
            except Exception as e:
                print(f"[Ark-TosUpload] 图片上传失败 (图片_{i}): {e}")
                image_results.append("")

        # 汇总
        all_urls = video_results + audio_results + image_results
        uploaded = sum(1 for u in all_urls if u)
        print(f"[Ark-TosUpload] 完成: {uploaded}/15 个 URL")

        return tuple(all_urls)


NODE_CLASS_MAPPINGS = {"ArkTosUpload": ArkTosUpload}
NODE_DISPLAY_NAME_MAPPINGS = {"ArkTosUpload": "Ark Seedance TOS 上传"}

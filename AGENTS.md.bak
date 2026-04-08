# ComfyUI 自定义节点开发规则

## 项目结构

```
plugin_directory/
├── __init__.py              # 插件入口，负责节点发现与注册
├── Ark_*.py                 # 各节点实现文件（每个 .py 文件是一个独立节点）
├── config.ini               # 用户配置（自动创建，更新时保留）
├── master_key.ini           # 敏感密钥存储（与 config 分离）
├── web/
│   ├── ark_video_ui.js      # 前端 UI 扩展
│   └── ark_node_tutorials.js # 节点教程数据
└── .update_meta.json        # 更新元信息
```

## 核心规范

### 1. 节点类定义

每个节点类必须包含以下属性：

```python
class ArkNodeExample:
    DISPLAY_NAME = "节点显示名称"      # UI 中显示的名称
    RETURN_TYPES = ("IMAGE", "STRING") # 返回类型元组
    RETURN_NAMES = ("输出1", "输出2")  # 输出端口名称
    FUNCTION = "run"                   # 执行方法名
    CATEGORY = "Ark"                   # 节点分类

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": { ... },   # 必填输入
            "optional": { ... },   # 可选输入
            "hidden": { ... },     # 隐藏输入（如 prompt、extra_pnginfo）
        }

    def run(self, **inputs):
        # 节点执行逻辑
        return (result1, result2)
```

### 2. 节点注册方式

在节点文件末尾定义映射：

```python
NODE_CLASS_MAPPINGS = {"ClassName": ClassName}
NODE_DISPLAY_NAME_MAPPINGS = {"ClassName": "显示名称"}
```

`__init__.py` 会自动扫描所有 `.py` 文件并通过 `_discover_nodes()` 发现节点类。

### 3. INPUT_TYPES 字段规范

#### 必填字段 (required)

| 类型 | 格式 | 示例 |
|------|------|------|
| 字符串 | `("STRING", {"multiline": True, "default": "", "rows": 8})` | 多行文本 |
| 下拉选项 | `(["option1", "option2"], {"default": "option1"})` | 单选 |
| 整数 | `("INT", {"default": 0, "min": 0, "max": 2147483647})` | 数值输入 |
| 布尔值 | `("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭"})` | 开关 |
| IMAGE | `"IMAGE"` | 图像输入 |

#### 隐藏字段 (hidden)

用于接收 ComfyUI 系统数据：
```python
"hidden": {
    "prompt": "PROMPT",
    "extra_pnginfo": "EXTRA_PNGINFO",
}
```

### 4. 配置管理

#### 配置文件分离
- `config.ini`: 普通配置（API Key、中继地址等）
- `master_key.ini`: 敏感密钥（单独存储，加锁保护）

#### 配置读写模式
```python
import configparser
import threading
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("config.ini")
CONFIG_LOCK = threading.Lock()
CONFIG = configparser.ConfigParser()

# 自动创建配置文件
if CONFIG_PATH.exists():
    CONFIG.read(CONFIG_PATH, encoding="utf-8")
else:
    CONFIG["DEFAULT"] = {}
    with CONFIG_PATH.open("w", encoding="utf-8") as fp:
        CONFIG.write(fp)
```

### 5. 图像处理规范

#### Tensor 转 PIL
```python
def tensor_to_pil(image_tensor):
    if len(image_tensor.shape) > 3:
        image_tensor = image_tensor[0]
    array = np.clip(image_tensor.cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(array)
```

#### PIL 转 Tensor
```python
img_np = np.array(img).astype(np.float32) / 255.0
tensor = torch.from_numpy(img_np)
return (torch.stack([tensor]),)  # 返回元组包裹的 batch
```

#### 图像下载重试
```python
def download_image_with_retry(url, max_retries=3, timeout=120):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, timeout=timeout, verify=False)
            if res.status_code == 200:
                return Image.open(io.BytesIO(res.content)).convert("RGB")
        except Exception as exc:
            last_error = exc
        if attempt < max_retries:
            time.sleep(2 ** attempt)
    raise last_error or Exception("下载失败")
```

### 6. API 请求处理

#### 请求函数
```python
def make_request(method, url, timeout=600, **kwargs):
    kwargs.setdefault("verify", False)
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response
```

#### 响应解析（兼容多种格式）
- OpenAI 格式: `{"data": [{"url": "...", "b64_json": "..."}]}`
- Gemini 格式: `{"candidates": [{"content": {"parts": [{"inlineData": {...}}]}}]}`
- Chat 格式: `{"choices": [{"message": {"content": "..."}}]}`

### 7. 并发请求

使用 `ThreadPoolExecutor` 实现并发生图：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _dispatch_requests(self, func, configs, prompts, merge=True):
    tasks = [(config, prompt) for config, prompt in zip(configs, prompts)]
    results = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(func, config, prompt): idx
            for idx, (config, prompt) in enumerate(tasks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                print(f"[WARN] 请求 #{idx + 1} 失败: {exc}")

    # 过滤 None 结果
    valid_results = [r for r in results if r is not None]
    return self._merge_results(valid_results) if merge else results
```

### 8. 插件更新机制

`__init__.py` 中内置了自更新功能：

- 通过 GitHub API 检查远程提交
- 下载 ZIP 覆盖更新
- 保留本地配置文件（`config.ini`, `master_key.ini` 等）
- 注册 HTTP 路由 `/cy_nodes/updater/status` 和 `/cy_nodes/updater/update`

### 9. 前端扩展 (JavaScript)

#### 扩展注册
```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CY.BananaPro.Fold",

    async nodeCreated(node) {
        if (!TARGET_NODES.includes(node.comfyClass)) {
            return;
        }
        // 节点创建时的自定义逻辑
    },
});
```

#### 前端自定义功能
- 在节点标题栏绘制操作按钮（教程、在线生图等）
- 控件联动（切换中继网址时动态过滤模型选项）
- 密码输入掩码（Key 字段自动设为 `type="password"`）
- 弹窗教程（分步指导、目录导航）
- 令牌自动创建（调用 API 并自动填入）

### 10. 日志规范

统一使用 `[前缀]` 格式：
```python
print(f"[Ark视频生成] 创建任务: model={model_value}")
print(f"[WARN] 视频下载失败 (尝试 {attempt}/{max_retries})")
print(f"[ERROR] API 返回 {response.status_code}")
print(f"[OK] 成功加载节点文件")
```

## 注意事项

1. **类型返回**: 所有输出必须包裹在元组中，如 `return (image_tensor,)`
2. **多输出节点**: 使用 `RETURN_TYPES` 定义多个输出类型，返回对应长度的元组
3. **可选输出**: 未生成的输出端口返回 `None`
4. **批量处理**: 图像使用 batch 维度 (`torch.stack`) 合并
5. **错误处理**: 关键错误抛出 `ValueError`，非关键错误打印 `[WARN]` 并继续
6. **线程安全**: 配置文件写入使用 `threading.Lock()` 保护
7. **SSL 验证**: API 请求设置 `verify=False`（中继服务可能使用自签证书）
8. **超时设置**: 生图 API 设置较长超时（600 秒 / 10 分钟）
9. **配置持久化**: 节点控件值自动保存回 `config.ini`，下次加载时作为默认值

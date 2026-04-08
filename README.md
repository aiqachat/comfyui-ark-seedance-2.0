# Ark Seedance 2.0 - ComfyUI 视频生成插件

火山方舟 Seedance 系列视频生成模型的 ComfyUI 自定义节点。

## 功能特性

- ✅ 文生视频（Text-to-Video）
- ✅ 图生视频-首帧（Image-to-Video）
- ✅ 图生视频-首尾帧
- ✅ 多模态参考生视频（图片 + 视频 + 音频）
- ✅ 支持 Seedance 2.0 / 2.0 fast / 1.5 pro / 1.0 系列
- ✅ 有声/无声视频生成
- ✅ 视频尾帧提取（用于连续视频串联）
- ✅ 异步任务轮询
- ✅ 图像 Base64 编码/解码

## 安装

1. 将本文件夹复制到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone <repository_url> ark-comfyui-0
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置 API Key：

**方式一：通过节点输入（推荐）**
- 在 ComfyUI 中添加 "Ark Seedance Video Gen" 节点
- 在节点的 `api_key` 字段中输入您的 API Key
- API Key 会自动保存到 `master_key.ini` 文件

**方式二：手动编辑配置文件**
- 编辑 `master_key.ini` 文件，填入您的火山方舟 API Key：

```ini
[DEFAULT]
api_key = your_api_key_here
```

获取 API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey

## 节点说明

### 1. Ark Seedance Video Gen

**功能**: 创建视频生成任务

**输入**:
- `prompt`: 视频生成提示词
- `model`: 模型选择
- `image_1` ~ `image_9`: 参考图像（可选，最多9张独立输入端口）
- `image_usage_mode`: 图片使用模式（reference_image/first_frame/first_last_frame，默认 reference_image）
- `resolution`: 分辨率（480p/720p/1080p）
- `ratio`: 宽高比
- `duration`: 视频时长（auto/4-15秒，默认 auto；根据模型动态更新选项）
- `generate_audio`: 是否生成音频
- `watermark`: 是否添加水印
- `return_last_frame`: 是否返回尾帧
- `seed`: 随机种子

**输出**:
- `task_id`: 任务 ID（连接到查询节点）

**时长设置说明**:

| 选项 | 说明 | 支持的模型 |
|------|------|-----------|
| `auto` | 智能指定时长（模型自动选择合适的时长） | Seedance 2.0/2.0 fast、Seedance 1.5 pro |
| `4`~`15` | 具体时长（秒） | 所有模型（范围因模型而异） |

**各模型时长范围**:

| 模型系列 | 时长范围 | 智能指定 |
|---------|---------|---------|
| Seedance 2.0 / 2.0 fast | 4-15 秒 | ✅ 支持（auto） |
| Seedance 1.5 pro | 4-12 秒 | ✅ 支持（auto） |
| Seedance 1.0 pro / pro fast | 2-12 秒 | ❌ 不支持 |
| Seedance 1.0 lite | 2-12 秒 | ❌ 不支持 |

**图片使用模式说明**:

| 模式 | 说明 | 图片数量要求 | 角色分配 |
|------|------|------------|---------|
| `reference_image` | 参考图模式（默认） | 1-9张 | 所有图片作为参考图 |
| `first_frame` | 首帧模式 | 1-9张 | 所有图片作为首帧 |
| `first_last_frame` | 首尾帧模式 | 至少2张 | 第1张为首帧，第2张为尾帧，其余为参考图 |

**使用建议**:
- 文生视频：不连接任何图片输入
- 图生视频（首帧）：连接1张图片，选择 `first_frame` 模式
- 图生视频（首尾帧）：连接2张图片，选择 `first_last_frame` 模式
- 多模态参考：连接多张图片，选择 `reference_image` 模式（默认）

### 2. Ark Seedance Query Task

**功能**: 查询任务状态并下载视频

**输入**:
- `task_id`: 任务 ID
- `auto_poll`: 是否自动轮询
- `poll_interval`: 轮询间隔（秒）
- `max_wait`: 最大等待时间（秒）

**输出**:
- `status`: 任务状态（succeeded/failed/expired）
- `video`: 视频帧序列（VIDEO 类型，可连接 SaveVideo 或 Preview）
- `video_url`: 视频下载链接
- `last_frame`: 尾帧图像（可选）

### 3. Ark Seedance Image Encode

**功能**: 将 ComfyUI 图像转为 Base64

### 4. Ark Seedance Image Decode

**功能**: 将 Base64 转为 ComfyUI 图像

### 5. Ark Seedance Prompt Builder

**功能**: 帮助构建多模态提示词

## 使用示例

### 文生视频

```
[Ark Seedance Video Gen]
  prompt: "一只猫在草地上奔跑"
  model: doubao-seedance-2-0-260128
  resolution: 720p
  ratio: 16:9
  duration: 5
  generate_audio: False

       ↓ task_id

[Ark Seedance Query Task]
  auto_poll: True
  poll_interval: 30

       ↓ video

[SaveVideo] 或 [VHS_VideoCombine]
```

### 图生视频（首帧）

```
[Load Image] → image_1 → [Ark Seedance Video Gen]
  prompt: "镜头缓慢推进，展示细节"
  image_usage_mode: first_frame  ← 选择首帧模式

       ↓ task_id

[Ark Seedance Query Task] → video → [SaveVideo]
```

### 图生视频（首尾帧）

```
[Load Image 1] → image_1 → [Ark Seedance Video Gen]
[Load Image 2] → image_2 →   image_usage_mode: first_last_frame  ← 选择首尾帧模式
  prompt: "从场景A平滑过渡到场景B"

       ↓ task_id

[Ark Seedance Query Task] → video → [SaveVideo]
```

### 多模态参考生视频

```
[Load Image 1] → image_1 →
[Load Image 2] → image_2 → [Ark Seedance Video Gen]
[Load Image 3] → image_3 →   image_usage_mode: reference_image  ← 参考图模式（默认）
  prompt: "[图1]男生和[图2]小狗坐在[图3]草坪上"

       ↓ task_id

[Ark Seedance Query Task] → video → [SaveVideo]
```

### 多模态参考（图片+视频+音频）- Seedance 2.0

```
[Images] ──
           ├→ [Ark Seedance Video Gen]
[Videos] ──┤   image_usage_mode: reference_image（默认）
[Audio]  ──┘   
  prompt: "全程使用视频1的第一视角构图..."

       ↓ task_id

[Ark Seedance Query Task] → video → [SaveVideo]
```

## 支持的模型

| 模型 ID | 说明 | 最高分辨率 | 时长范围 |
|---------|------|-----------|---------|
| doubao-seedance-2-0-260128 | 最高品质 | 720p | 4-15秒 |
| doubao-seedance-2-0-fast-260128 | 快速版本（50%价格） | 720p | 4-15秒 |
| doubao-seedance-1-5-pro | 中等能力 | 1080p | 4-12秒 |
| doubao-seedance-1-0-pro | 基础能力 | 1080p | 2-12秒 |
| doubao-seedance-1-0-pro-fast | 快速版本 | 1080p | 2-12秒 |
| doubao-seedance-1-0-lite-t2v | 轻量文生视频 | 720p | 2-12秒 |
| doubao-seedance-1-0-lite-i2v | 轻量图生视频 | 720p | 2-12秒 |

## 配置说明

### config.ini（普通配置）

```ini
[DEFAULT]
api_base_url = https://ark.cn-beijing.volces.com/api/v3
poll_interval = 30
max_retries = 3
timeout = 600
```

### master_key.ini（敏感密钥）

```ini
[DEFAULT]
api_key = your_api_key_here
```

## 注意事项

1. **API 限流**: Seedance 2.0 限制 600 RPM，10 并发
2. **任务有效期**: 生成的任务 ID 仅保存 7 天
3. **请求体大小**: 整个请求体不超过 64 MB
4. **图片要求**: 
   - 格式：JPEG, PNG, WebP 等
   - 宽高比：0.4-2.5
   - 尺寸：300-6000 px
   - 单张大小：< 30 MB
5. **视频要求**（作为参考输入时）:
   - 格式：MP4, MOV
   - 时长：2-15 秒
   - 分辨率：480p, 720p
6. **音频要求**（作为参考输入时）:
   - 格式：WAV, MP3
   - 时长：2-15 秒

## 故障排除

### 问题：API Key 未配置

**解决**: 
- 方式一：在任意 Seedance 节点的 `api_key` 输入框中输入 API Key，会自动保存
- 方式二：手动编辑 `master_key.ini` 文件，设置 `api_key` 字段

### 问题：任务创建失败

**解决**:
1. 检查 API Key 是否正确
2. 确认模型 ID 正确
3. 检查提示词是否符合要求
4. 查看控制台错误信息

### 问题：视频下载失败

**解决**:
1. 检查网络连接
2. 确认任务状态为 succeeded
3. 增加 timeout 配置

## 参考文档

- [Seedance 2.0 API 文档](https://www.volcengine.com/docs/82379/1520757)
- [SDK 示例](https://www.volcengine.com/docs/82379/2291680)
- [获取 API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)
- [提示词指南](https://www.volcengine.com/docs/82379/2222480)

## 许可证

MIT License

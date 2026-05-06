# Ark Seedance 2.0 - ComfyUI 视频生成插件

火山方舟 Seedance 2.0 视频生成模型的 ComfyUI 自定义节点。

## 功能特性

- 文生视频（Text-to-Video）
- 图生视频-首帧（Image-to-Video）
- 图生视频-首尾帧
- 多模态参考生视频（图片参考 / 视频参考 / 音频参考 / 组合参考）
- 编辑视频 / 延长视频
- 生成有声视频
- 联网搜索增强
- 返回视频尾帧（用于连续视频串联）
- 异步任务轮询
- 支持 Seedance 2.0 和 Seedance 2.0 fast 两个模型
- 支持自定义 API Base URL（兼容第三方 API 代理）

## 支持的模型

| 模型 ID | 说明 | 分辨率 | 时长 |
|---------|------|--------|------|
| doubao-seedance-2-0-260128 | Seedance 2.0 标准版 | 480p, 720p | 4-15 秒 |
| doubao-seedance-2-0-fast-260128 | Seedance 2.0 快速版 | 480p, 720p | 4-15 秒 |

两个模型功能完全一致，fast 版本生成速度更快、价格更低。

## 安装

1. 克隆到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/aiqachat/ark-seedance-2.0-comfyui.git
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 重启 ComfyUI

## 配置 API Key

**方式一：节点输入（推荐）**

在节点的 `api_key` 字段中输入你的 API Key，运行一次后会自动保存到 `master_key.ini`，之后重启 ComfyUI 也会自动填充。

**方式二：手动编辑配置文件**

编辑 `master_key.ini` 文件：

```ini
[DEFAULT]
api_key = your_api_key_here
```

获取 API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey

## 配置 API Base URL

默认使用火山方舟官方地址 `https://ark.cn-beijing.volces.com/api/v3`，也支持配置第三方 API 代理地址。

**方式一：节点输入（推荐）**

在节点的 `base_url` 字段中修改地址，运行一次后会自动保存到 `config.ini`。

**方式二：手动编辑配置文件**

编辑 `config.ini` 文件：

```ini
[DEFAULT]
api_base_url = https://your-proxy.example.com/v1
```

**智能路由说明：**

插件会根据 Base URL 自动选择请求方式：

| Base URL | 创建任务端点 | 查询任务端点 | 请求格式 |
|----------|------------|------------|---------|
| 默认（`ark.cn-beijing.volces.com`） | `/contents/generations/tasks` | `/contents/generations/tasks/{id}` | 官方格式 |
| 自定义（第三方） | `/video/generations` | `/video/generations/{id}` | 使用 `content` 包裹参数 |

当使用第三方 API 时，插件会将原生的 `content` 数组（包含 text、image_url、video_url、audio_url 等）直接传递到请求体的 `content` 字段中，实现参数透传。

## 节点说明

### Ark Seedance 视频生成

创建视频生成任务。

**输入参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| 提示词 | STRING | 视频生成提示词，支持中英文，建议中文不超过 500 字 |
| 模型 | 下拉选择 | `doubao-seedance-2-0-260128` / `doubao-seedance-2-0-fast-260128` |
| 分辨率 | 下拉选择 | `480p` / `720p` |
| 宽高比 | 下拉选择 | 自适应 / 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16 |
| 时长 | 下拉选择 | 智能（模型自动选择）/ 4~15 秒 |
| 生成音频 | 布尔 | 是否生成有声视频 |
| 水印 | 布尔 | 是否添加水印 |
| 返回尾帧 | 布尔 | 是否返回视频尾帧 |
| 图片_1~9 | IMAGE（可选） | 参考图像，最多 9 张 |
| 图片用途 | 下拉选择 | 参考图 / 首帧 / 首尾帧 |
| 种子 | INT（可选） | 随机种子，-1 表示随机 |
| api_key | STRING | API Key，留空则从配置文件读取 |
| base_url | STRING | API Base URL，默认使用火山方舟官方地址，修改后自动保存 |

**输出：** 任务ID（STRING）

**图片用途说明：**

| 模式 | 说明 | 图片要求 |
|------|------|---------|
| 参考图（默认） | 所有图片作为参考图 | 1-9 张 |
| 首帧 | 所有图片作为首帧 | 至少 1 张 |
| 首尾帧 | 第 1 张为首帧，第 2 张为尾帧，其余为参考图 | 至少 2 张 |

### Ark Seedance 任务查询

查询任务状态并下载视频结果。

**输入参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| 任务ID | STRING | 从视频生成节点获取 |
| 自动轮询 | 布尔 | 开启后自动等待任务完成 |
| 轮询间隔 | INT | 轮询间隔秒数，默认 30 |
| 最大等待 | INT | 最大等待秒数，默认 3600 |
| api_key | STRING | 同上 |
| base_url | STRING | API Base URL，需与视频生成节点保持一致 |

**输出：**

| 输出 | 类型 | 说明 |
|------|------|------|
| 状态 | STRING | succeeded / failed / expired |
| 视频 | VIDEO | 可连接 SaveVideo 节点保存 |
| 视频链接 | STRING | 视频下载 URL |
| 尾帧 | IMAGE | 视频最后一帧（需开启返回尾帧） |

### Ark Seedance 图像编码

将 ComfyUI IMAGE 转为 Base64 字符串。

### Ark Seedance 图像解码

将 Base64 字符串转为 ComfyUI IMAGE。

### Ark Seedance 提示词构建

辅助构建多模态提示词。

## 使用示例

### 文生视频

```
[Ark Seedance 视频生成]
  提示词: "一只猫在草地上奔跑"
  模型: doubao-seedance-2-0-260128
  分辨率: 720p
  宽高比: 16:9
  时长: 5

       ↓ 任务ID

[Ark Seedance 任务查询]
  自动轮询: 开

       ↓ 视频

[SaveVideo]
```

### 图生视频（首帧）

```
[Load Image] → 图片_1 → [Ark Seedance 视频生成]
                          图片用途: 首帧
                          提示词: "镜头缓慢推进，展示细节"

       ↓ 任务ID

[Ark Seedance 任务查询] → 视频 → [SaveVideo]
```

### 图生视频（首尾帧）

```
[Load Image 1] → 图片_1 → [Ark Seedance 视频生成]
[Load Image 2] → 图片_2 →   图片用途: 首尾帧
                             提示词: "从场景A平滑过渡到场景B"

       ↓ 任务ID

[Ark Seedance 任务查询] → 视频 → [SaveVideo]
```

### 多模态参考

```
[Load Image 1] → 图片_1 →
[Load Image 2] → 图片_2 → [Ark Seedance 视频生成]
[Load Image 3] → 图片_3 →   图片用途: 参考图
                             提示词: "[图1]男生和[图2]小狗坐在[图3]草坪上"

       ↓ 任务ID

[Ark Seedance 任务查询] → 视频 → [SaveVideo]
```

## 配置文件

### config.ini

```ini
[DEFAULT]
# 默认使用火山方舟官方地址，修改为第三方地址后会自动切换请求格式
api_base_url = https://ark.cn-beijing.volces.com/api/v3
poll_interval = 30
max_retries = 3
timeout = 600
```

### master_key.ini（已被 .gitignore 忽略）

```ini
[DEFAULT]
api_key = your_api_key_here
```

## 注意事项

1. **API 限流**: Seedance 2.0 限制 600 RPM，10 并发
2. **任务有效期**: 任务 ID 保存 7 天
3. **请求体大小**: 不超过 64 MB
4. **图片要求**: JPEG/PNG/WebP，宽高比 0.4-2.5，尺寸 300-6000px，单张 < 30MB
5. **视频参考要求**: MP4/MOV，2-15 秒，480p/720p
6. **音频参考要求**: WAV/MP3，2-15 秒

## 参考文档

- [Seedance 2.0 API 文档](https://www.volcengine.com/docs/82379/1520757)
- [获取 API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)
- [提示词指南](https://www.volcengine.com/docs/82379/2222480)

## 许可证

MIT License

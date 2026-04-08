# Ark Seedance 2.0 ComfyUI 插件 - 项目规划总结

## 项目概述

本项目是一个 ComfyUI 自定义节点插件，让用户可以在 ComfyUI 中直接使用火山方舟 Seedance 2.0 系列视频生成模型。

## 已完成的工作

### 1. 项目结构

```
ark-comfyui-0/
├── __init__.py                    # 插件入口，自动发现和注册节点
├── config.py                      # 配置管理模块（线程安全）
├── config.ini                     # 普通配置文件（自动创建）
├── master_key.ini                 # API Key 存储（敏感信息）
├── seedance_client.py             # Seedance API 客户端封装
├── Ark_seedance.py               # 主视频生成节点
├── Ark_seedance_query.py         # 任务查询节点
├── Ark_seedance_utils.py         # 辅助工具节点（3个）
├── requirements.txt              # Python 依赖
├── README.md                     # 使用文档
├── test_project.py               # 测试脚本
└── web/
    ├── ark_seedance_ui.js        # 前端 UI 扩展
    └── ark_seedance_tutorials.js # 节点教程数据
```

### 2. 节点清单（6个节点）

#### 核心节点

| 节点类名 | 显示名称 | 功能 |
|---------|---------|------|
| ArkSeedanceVideoGen | Ark Seedance Video Gen | 创建视频生成任务 |
| ArkSeedanceQueryTask | Ark Seedance Query Task | 查询任务状态并下载视频 |

#### 辅助节点

| 节点类名 | 显示名称 | 功能 |
|---------|---------|------|
| ArkSeedanceImageEncode | Ark Seedance Image Encode | 图像转 Base64 |
| ArkSeedanceImageDecode | Ark Seedance Image Decode | Base64 转图像 |
| ArkSeedancePromptBuilder | Ark Seedance Prompt Builder | 构建多模态提示词 |

### 3. 支持的模型（7个）

| 模型 ID | 说明 | 最高分辨率 | 时长范围 |
|---------|------|-----------|---------|
| doubao-seedance-2-0-260128 | 最高品质 | 720p | 4-15秒 |
| doubao-seedance-2-0-fast-260128 | 快速版本 | 720p | 4-15秒 |
| doubao-seedance-1-5-pro | 中等能力 | 1080p | 4-12秒 |
| doubao-seedance-1-0-pro | 基础能力 | 1080p | 2-12秒 |
| doubao-seedance-1-0-pro-fast | 快速版本 | 1080p | 2-12秒 |
| doubao-seedance-1-0-lite-t2v | 轻量文生视频 | 720p | 2-12秒 |
| doubao-seedance-1-0-lite-i2v | 轻量图生视频 | 720p | 2-12秒 |

### 4. 支持的功能

- ✅ 文生视频（Text-to-Video）
- ✅ 图生视频-首帧（Image-to-Video，1张图自动判断）
- ✅ 图生视频-首尾帧（2张图自动判断）
- ✅ 多模态参考生视频（3-9张图自动判断）
- ✅ 智能场景判断（根据图片数量自动选择场景）
- ✅ 多模态输入（图片 + 视频 + 音频）
- ✅ 有声/无声视频生成
- ✅ 视频尾帧提取（用于连续视频串联）
- ✅ 异步任务轮询
- ✅ 图像 Base64 编码/解码
- ✅ 动态参数调整（模型切换时自动更新可用选项）
- ✅ 配置持久化
- ✅ 错误重试机制

#### 4.1 智能场景判断规则

| 图片数量 | 自动判断场景 | 角色分配 | 说明 |
|---------|------------|---------|------|
| 0张 | 文生视频 | - | 纯文本生成 |
| 1张 | 图生视频-首帧 | first_frame | 以图为起始帧 |
| 2张 | 图生视频-首尾帧 | first_frame + last_frame | 定义开始和结束 |
| 3-9张 | 多模态参考生视频 | reference_image × N | 多张参考图 |

**注意**: 三种场景（首帧、首尾帧、参考图）为互斥场景，不可混用。自动判断模式会根据图片数量自动选择正确的场景。

### 5. 技术实现亮点

#### 5.1 相对导入兼容
所有模块使用 try-except 处理相对导入，既能在 ComfyUI 包环境中运行，也能独立测试。

#### 5.2 配置分离
- `config.ini`: 普通配置（API URL、超时等）
- `master_key.ini`: 敏感密钥（单独存储）
- 线程安全的配置读写

#### 5.3 异步任务处理
- 创建任务返回 task_id
- 查询节点支持自动轮询和单次查询两种模式
- 可配置轮询间隔和最大等待时间

#### 5.4 视频处理
- 使用 OpenCV 提取视频帧
- 自动均匀采样
- 转为 ComfyUI Tensor 格式

#### 5.5 前端扩展
- 模型切换时自动更新可用参数范围
- 防止用户选择无效参数组合

### 6. 配置示例

#### config.ini
```ini
[DEFAULT]
api_base_url = https://ark.cn-beijing.volces.com/api/v3
poll_interval = 30
max_retries = 3
timeout = 600
```

#### master_key.ini
```ini
[DEFAULT]
api_key = your_api_key_here
```

### 7. 使用流程

```
1. 配置 API Key
   ↓
2. 使用 ArkSeedanceVideoGen 创建任务
   ↓ (输出 task_id)
3. 使用 ArkSeedanceQueryTask 查询状态
   ↓ (输出 video_frames, video_url)
4. 使用 Preview 或 Video Combine 查看/保存视频
```

### 8. 测试验证

运行 `python test_project.py` 通过所有测试：
- ✓ 项目结构完整
- ✓ 配置模块正常
- ✓ API 客户端基本功能正常

### 9. 依赖项

```
requests>=2.28.0        # HTTP 请求
Pillow>=9.0.0          # 图像处理
numpy>=1.21.0          # 数值计算
torch>=1.12.0          # ComfyUI 图像 Tensor
opencv-python>=4.7.0   # 视频帧提取
```

## API 参考

- [Seedance 2.0 API 文档](https://www.volcengine.com/docs/82379/1520757)
- [SDK 示例](https://www.volcengine.com/docs/82379/2291680)
- [获取 API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

## 下一步

项目已完整，可以直接使用：

1. 编辑 `master_key.ini` 配置您的 API Key
2. 将本项目复制到 ComfyUI 的 `custom_nodes` 目录
3. 安装依赖：`pip install -r requirements.txt`
4. 重启 ComfyUI

## 注意事项

1. API 限流：Seedance 2.0 限制 600 RPM，10 并发
2. 任务有效期：生成的任务 ID 仅保存 7 天
3. 图片要求：格式 JPEG/PNG 等，尺寸 300-6000px，单张 < 30MB
4. 视频要求（参考输入）：MP4/MOV，2-15秒，480p/720p
5. 2.0 系列模型不支持 1080p 和离线推理

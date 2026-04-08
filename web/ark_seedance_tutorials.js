/**
 * Ark Seedance 节点教程数据
 */

const TUTORIALS = {
  ArkSeedanceVideoGen: {
    title: "Seedance 视频生成节点",
    steps: [
      {
        title: "配置 API Key",
        content:
          "首次使用前，请在 master_key.ini 文件中配置您的火山方舟 API Key。获取地址：https://console.volcengine.com/ark/region:ark+cn-beijing/apikey",
      },
      {
        title: "输入提示词",
        content:
          "在 prompt 字段输入视频生成提示词。支持中英文，建议中文不超过 500 字，英文不超过 1000 词。提示词应详细描述想要的视频内容。",
      },
      {
        title: "选择模型",
        content:
          "根据需求选择模型：\n- doubao-seedance-2-0-260128: 最高品质（推荐）\n- doubao-seedance-2-0-fast-260128: 快速版本（50% 价格）\n- doubao-seedance-1-5-pro: 中等能力\n- 其他 1.0 系列模型",
      },
      {
        title: "配置参数",
        content:
          "设置分辨率（480p/720p/1080p）、宽高比、时长、是否生成音频等参数。注意：2.0 系列模型不支持 1080p。",
      },
      {
        title: "添加参考图像（可选）",
        content:
          "连接 images 输入端口提供参考图。可设置 image_roles 定义每张图片的角色：\n- first_frame: 首帧\n- last_frame: 尾帧\n- reference_image: 参考图\n\nSeedance 2.0 支持 1-9 张参考图。",
      },
      {
        title: "执行节点",
        content:
          "点击 Queue Prompt 执行节点。节点会创建视频生成任务并返回 task_id。使用查询节点来获取最终视频。",
      },
    ],
  },

  ArkSeedanceQueryTask: {
    title: "Seedance 任务查询节点",
    steps: [
      {
        title: "输入任务 ID",
        content:
          "将视频生成节点输出的 task_id 连接到本节点的 task_id 输入端。",
      },
      {
        title: "选择查询模式",
        content:
          "- auto_poll: True 时自动轮询直到任务完成\n- auto_poll: False 时仅查询一次当前状态",
      },
      {
        title: "配置轮询参数",
        content:
          "- poll_interval: 轮询间隔（秒），默认 30 秒\n- max_wait: 最大等待时间（秒），默认 3600 秒（1小时）",
      },
      {
        title: "获取结果",
        content:
          "任务完成后：\n- status: succeeded/failed/expired\n- video_frames: 视频帧序列（ComfyUI 图像 batch）\n- video_url: 视频下载链接\n- last_frame: 尾帧图像（如果请求了）",
      },
    ],
  },

  ArkSeedanceImageEncode: {
    title: "图像编码节点",
    steps: [
      {
        title: "连接输入图像",
        content: "将需要编码的 ComfyUI 图像连接到 images 输入端。",
      },
      {
        title: "获取 Base64",
        content:
          "节点输出 Base64 编码的图像。多张图像时，每行一个 Base64 字符串。",
      },
    ],
  },

  ArkSeedanceImageDecode: {
    title: "图像解码节点",
    steps: [
      {
        title: "输入 Base64",
        content:
          "输入 Base64 编码的图像数据。支持多行，每行自动解码为一张图像。",
      },
      {
        title: "获取图像",
        content: "输出解码后的 ComfyUI 图像 batch，可连接到其他图像处理节点。",
      },
    ],
  },

  ArkSeedancePromptBuilder: {
    title: "提示词构建节点",
    steps: [
      {
        title: "输入文本提示词",
        content: "输入描述想要生成视频内容的文本提示词。",
      },
      {
        title: "配置多模态输入",
        content:
          "- image_count: 图片数量（0-9）\n- image_roles: 每张图片的角色（每行一个）\n- has_video: 是否包含参考视频\n- has_audio: 是否包含参考音频",
      },
      {
        title: "获取 Content JSON",
        content:
          "输出符合 API 格式的 content JSON，包含文本和图片占位符。",
      },
    ],
  },
};

// 导出教程数据
if (typeof module !== "undefined" && module.exports) {
  module.exports = TUTORIALS;
}

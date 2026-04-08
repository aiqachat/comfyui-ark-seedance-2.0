/**
 * Ark Seedance UI 扩展
 * 为 Seedance 节点提供增强的 UI 功能
 */

import { app } from "../../scripts/app.js";

// 目标节点列表
const TARGET_NODES = [
  "ArkSeedanceVideoGen",
  "ArkSeedanceQueryTask",
  "ArkSeedanceImageEncode",
  "ArkSeedanceImageDecode",
  "ArkSeedancePromptBuilder",
];

app.registerExtension({
  name: "Ark.Seedance",

  async nodeCreated(node) {
    if (!TARGET_NODES.includes(node.comfyClass)) {
      return;
    }

    console.log(`[Ark-Seedance] 节点创建: ${node.comfyClass}`);

    // 为 API Key 字段设置密码掩码
    setupApiKeyMask(node);

    // 根据节点类型应用自定义逻辑
    switch (node.comfyClass) {
      case "ArkSeedanceVideoGen":
        setupVideoGenNode(node);
        break;
      case "ArkSeedanceQueryTask":
        setupQueryTaskNode(node);
        break;
      case "ArkSeedancePromptBuilder":
        setupPromptBuilderNode(node);
        break;
    }
  },
});

/**
 * 为 API Key 字段设置密码掩码
 * 注意：不能直接修改 widget.type，否则 ComfyUI 无法正确序列化值
 * 改为通过 DOM 元素设置 input type="password"
 */
function setupApiKeyMask(node) {
  const apiKeyWidget = node.widgets?.find((w) => w.name === "api_key");
  if (apiKeyWidget) {
    // 保存原始 draw 方法，在 widget 渲染后设置 input 类型
    const originalDraw = apiKeyWidget.draw;
    let masked = false;
    apiKeyWidget.draw = function (ctx, node, width, y, height) {
      if (originalDraw) {
        originalDraw.call(this, ctx, node, width, y, height);
      }
      // 当 DOM input 元素可用时，设置为 password 类型
      if (!masked && this.inputEl) {
        this.inputEl.type = "password";
        masked = true;
        console.log("[Ark-Seedance] API Key 字段已设置为密码掩码模式");
      }
    };
  }
}

/**
 * 设置视频生成节点
 */
function setupVideoGenNode(node) {
  console.log("[Ark-Seedance] 视频生成节点已设置");
}

/**
 * 设置任务查询节点
 */
function setupQueryTaskNode(node) {
  // 可以在这里添加自定义按钮或状态显示
  console.log("[Ark-Seedance] 任务查询节点已设置");
}

/**
 * 设置提示词构建节点
 */
function setupPromptBuilderNode(node) {
  console.log("[Ark-Seedance] 提示词构建节点已设置");
}

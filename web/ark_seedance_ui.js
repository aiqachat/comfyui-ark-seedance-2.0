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
 * 通过定时检查 DOM input 元素来设置 password 类型
 * 不修改 widget 的 draw/type 等属性，避免破坏渲染
 */
function setupApiKeyMask(node) {
  const apiKeyWidget = node.widgets?.find((w) => w.name === "api_key");
  if (!apiKeyWidget) return;

  // 定时检查 inputEl 是否可用
  let attempts = 0;
  const interval = setInterval(() => {
    attempts++;
    if (apiKeyWidget.inputEl) {
      apiKeyWidget.inputEl.type = "password";
      clearInterval(interval);
      console.log("[Ark-Seedance] API Key 字段已设置为密码掩码模式");
    }
    if (attempts > 50) {
      clearInterval(interval);
    }
  }, 100);
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

# 多模型与额度效率

Origin Companion 0.2.2 按模型能力调整 MCP 接口。模型仍由 Claude、Codex、WorkBuddy 或其他宿主选择；插件没有内置模型 API 客户端，不保存模型密钥，不发起额外付费推理。预设不是模型检测，也不能让不支持工具调用的聊天界面获得 MCP 能力。

本机主用配置为 **GPT-5.6 Terra + max 推理**，按用户已确认的使用成本保留 max。额度优化集中于工具定义、按需说明、批量原生执行和减少 GUI 往返。模型推理设置由宿主应用执行，插件预设只向 Agent 提供此偏好；其他模型仍按实际能力选择接口与视觉配置。

## 两种接口，同一个 Origin 内核

| 模式 | 面向模型的工具 | 使用场景与代价 |
| --- | --- | --- |
| `economy` | 5 个：状态、短参数配方、按需说明、通用调用、文件/预览 | 常规任务、较小模型、额度紧张；首次使用复杂操作需要查询一次参数说明 |
| `full` | 14 个，完整类型化参数直接列出 | 连续复杂编程、宿主不擅长 JSON 字符串调用；初始工具上下文更大 |

经济模式通过 `origin_call(operation, arguments_json)` 访问完整模式的全部操作，复用相同的 Pydantic 校验、任务去重、版本保护、检查点与单进程 Origin 执行队列。通用调用按具有写入和外部访问能力标记，宿主不会误认为它是只读工具。固定绘图/线性拟合使用直接的 `origin_recipe` 工具，不要求模型编写 JSON 字符串或 Python。

配方只接受已经检查过的数据集与列名；拟合必须明确截距及权重。`action=run` 一次完成校验和提交，不新增审批轮次。错误会返回简短字段提示，不自动修复 JSON、不自动重放 GUI，也不自动切换昂贵模型。复杂多面板、误差棒、Beer–Lambert、非线性拟合继续使用完整工作流/程序入口。保存的文件不被摘要裁剪；文本读取按页返回 `next_offset`。

2026-09-11 的本地协议测量：完整模式工具定义 **19,514 UTF-8 字节**，经济模式 **4,372 字节**，减少 **77.60%**。测量是紧凑 JSON 的工具定义，不包含聊天、技能、动态说明和图片；**不是实际计费 token 或费用降低比例**。运行 `scripts/benchmark_profiles.py --output <report.json>` 可复核。不同操作组合可能让完整模式更省调用次数，不能保证经济模式每次都更便宜。

## 能力配置

```powershell
$originInstall = Get-Content -Raw "$env:USERPROFILE\.origin-agent\install.json" | ConvertFrom-Json
& $originInstall.executable configure-model gpt-terra --profile economy --vision auto
```

该命令只更新 `.origin-agent/agent-profile.json`，保留一次旧配置备份；重连 MCP 后生效。指定 `--profile full` 即可恢复直接工具接口。也可为每个宿主分别使用 `serve --profile economy --model-preset deepseek --vision off`，或设置 `ORIGIN_AGENT_PROFILE`、`ORIGIN_AGENT_MODEL_PRESET`、`ORIGIN_AGENT_VISION`。优先级是命令行 > 环境变量 > 本机配置 > 默认完整模式。

`vision=off` 在工具入口拒绝图片预览和截图驱动输入，保留 Origin 原生程序、UIA 文本控件、菜单与数值回读。`auto` 要求 Agent 自行确认当前模型和宿主能读取图片；`on` 表示操作者已经选择支持图片的组合，两者都不是视觉能力实测。截图操作仍需最新观察、目标窗口及前台校验。视觉能力不是某一品牌所有型号的共同属性。

| 预设 | 推荐起点 | 宿主必须处理的差异 |
| --- | --- | --- |
| `deepseek` | economy；纯文本型号用 off | 使用兼容的工具调用适配器；严格模式对 JSON Schema 子集另有要求，不把任意 MCP Schema 直接标成 strict |
| `gpt-terra` | economy + max 推理；复杂连续编辑可比较 full | 宿主选择 `gpt-5.6-terra` 和 `max`；保留用户主用推理强度，优化工具上下文和往返，插件不改变账户设置 |
| `gemini` | economy + auto | 保留完整调用 ID、工具结果及 thought signatures；不手工丢弃签名 |
| `glm` | economy；文本型号 off | 交错思考时保留 `reasoning_content`，正确组装流式参数；视觉型号单独确认 |
| `kimi` | economy；多模态型号 auto | 明确步骤、提供操作样例、保留宿主要求的工具上下文；历史文本型号不假设有视觉 |
| `elm` | economy；先检查账户可用型号 | 在支持自定义 ELM API 和 MCP 的宿主接入；ELM 网页聊天不自动等于本地 MCP Agent |

这些是接口配置和宿主要求，**不是上述模型已完成真实 API 测评的声明**。配置七种预设后的本地协议校验、短参数工作流、全部操作的 Schema 可达性和文字模式限制均有自动测试；模型选择正确率、科学判断与实际 token 费用必须用具体账户/型号另测。

## 模型测评门槛

使用同一组合任务比较 economy/full：CSV 散点图、自由截距校准、明确零截距校准、单位缺失的追问、非线性拟合、继续编辑 OPJU、过期 GUI 观察恢复、模型不支持图像的降级。输入只用合成数据。记录成功率、Origin 数值回读、项目可重开、工具错误/重试次数、时间、提供商实际输入/缓存/输出/推理 token 及实际价格。

不能用工具调用返回成功替代图像/科学质量评审；不能在额度比较中省略失败重试、工具说明和截图。任务变更时才扩展测评。当前未使用任何人的模型额度进行上述跨提供商实测，也没有自动上传实验数据。

## 官方依据（核对日期：2026-09-11）

- [DeepSeek 工具调用与严格模式](https://api-docs.deepseek.com/guides/tool_calls/)：工具执行由应用完成；严格模式由提供商适配层选择。
- [OpenAI GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)：支持工具调用、结构化输出与图像输入；定位于智能和成本平衡。
- [Gemini 工具调用签名](https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures)：使用该 API 时按原样保留所需签名；其他 API 应遵循各自规则。
- [GLM 思考模式](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode)：交错工具调用需要保留推理上下文，思考设置由宿主控制。
- [Kimi 提示最佳实践](https://platform.moonshot.ai/docs/guide/prompt-best-practice)：明确步骤、样例、相关说明按需使用。
- [ELM 模型及额度边界](ELM.md)。

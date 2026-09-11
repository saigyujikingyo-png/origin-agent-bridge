# 爱丁堡大学 ELM

公开信息核对日期：**2026-09-11**。以下来自大学官方页面的公开检索内容；没有登录个人 ELM 账户或使用 API Key 探测实际权限。

ELM 是学校提供的多模型服务入口。官方说明向全体学生和教职员工免费提供，并可在 ELM 内申请 API Key。这表示 ELM 服务访问，不是发放可转到个人 OpenAI、DeepSeek 等账户的通用 token 余额。[官方介绍](https://information-services.ed.ac.uk/computing/comms-and-collab/elm/elm-competence-centre/introduction-to-elm)

| 接入 | 官方公开目录中的代表型号 |
| --- | --- |
| 网页聊天 | GPT-5.5、GPT-5.4、GPT-5.4-mini/nano，以及早期 GPT/o 系列 |
| 网页聊天 | Gemini-3.1-flash-lite、Gemini-3.1-pro；本地托管 Llama 3.3、EuroLLM |
| API | 目录明确列出 GPT-5.5/5.5-pro、GPT-5.4/5.4-pro/mini/nano、GPT-5/mini/nano、GPT-4.1；编码类别列出 GPT-5.3-codex |

目录还描述可通过 API 使用本地托管和 OpenAI 模型。但它**没有明确列出 GPT-5.6 Terra、DeepSeek、GLM、Kimi**；不能把概括性“完整模型系列”当作特定账户的权限证据。Gemini 出现在网页聊天栏目，不能据此确认每个 Gemini 型号也可通过该账户 API 调用。[官方模型目录](https://information-services.ed.ac.uk/computing/elm/elm_competence_centre/elm-models-available-through-the-api)

**未核实到统一的每人每月 token 数、速率限制或 API 无限额度承诺。** 上下文窗口表示单次任务可容纳的输入规模，和账户免费配额不是同一个概念。实际型号、请求限制及用途规则应以申请页面、个人控制台或 ELM 团队确认结果为准；此插件没有把商业 API 标价计作学生应支付费用。

使用 Origin Companion 时，选择支持自定义模型 API 且支持本地 MCP 的 Agent；在该 Agent 的安全配置中填写 ELM 颁发的 Key 和官方提供的地址，选择获准的模型，然后连接本机 Origin Companion。官方有 [Python/API 接入示例](https://information-services.ed.ac.uk/computing/elm/elm-competence-centre/examples-of-how-to-use-elm-with-python-and-elm-api-key/interacting-with-elm-using-python-and-the-elm-api)。不要假设 ELM 网页聊天本身能安装本地 MCP 插件，不要把 Key 写入本仓库或分享包。

每位同学/教授使用自己的 ELM 身份与本机有效 Origin 授权。可分享插件，不共享学校账号或 API Key。Origin Companion 的模型配置不申请额度、不代为开通模型、不产生新的模型推理账单；实际推理由所选 Agent/服务计量。

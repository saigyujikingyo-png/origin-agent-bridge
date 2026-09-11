# 验收记录

日期：2026-09-11。版本：0.1.0。测试输入全部是合成数据，不是实际实验结果。当前交付为已通过本机原生验收的早期版本。

已验证本机 Origin 2026b SR2，10.350243，64 位，普通版，非 Demo。官方 originpro 1.1.15 / OriginExt 1.2.5 能创建独立实例。

原生验收脚本 `scripts/verify_native.py` 通过真正的 stdio MCP 连接执行文件检查、批量规划、任务队列、拟合与导出，再读取项目索引和 PNG 预览。它还重复提交同一计划以验证去重，并保存机器可读 acceptance.json。

## 当前结果

| 验收项 | 结果 |
|---|---|
| 自动化测试 | Windows Python 3.12：19 passed，14.54 秒；ruff 检查通过 |
| 干净 CI 环境 | GitHub Actions Ubuntu / Windows 均通过依赖锁定安装、ruff 和全部 19 项测试；[运行记录](https://github.com/saigyujikingyo-png/origin-agent-bridge/actions/runs/34565734250) |
| 安装包独立性 | 已安装的冻结 EXE；PATH 仅保留 System32，清除 PYTHONPATH/PYTHONHOME 后执行成功 |
| 路径适配 | 数据/作业目录包含中文与空格，完整流程通过 |
| 原生执行 | 3 张图，2 次线性拟合；覆盖自由截距、零截距、误差棒、多 Y、Beer–Lambert 未知样品 |
| 保存与核对 | OPJU 重开成功，全部数据列哈希一致，3 张图及 2 个原生报告存在 |
| 数值 | Origin 的系数、RSS、样本数通过独立最小二乘校验；误差列未被偷偷用作权重 |
| 产物 | OPJU、3 组 PNG/PDF/SVG、2 组拟合 JSON 与残差 CSV、来源与验证 manifest |
| 图片 | PNG 可解码；人工视觉检查第 1、3 图：标签、误差棒、图例、曲线清晰，图例未遮挡数据 |
| 去重 | 同一计划重复提交返回原 job ID |
| MCP | 8 个工具；SDK 进程内、真实 stdio 自动/legacy 协商及回环 Streamable HTTP 通过 |
| HTTP | 外来 Host 请求被拒绝 |
| 工件读取 | 哈希篡改与路径穿越被拒绝 |

上述安装版原生任务的冷启动 MCP 连接为 2.235 秒；Origin 连接、计算、导出、重开核对耗时 46.578 秒；包含数据检查、计划、任务等待与图片读取的总时间为 52.344 秒。这是一次实际测量，不是吞吐量或延迟保证。此前独立安装包同类任务约 27 秒，机器负载和 Origin 首次启动会影响时间。

工具清单序列化共 7,969 个字符。它不是实际模型 token 数，更不能据此宣称节省了某一比例的账户费用。发布 ZIP/MCPB 约 31.22 MiB，无额外模型 API 依赖。

单元/协议测试覆盖缺失科学参数、无效数值、文件范围、快照与计划篡改、Excel 公式、已知数值解、并发去重、取消、设备锁、Windows 共享句柄重试，以及官方 SDK 的进程内和真实 stdio/HTTP 连接。

## 宿主安装与账号验收

已从 Claude Desktop、WorkBuddy 和 Codex 已安装缓存读取各自的真实启动配置，使用官方 MCP Client 逐一连接：全部发现 8 个工具并成功调用 `origin_status`；三个配置均使用同一 `.origin-agent/inbox`。这是启动命令/协议验收，不能替代宿主 UI 中的模型调用验收。

- Codex：`origin-agent@personal` 0.1.0 已安装；新会话才能加载该插件。
- Claude Desktop：已备份并合并专用 MCP 配置；需要宿主重启并进行模型调用验收。
- WorkBuddy 5.3.5：已备份并合并用户 `mcp.json`，安装了工作流 skill；原有服务保留。日志证明该配置是连接器刷新来源。仍需宿主模型调用验收。
- ChatGPT：已经创建并关联私有隧道，安装开发者插件，发现全部 8 个工具。官方 Windows tunnel-client 0.0.14 已校验 SHA-256 并安装；受管进程 process_running / healthy / ready 均为 true。仅 Tunnels Read/Use 的密钥由用户创建，关闭全部模型 API 权限，并存于本机加密文件。
- ChatGPT 自然语言端到端：已经实际执行合成数据导入、计划、Origin OLS、导出、工程重开、项目检查、PNG 附件显示和结果报告。云端发起的作业 ID 为 `22dffe6f92f04e22b4daf7036ee32971`，原生阶段 20.469 秒；斜率 0.2004，截距 0.0992，RSS 0.0002304，OPJU 130,284 字节。
- 此次云端测试中，模型首次填写了错误字段，验证器拒绝后模型自行修正，未进入错误的原生计算。PNG 附件显示需要一次 ChatGPT 文件实体化许可。本次没有直接验证在云端下载 OPJU，原文件可在 Windows 本机打开。
- 多电脑：包内无硬编码开发机运行路径，安装器在目标电脑生成路径；尚无第二台实体电脑的实测证据。

安装版作业 ID：`ac399f49e7d44c95908dbf313a510e8c`。完整 acceptance.json 和 OPJU 留在验证电脑本地，不包含在源码仓库中。

实体第二台电脑、其他 Origin 版本、Claude/WorkBuddy/Codex 内的最终模型调用仍需分别实测，不能从协议测试或 ChatGPT 的成功推定全部通过。
# 0.2 开发分支：通用接口原型

2026-09-11，本机源码原型通过 29 项单元/协议测试、Ruff、插件清单和 skill 格式校验。实际 Origin 仍为 2026b SR2 10.350243 普通版；以下通过官方 MCP Client 调用源码服务，再由独立 Worker 调用实际 Origin。

| 案例 | 实际结果 | 原生耗时 |
|---|---|---|
| Python 非线性 ExpDec1 拟合 | 无噪声合成数据恢复 A1=2、t1=1.4、y0=0.3；报表、曲线、OPJU 和图像生成；数值与预期检查通过 | 23.641 s |
| 从 OPJU 副本继续编辑 | 成功修改轴标题并再次保存/重开，工程结构一致 | 14.250 s |
| LabTalk / X-Functions | newbook、列运算、total 求和得到 55，type 日志回传，后置条件通过 | 13.094 s |
| Origin C | 在本机编译函数，调用后回读 square(7)=49，后置条件通过 | 12.578 s |

代码与文档已纠正两项实际接口差异：LabTalk `sum` 返回累计和数据集，求总和应使用 `total` 或 `sum.total`；`run.LoadOC` 在此版本需要 Windows 反斜杠路径，正斜杠返回代码 3。未满足预期的测试均曾被标记为失败，没有交付错误结果。`type` 日志无法捕获所有 X-Function `-h` 输出，文档已明确此边界。

本机初次能力检索发现 799 个 X-Function 文件、305 个拟合函数文件和 305 个 Python API 索引项。这是发现数量，不是授权数量、已验收数量或全功能覆盖率。原生拟合图像已人工/Agent 查看。通用程序的工程检查仅验证结构重开，不包含完整数值往返和独立科学模型校验。

证据保留在验证电脑 `.origin-agent/verification/general-source-020/acceptance-programs.json`。新代码未构建安装包、未替换当前已安装的 0.1.0，未测试新工具在 ChatGPT/Claude/WorkBuddy 内的模型调用，也未验收完整 GUI 与教授/学生多电脑使用。不能把下面 0.1 的发行证据自动套用到新代码。

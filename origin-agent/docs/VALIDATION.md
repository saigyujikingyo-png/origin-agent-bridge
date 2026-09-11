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

证据保留在验证电脑 `.origin-agent/verification/general-source-020/acceptance-programs.json`。新代码未构建安装包、未替换当前已安装的 0.1.0，未测试新工具在 ChatGPT/Claude/WorkBuddy 内的模型调用，也未验收完整 GUI 与教授/学生多电脑使用。不能把前述 0.1 的发行证据自动套用到新代码。

## 个人分享目标与候选实测

用户进一步明确只针对其爱大授权的这个 Origin 版本，供个人分享给同学和教授。开发版据此加入指定构建号、位数、许可类型与非 Demo 检查，不再泛化宣称支持所有历史版本。加入版本检查后，本地单元/协议测试为 37 项通过；未探测的安装与已验证的目标明确区分，状态中的完整功能验收标志仍为 false。

指定版本检查加入后，四项原生 MCP 案例再次全部通过：非线性拟合 21.51 秒、OPJU 继续编辑 14.23 秒、LabTalk 11.75 秒、Origin C 11.66 秒。新证据为项目忽略目录 `.local/target-020-native/acceptance-programs.json`；这个结果仍只覆盖上述案例。

独立安装并实测 Ge-Shun/origin-mcp 0.1.4 的结果见 [候选评估](CANDIDATE_EVALUATION.md)。严格验收完成 17 次 MCP 调用，8 项检查通过、1 项失败；失败是外层成功、实际未执行的结构化非线性拟合。原始证据位于项目忽略目录 `.local/candidate-validation/run-02/candidate-report.json`，不是本项目已通过的发行验收。

## 0.2 开发分支：持续会话第一阶段

2026-09-11，按 [实施方案](IMPLEMENTATION_PLAN.md) 完成持续会话、版本冲突检查、检查点与恢复，以及现有单设备队列的整合。Windows Python 3.12 本地测试为 **45 passed，15.21 秒**；Ruff 和工作流 skill 格式校验通过。源码 MCP 接口共 11 个工具，工具清单序列化大小的回归门槛为 28,000 字符；这不是模型 token 数或费用测量。没有增加运行依赖、网络监听服务或模型 API 调用。

两套脚本均通过真实 stdio MCP 连接调用本机 Origin 2026b SR2 10.350243 普通版，使用合成数据和独立的本地存储目录。最新证据共 **24 个原生作业**，包含预期失败与取消，全部满足各自验收条件：

| 验收组 | 已验证行为 | 本地证据 |
|---|---|---|
| `scripts/verify_sessions.py`，12 个作业 | 同一 Origin PID 连续创建和修改；过期版本修改拒绝；失败后回读原数据；恢复已提交检查点；取消未完成修改后恢复；隐藏会话空闲退出并重新唤醒；关闭会话 | `.local/session-native-02/acceptance-sessions.json` |
| `scripts/verify_session_switching.py`，12 个作业 | 程序普通 Save 后再报错仍能回滚；可见会话超过空闲阈值保持打开；拒绝其他会话的检查点；两个工程切换及插入独立批处理后各自数据仍正确；关闭会话 | `.local/session-switch-01/acceptance-switching.json` |

第一组还验证了重复请求返回相同 job ID，以及第二个独立 MCP 进程可以读取同一会话的版本和 Origin PID。第二组发现并验证了一个关键保存约束：Origin 的 Save 会改变当前工程路径，因此修改前保存恢复快照后必须立即切回可写的 `working.opju`，避免后续普通 Save 覆盖恢复快照。测试结束后未遗留 Origin 实例。

最新第一组计时如下。端到端时间包含提交与等待；原生时间由工作进程记录。它们是本机小型合成工程的一次测量，不能推定大型工程、GUI 操作或其他电脑的性能。

| 操作 | 端到端 | 原生阶段 |
|---|---:|---:|
| 首次打开会话 | 14.516 s | 11.234 s |
| 同会话创建工作表 | 1.594 s | 0.875 s |
| 同会话修改已有工作表 | 1.062 s | 0.594 s |

连续会话保留当前工程，不在每次修改后重开，因此结果中的 `project_reopened` 和 `structure_roundtrip` 为 false。原生脚本以数值回读验证这些会话案例；这不等于对任意通用程序做了独立科学校验。回滚范围是 Origin 工程，不包含脚本写入的外部文件或网络副作用。

本阶段仍是未发布的 0.2 源码；已安装及已发布的 0.1.0 未替换。GUI 控件自动化、完整功能矩阵、新安装包、各宿主模型调用及第二台实体电脑尚未验收。可见窗口的空闲保留测试不等于 GUI 自动化测试。源代码用例与之前 0.1 的发行验收分别记录，不能互相替代。

## 0.2 开发分支：基础 GUI 与 Origin Companion 品牌

2026-09-11，新增 `origin_gui`，源码工具总数为 12；工具清单回归门槛为 32,000 字符。Windows Python 3.12 本地 **62 项单元/协议测试通过，16.72 秒**；Ruff、插件清单和工作流 skill 校验通过。新增运行依赖为 Windows 专用 comtypes 1.4.16，未新增网络服务或模型 API 调用。GUI 设计与限制见 [GUI.md](GUI.md)。

最终 `scripts/verify_gui.py` 通过真实 stdio MCP 操作本机 Origin 2026b SR2 10.350243 普通版。证据在忽略目录 `.local/gui-acceptance-06/acceptance-gui.json`：**23 个作业全部满足预期，其中 19 个成功、4 个按要求拒绝**。总耗时 91.609 秒，生成 10 张有效窗口截图，最终这次无截图错误。作业数不是工具调用数或模型 token 测量。

| 验证内容 | 实际结果 |
|---|---|
| 菜单与属性窗口 | 通过 UIA 打开 Window → Properties；填写标准 Edit；通过原生 OK 确认；退出残留 MFC 菜单 |
| GUI 提交与数据回读 | Long name 为 `Origin Companion GUI verified`；原有 `[1,2,3]` 完整保留；OPJU 保存成功 |
| 模态回滚 | 属性窗口内修改未提交名称；重启本会话拥有的 Origin，恢复 begin 工程；再次回读名称与数据均正确 |
| 过期观察 | 使用旧 observation_id 被拒绝，未执行输入 |
| 事务隔离 | GUI 事务内程序、独立批处理、弹窗内 commit 均被拒绝 |
| 收尾 | 成功保存并关闭合成测试工程 |

这次测量中，修改 Long name 的 MCP 作业耗时 1.609 秒，提交 4.203 秒，需要重启 Origin 的模态回滚 18.141 秒。已直接查看属性窗口截图，确认实际文本、字段和按钮；数值及名称由 Origin 原生接口断言回读。单个属性窗口案例不代表全部对话框或自绘编辑器已覆盖，也不是独立科学分析验收。

探索测试曾发现并修复 MFC 空/重复目标 ID、旧菜单残留、对话框销毁时的 UIA 读取错误、同一 Worker 重连时的失效 OriginExt 对象、Windows 短暂文件共享冲突，以及截图失败不应否定已完成保存的问题。失败探索记录与最终通过记录分开保存，没有计入通过案例。

用户选定 **Origin Companion＋蓝色开放圆环**。源码和各宿主打包元数据已统一；本机 Codex personal 插件缓存已刷新，显示名称及 SVG SHA-256 与源码一致。保留 `origin-agent` 连接 ID。安装引擎仍为 0.1.0，新增 GUI 尚未打包替换，也未完成新能力的宿主模型调用或第二台电脑验收。

## 0.2 交付验收：复杂 GUI、冻结包与安装器

2026-09-11，本轮实现 UIA 选择/切换/展开/折叠/数值，以及基于最新截图的点击、拖选、滚轮、快捷键和 Unicode 输入。加入原生自检、宿主配置合并、备份、失败恢复及带冲突保护的回滚；保持 12 个 MCP 工具和单一运行栈。

本地核心/协议测试 **80 项通过**，Ruff 通过。真实 Origin 基线仍为 2026b SR2 10.350243、64 位普通版、非 Demo。

| 冻结版验收 | 结果 | 本地证据 |
|---|---|---|
| 复杂 GUI | 43 个作业符合预期；39 成功、4 拒绝；107.687 秒；中文、拖选、滚轮、选择、勾选、提交和模态回滚均有回读 | `.local/gui-frozen-020-01/acceptance-gui.json` |
| 通用程序 | ExpDec1 数值恢复、OPJU 继续编辑、LabTalk 总和 55、Origin C square(7)=49 全部通过 | `.local/frozen-020-r2-programs/acceptance-programs.json` |
| 持续会话 | 12 个作业满足预期，覆盖失败回滚、取消恢复、过期版本、空闲再唤醒 | `.local/frozen-020-r2-sessions/acceptance-sessions.json` |
| 多工程 | 12 个作业满足预期，包含普通 Save 后失败恢复、可见会话保留、跨工程检查点拒绝、工程/批处理切换 | `.local/frozen-020-r2-session_switching/acceptance-switching.json` |
| 固定科研流程 | 三张图、两份原生拟合报告、数据回读、OPJU 重开和 PNG/PDF/SVG 通过；图像已查看；原生阶段 22.109 秒 | `.local/frozen-020-r2-native/acceptance.json` |
| 可移植安装 | 中文与空格路径；PATH 仅 System32；未提供外部 Python/Node；真实 Origin 自检；模拟 Claude/WorkBuddy 配置生成；回滚恢复 7 个文件 | `.local/portable 中文验收/State/installations/87ca351acbd949539876a656ae7f7929/receipt.json` |

冻结运行时共 **72 个作业**符合对应预期：63 成功、8 个预期拒绝/失败、1 个预期取消。源代码复杂 GUI 另有 43 个作业通过，用时 111.718 秒，不重复计入冻结版统计。

一次初始 OPJU 继续编辑验收超时。Windows 电源日志证实对应区间因合盖进入新型待机，约十分钟后由电源按钮唤醒（Kernel-Power 506/507）。同一合成工程随后成功重新打开，四项完整程序回归通过。保留失败记录，未计入通过；插件不承诺在休眠/合盖时持续运行。

官方 `@anthropic-ai/mcpb` 校验器要求 PNG 图标：已将选定 SVG 原样导出为 512×512 PNG，修复后清单和图标校验通过。ZIP/MCPB 约 **31.7 MiB**，无额外运行时 Node 依赖；SVG 仍供其他宿主使用。包内哈希用于完整性检查，尚未做发布者代码签名。

完整功能标志保持 false。矩阵、3D、全部统计/信号/峰算法、每个自绘编辑器和 App 仍需任务级验收；第二台实体电脑、各宿主模型真正发起调用也不能从协议测试推定通过。详见 [COVERAGE.md](COVERAGE.md)。本节与前文旧版记录并存，旧版“尚未安装”的文字描述的是当时状态。


## 0.2.1：多模型接口与本机升级

2026-09-11，加入 full/economy 接口与 generic、DeepSeek、GPT Terra、Gemini、GLM、Kimi、ELM 配置。Terra 主用建议按用户偏好保留 **max** 推理；插件不更改宿主模型。104 项核心/协议测试通过（30.04 秒），Ruff 检查通过；包含两种模式的新旧 stdio 和 HTTP、参数去重/校验、语法位置反馈、不回显输入的错误、文本模型限制与配置优先级。

工具定义体积为 full 19,514 字节 / economy 4,372 字节，减少 77.60%。数值来自 `scripts/benchmark_profiles.py` 的 UTF-8 JSON 序列化，不是提供商计费 token。全部 13 个操作在经济接口中可查询原 Schema；固定配方复用原有校验与任务去重。详细技能说明改为按需读取参考文件。

0.2.0 已完成实际本机安装（收据 `4b0d06eb4307490a9c8f882c0e0029a6`），Claude Desktop、WorkBuddy 和 Codex 缓存的实际启动命令均通过 MCP 协议检验，工具数 12；该记录是 0.2.1 升级前的实测状态。主机配置不是模型推理调用证据。


冻结版经济接口通过真实 MCP 完成两个原生作业（37.734 秒）：合成线性拟合斜率 2、截距 1，原生报告和 OPJU 重开通过；通用程序工作表回读 [7,14,21]、显式单元格合计 42。相同配方重用同一任务，分页读取后重构的 manifest 与本地文件完全相等。原生图像已查看。证据 `.local/frozen-021-economy-r2/acceptance-economy.json`。

首次经济验收中，测试夹具使用 `sum(col(A))`，Origin 数值求值返回 7，未满足预期 42，因此被正确拒绝。夹具改用 `col(A)[1]+col(A)[2]+col(A)[3]` 后完整重跑通过；该修改不改变运行引擎。保留首次失败于 `.local/frozen-021-economy`，不将其计入成功。

最终安装的程序版本、配置收据、宿主命令及隧道状态在本机 `.origin-agent/verification` 和本版本交付记录中另行记录。跨模型真实推理及第二台实体机器仍未验收。

0.2.1 冻结版完整 GUI 回归再次通过：43 个作业，39 个成功、4 个预期拒绝/失败，用时 104.563 秒；含中文输入、拖选、滚轮、UIA 选择/值/切换、提交回读及模态回滚。证据 `.local/frozen-021-gui/acceptance-gui.json`。


## 0.2.2：Work 工具缓存兼容修复

2026-09-11，先用安装版 0.2.1 + 合成 CSV 复现：经济模式直接调用 `origin_inspect_dataset` 返回 `Unknown tool`，经 `origin_call` 成功。0.2.2 在不扩大经济模式工具列表的条件下接受完整模式旧名称；未知名称、参数校验、视觉限制和既有会话状态检查保留。

- 105 项自动测试通过，包含实际 stdio 的 auto/legacy 协议与 full/economy 两种模式。Ruff 检查及格式检查通过。
- 冻结 Windows 版本在经济模式下通过旧名称完成 inspect → plan → run → get_job → inspect_project。3 个合成图、2 个原生拟合报告和 OPJU 重新打开验证通过；PNG/PDF/SVG 导出，3 张 PNG 已检查标签与裁切。该数据只用于程序验收，不是用户的作业结果。
- 列表保持 5 个工具，JSON 字符数 4743；本次冷启动 0.984 秒，合成工作流端到端 28.219 秒。属于单次本机测量，不是模型推理或 token 计费指标。
- 项目同步的 Windows 共享锁已单独解除；不是修改 Origin 引擎的结果。具体诊断与复发处理见 [Work 排障](WORK_TROUBLESHOOTING.md)。ChatGPT Work 用户界面重新发送及模型完整任务仍需独立确认，不能用协议检查代替。

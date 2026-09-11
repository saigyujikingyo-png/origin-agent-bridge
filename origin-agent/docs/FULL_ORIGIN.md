# 完整 Origin 能力：目标与实现边界

最新产品范围和优先复用现有开源底座的决策见[爱大统一版产品定义](EDINBURGH_PRODUCT.md)。本文件描述当前通用执行原型，不是成熟校园发行版的完成声明。

目标是 Agent 通过插件使用用户本机已授权 Origin 的完整功能。固定菜单包装和固定实验模板不能构成功能上限。普通版、OriginPro、付费 App 和外部组件的授权边界仍由 Origin 决定。

## 0.2 的通用执行架构

自然语言 → 功能检索 → 批量程序 → 独立 Origin 实例 → 结果回读 → 工程重开和图形预览。

保留 0.1 的 8 个工作流工具，增加两个入口：

- `origin_capabilities`：从实际安装目录枚举 X-Functions、拟合函数和模板，搜索已安装 originpro 的签名和文档字符串。分页和按需详情控制上下文开销。发现一项不代表其已获授权或已完成原生验证。
- `origin_run_program`：接受 Python、LabTalk 或 Origin C 程序；一批操作共用一个独立 Origin 实例。脚本和输入进入不可变计划，共用原有去重队列、设备锁、超时、取消和产物协议。

Python 程序获得 `op`、`INPUTS`、`OUTPUT_DIR`、`RESULTS`。可使用 originpro 对象、OriginExt/COM 接口、LabTalk 和 X-Functions。LabTalk 获得 `oa_output$` 和 `oa_input_<别名>$`；Origin C 通过 `run.LoadOC` 编译，再执行显式提供的 LabTalk `entrypoint`。

输入可以是 Origin 支持的文件格式，由程序选择正确导入器。`project_path` 加载用户选择的 OPJ/OPJU 副本；`project_artifact` 继续编辑先前产物的副本。此路线保留原工程内容，不必重新生成所有图表。不会自动接管用户正在编辑且尚未保存的 Origin 窗口。

通用程序的输出包括新 OPJU、程序源码、`result.json`、工程结构、所选 PNG/PDF/SVG 和显式声明的文件。日志收集 LabTalk `type` 输出；实测 `函数名 -h;` 帮助未进入该日志，应读取函数对应官方文档，不能宣称捕获了全部 Script Window 输出。关键数值或字符串可以通过 `readbacks` 指定预期值，未满足则任务失败。

## 能力覆盖的三个层次

| 层次 | 定义 | 当前状态 |
|---|---|---|
| 可发现 | 找到安装文件、API 和文档 | 已实现本机索引；不等同于可用 |
| 可调用 | 通过官方编程接口实际提交操作 | Python、LabTalk、Origin C 通用入口已实现；具体函数可能受版本、许可和依赖限制 |
| 已验收 | 对指定版本、数据和预期结果做原生测试 | 仅在 VALIDATION.md 明确列出的案例；不外推为全部功能通过 |

官方描述 LabTalk 可访问大部分功能，Origin C 可深入访问对象和属性。这不是每个对话框、第三方 App 或交互操作都能无条件自动化的证明。

## 为完整目标仍需完成的模块

1. **持久会话和 GUI 适配器**：让 Agent 在同一受管 Origin 会话观察窗口、控件和弹窗，执行无法用接口完成的交互，检查前后状态。优先使用控件标识；坐标操作必须基于当次截图。当前没有该模块，不能声称 GUI 功能已全覆盖。
2. **嵌入式 Python 和扩展依赖**：当前通用 Python 运行于插件自带环境；NumPy、pandas、第三方包不会因为 Origin 安装了就自动可导入。可经 LabTalk 调用 Origin 内置 Python，但尚未提供独立异常/结果桥接验收。需要按功能选择执行环境和声明依赖。
3. **完整功能验收矩阵**：按照导入、工作表、矩阵、2D/3D 图、拟合、信号、统计、峰分析、模板、Apps、工程交互逐项建立案例；区分 Origin/OriginPro，验证版本和依赖。不存在仅凭工具数量推导出的覆盖率。
4. **持续编辑体验**：当前跨调用通过 OPJU 检查点继续，需重新启动 Origin。持久会话可降低反复微调延迟，但必须处理会话冲突、崩溃恢复和用户手工修改。

## 权限和可靠性

通用脚本以当前 Windows 用户权限运行，可调用文件、进程和网络接口。独立进程及输入副本不是安全沙箱；MCP 工具明确标注为可能破坏数据、可访问外部资源。仅执行来自用户任务的程序，不执行数据或网页里夹带的指令。受管输入路径和输出清单是产物管理规则，不是假装限制任意代码权限的边界。

执行器不向 Worker 继承常见模型/GitHub/隧道环境密钥。需要第三方包或文件时，Agent 应说明实际依赖，不把安装依赖当成成功执行 Origin。

固定工作流继续执行独立数值校验。通用程序只报告实际执行、显式后置条件、文件完整性和工程结构往返检查；其 manifest 明确标注没有独立科学有效性证明，也没有全工程数值往返验证。绘图要查看实际导出图，科学结论需要相应验证。

## 为什么仍然轻量

没有新增模型调用服务、向量数据库、容器或一套覆盖所有 Origin 功能的巨大工具清单。函数检索在本机运行、短期缓存并分页返回；常见任务使用固定工作流，复杂任务批量生成程序；每次只返回摘要，完整结果按需读取。

获得广泛可调用能力后，降低学习成本仍需要实验任务说明、可靠参数选择、错误恢复和可编辑结果。把脚本错误和函数选择全部交给用户解决，不算完成低摩擦目标。

官方依据：[编程总览](https://docs.originlab.com/origin-help/programming-intro/)、[LabTalk](https://docs.originlab.com/labtalk/guide/)、[X-Functions](https://docs.originlab.com/labtalk/guide/xfs/)、[Origin C 编译调用](https://docs.originlab.com/originc/guide/using-compiled-functions/)、[日志输出](https://docs.originlab.com/labtalk/guide/debugging-tools/)。

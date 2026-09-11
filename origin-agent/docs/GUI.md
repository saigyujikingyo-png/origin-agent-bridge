# Origin Companion GUI 通道

此通道补充 Python、LabTalk、X-Functions 与 Origin C，复用同一 MCP 服务、队列和常驻 Origin 会话。批量计算仍优先调用原生程序；Agent 仅在需要界面交互时获取控件摘要或截图。用户表达任务目标，不必学习菜单路径或编写代码。

## 接口与执行

`origin_gui(session_id, expected_revision, request_id, gui)` 支持：

| 动作 | 行为 |
|---|---|
| `begin` | 保存不可变 OPJU 检查点，再切回可写 working 工程，显示受管 Origin |
| `observe` | 读取窗口、控件和菜单；`query` 过滤；`screenshot` 按需生成 PNG |
| `invoke` | 调用最近观察中的菜单/按钮，或 UIA 的 Invoke、Expand、Legacy 默认动作 |
| `set_text` | 修改标准可写 Edit 或 UIA Value，并回读完整输入 |
| `select / toggle / expand / collapse` | 调用观察到的 UIA 模式；返回选择、勾选、展开和数值状态 |
| `click / drag / scroll` | 在最新截图内使用归一化坐标，校验窗口与鼠标落点所属进程 |
| `keys / type_text` | 受管窗口快捷键和 Unicode 文本，不使用剪贴板 |
| `dismiss` | 向最近观察的弹出窗口发送 Escape，随后观察它是否关闭 |
| `commit` | 弹窗关闭后保存 OPJU、更新工程索引、结束 GUI 事务 |
| `rollback` | 恢复 begin 检查点；必要时重启本会话拥有的 Origin 实例 |

每次成功操作，包括 observe，都递增会话 revision。重复 request_id 复用已有作业。每次输入绑定最近一次 observation_id 与 target_id，重新检查 PID、进程创建时间、全部顶层窗口、控件状态及唯一性；观察超过 120 秒或上下文变化即拒绝输入。

模态窗口中不调用 Origin 保存/读取 COM 接口。原生程序、独立批处理、工程切换在 GUI 事务结束前被拒绝。只返回当前弹出窗口的目标，避免在 MFC 未正确禁用主窗口时操作后台控件。错误后的会话 revision 应通过 inspect 获取；输入结果不确定时先观察，不能自动重放。

## 模块和代价

- `gui.py`：小型协议模型、陈旧/重复目标校验、公开摘要。
- `gui_session.py`：事务、检查点、状态、截图工件与失败恢复。
- `gui_native.py`：Win32 窗口/菜单/Button/Edit，进程身份约束，单窗口截图。
- `gui_accessibility.py`：Origin MFC 菜单的 UI Automation 缓存观察与动作。
- `gui_input.py`：截图、DPI 与客户区坐标绑定，前台/鼠标落点检查，Windows SendInput；中断时释放按键。
- `origin_runtime.py`：Origin 连接；已终止进程的 originpro 1.1.15 失效引用释放。

新增依赖仅 Windows 的 `comtypes==1.4.16`，用于 UI Automation。它加入 OriginExt 使用的 MTA 线程模型；不增加 HTTP 服务或模型调用。依赖自身的压缩 wheel 约 289 KiB，最终冻结包增量仍须打包实测。控件摘要最多 160 项，枚举有数量/时间预算；默认不返回截图，详细工件留在本地按需读取。这些措施控制上下文体积，尚未测得实际模型额度节省比例。

实际适配处理了 MFC 空 Runtime ID、零面积/重复可访问节点、对话框消失时的短暂读取错误，以及同一 Worker 内强制回滚后的失效连接。旧式菜单默认动作可能留下菜单窗口，Agent 可对观察到的窗口使用 dismiss 再核对结果。只对观察做有限重试，输入不会自动重放。截图读取失败单独返回 screenshot_error，不将已完成的保存误报为失败；需要视觉判断时仍须重新观察取得有效图片。来源：[Windows UI Automation](https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nn-uiautomationclient-iuiautomation)、[Origin detach](https://docs.originlab.com/originpro/namespaceoriginpro_1_1utils.html)。

## 能解决什么，尚未解决什么

原生接口承担数据、分析和批量绘图，GUI 通道承担必要的菜单/属性操作。这样可以减少找菜单、重复填表和在多个对话框之间切换的摩擦。保存可编辑 OPJU、保留检查点并回读结果，使用户能继续检查与修改。

0.2 已加入截图内点击、拖动、滚轮、快捷键和 Unicode 输入，用于补充不暴露可用 UIA 模式的自绘控件。坐标限定为最新截图内的 x/y 比例 [0,1)，目标必须为 capture.window_id；不能输入任意桌面坐标或操作其他程序。实例已验证文字拖选、下拉选项、中文输入与保存回读。每个复杂图形编辑器、App 和对话框仍须按任务核验，不能据通用输入机制推定全部功能通过。模型、权重、单位和数据处理仍需科学依据。

GUI 事务只恢复工程，不能撤销外部文件写入、网络行为或全局设置。会话只管理它启动的 Origin，不接管用户其他未保存窗口。GUI 需要交互式 Windows 桌面；锁屏、远程断连和其他语言界面还没有验收。

## 复现验收

在指定版本、已激活的交互式 Windows 桌面运行：

```powershell
uv run python scripts/verify_gui.py --home C:\OriginCompanionTests\gui-new-run
uv run python scripts/verify_gui.py --extended --home C:\OriginCompanionTests\gui-extended-new-run
```

目录必须是空的新目录。脚本通过真实 stdio MCP 创建合成工作簿，打开 Window → Properties，修改 Long name，提交后回读名称和 `[1,2,3]`；再在属性窗口内修改并回滚，检查名称和数据恢复。另验证陈旧观察、事务内程序/批处理以及弹窗内提交均被拒绝。截图、OPJU、每步耗时和完整结果写入本地；最终关闭测试工程。宿主模型与第二台电脑的验收独立记录，不能从此脚本推定通过。

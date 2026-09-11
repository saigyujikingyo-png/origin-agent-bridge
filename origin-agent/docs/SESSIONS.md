# 持续会话：已实现接口

会话使用同一个受管 Origin 实例处理连续编辑。所有请求仍经过现有 SQLite 队列、设备锁、超时和产物校验；没有增加网络端口或模型服务。默认隐藏会话空闲 180 秒后保存并退出，后续从检查点恢复；`visible=true` 的会话保持可见，直到关闭或切换任务。

## 开始与继续

调用 `origin_session(action="open", request_id="experiment-42", title="Kinetics")`。可选 `project_path` 载入工程副本。返回 job ID 后使用 `origin_get_job` 等待；成功结果的 `session` 包含 `session_id`、`revision` 和 `checkpoint_id`。

后续 `origin_run_program` 在原有 `program` 参数之外传入 `session_id` 和当前 `expected_revision`。每次成功产生新版本和可下载 OPJU；`RESULTS`、输入副本及 PNG/PDF/SVG 仍沿用原有契约。程序中无需重新建工程；要导入另一个工程时创建另一个会话。

同样的程序、同一会话版本重复提交，会返回同一作业。创建/检查点/恢复/关闭控制命令使用调用方稳定的 `request_id`；相同 ID 改变请求内容会被拒绝。会话修改在实际运行前核对版本，过期修改不触碰 Origin。

`origin_session(action="inspect", session_id=...)` 返回上次检查点的状态与有大小限制的工程索引，保留总数及截断标志；完整状态保存在本机。这个接口不是实时 GUI 观察。实时数据需要通过程序回读；手动修改可用 `checkpoint` 保存并更新索引。

## 检查点、错误与取消

每次修改前保存不可变的恢复文件，再切回可变的 `working.opju`。这样程序或用户调用普通 Save，不会覆盖修改前的恢复文件。成功产物同样保持不可变，Origin GUI 的当前文件始终回到 working 文件。

- `checkpoint`：保存当前工程并增加版本，捕获受管窗口中的手动编辑。
- `restore`：传当前版本及同一会话的成功作业 `checkpoint_id`，恢复该工程并生成新版本；其他会话的检查点被拒绝。
- 程序错误：恢复修改前的工程，版本不增加；若恢复本身失败，状态为 `needs_attention`。
- 取消/超时：先给予合作退出时间，必要时只终止已记录 PID 和创建时间的自有进程。下次执行从修改前检查点恢复。若取消晚于已验证提交，返回成功并明确说明已经提交。
- `close`：保存可编辑 OPJU，关闭受管实例并标记会话关闭。

自动恢复只覆盖 Origin 工程，不覆盖通用代码的外部文件和网络副作用。监督进程消失后，旧 Worker 不得再提交或覆盖被新 Worker 接管的会话。基础 GUI 事务及 Window Properties 模态回滚已实测，见 [GUI.md](GUI.md)。异常关闭 Origin、复杂模态窗口及完整 GUI 交互仍需后续专项验收，不能由单个案例推定全部可恢复。

## 开发与证据

- `sessions.py`：命令契约、计划哈希、请求幂等、版本元数据和中断恢复。
- `session_worker.py`：Supervisor 管理的工作进程与原子文件信箱。
- `session_native.py`：主线程 COM、工程切换、检查点、回滚和可见窗口生命周期。
- `program_native.py`：独立作业和会话共用程序执行；会话不会为校验而重开正在编辑的工程。
- `scripts/verify_sessions.py`：连续编辑、重复请求、过期拒绝、错误回滚、跨 MCP 进程、取消及空闲恢复。
- `scripts/verify_session_switching.py`：普通 Save 后报错的回滚、可见会话保留、工程隔离、错误检查点拒绝和批处理共存。

验收使用合成数据及目标版本的真实 Origin，经实际 MCP 调用；不等同于各 Agent 产品内模型调用、多电脑或完整功能验收。具体结果见 [VALIDATION.md](VALIDATION.md)。

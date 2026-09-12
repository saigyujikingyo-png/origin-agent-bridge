# 安装 Origin Companion 0.2

本版本面向 **Origin 2026 SR1 10.300197 和 2026b SR2 10.350243、Windows x64、普通 Origin、非 Demo**。每台电脑先自行安装并激活其中一个版本。SR2 已有原生验收记录；学校 SR1 的第二台设备验收仍在进行，不能仅凭安装器识别版本判定通过。插件不分发主程序或学校许可证，也不解除 OriginPro/第三方 App 的许可限制。

## 从你的 Agent 工作环境开始

Codex 用于本项目的开发与维护。师生使用下载的安装包，在云端 Work、本地 Work、Claude Desktop、WorkBuddy 等工作环境里连接 Origin Companion；无需克隆源码、安装 Git、创建代码项目或另装 Python。若宿主需要资料目录，使用研究文件夹即可。

| 使用场景 | 连接入口与当前状态 |
|---|---|
| 云端 Work | 在安装 Origin 的 Windows 电脑安装执行端，再配置自己的安全连接；已有真实云端验收。首次账号/隧道接入仍有下文所列设置步骤，尚未成为全程图形向导 |
| 本地 Work | 通过该宿主支持的插件或本机连接入口使用；本地 Work 用户流程待独立验收。不要把 `codex` 安装选项或 Codex CLI 自检当成本地 Work 已验证 |
| Claude Desktop / WorkBuddy | 使用下列安装器对应选项；本机配置和协议已验证，实际宿主模型验收单独记录 |

连接后，在 Agent 中提出分析、绘图或工程编辑目标，并查看返回的图像及可编辑工程。完整流程的目标是让用户在工作环境内完成任务；下面的维护命令用于排障或高级设置，不是每次使用的步骤。

## 一键安装

1. 下载 `origin-agent-0.2.8-windows-x64.zip`，核对随发行提供的 SHA-256，解压到普通本地目录。
2. 双击 `Install.cmd`，输入希望配置的宿主名称，例如 `claude,workbuddy`。直接回车只安装引擎和生成配置；云端 Work 用户随后完成下文的本人安全连接设置。本地 Work 的专用安装与用户入口尚需独立验收。
3. 安装器校验完整文件集合、复制独立运行时，再使用合成数据启动 Origin、检查指定版本和数值回读。通过后才合并宿主配置、切换活动版本。重新打开所选 Agent。
4. 让 Agent 先检查 Origin Companion 状态，再提交你的实际绘图、分析或编辑任务。

无需另装 Python、Node、uv 或编译器。默认程序在 `%USERPROFILE%\.origin-agent\app\0.2.8`，研究产物和会话在 `%USERPROFILE%\.origin-agent`。不改动 Origin 安装及许可；默认引擎安装不注册自启，云端用户可另外启用下方的私有隧道登录任务。包没有商业代码签名；哈希证明传输完整性，不能替代发布者签名。

已有用户可无交互升级：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -NonInteractive -Hosts claude,workbuddy
```

安装器保留其他 MCP 和宿主设置。旧版程序保留，默认不删除研究数据。每次安装输出 `receipt_id`，备份保存在 `.origin-agent\installations\<receipt_id>`。升级失败自动恢复已修改的配置；如果文件随后被用户修改，回滚会报告冲突而保留该修改。主动回滚：

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.8\server\origin-agent.exe" rollback-install <receipt_id>
```

自检与诊断：

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.8\server\origin-agent.exe" doctor --native
```

`doctor` 本身只检查发现；加 `--native` 才会创建合成工程并验证原生回读。若有未结束的 GUI 事务，先完成或回滚事务再安装。GUI 操作需要可交互、未锁屏的 Windows 桌面；休眠、合盖或断电会中断本机任务，恢复后先读取作业/会话状态再继续。

## 各宿主

- **Claude Desktop**：选择 `claude` 自动合并配置。也可直接导入 `.mcpb`；它自带运行时，使用默认本机数据目录。是否自动加载 skill 取决于宿主，服务器同时提供紧凑工具说明。
- **WorkBuddy**：选择 `workbuddy` 自动合并 `~/.workbuddy/mcp.json` 并安装工作流 skill。包内 `workbuddy` 目录保留连接器元数据和蓝色圆环图标。
- **本地 Work**：作为独立用户工作入口验收；当前不把 Codex 的开发配置步骤等同于本地 Work 安装说明。
- **其他 MCP Agent**：通用配置在 `.origin-agent/host-configs/0.2.8/generic-mcp.json`。各宿主连接入口和插件格式不同，运行引擎和工作流契约共用，实际使用仍需宿主验收。

<details>
<summary>开发与可选兼容入口：Codex / Claude Code</summary>

- **Codex**：选择 `codex` 需要本机有 Codex CLI；安装器通过其 `mcp add` 接口配置 MCP 与全局 skill。已用 personal marketplace 安装同名插件时，更新该插件而不要再添加一份 MCP。此开发机配置保留插件卡片和图标，不是通用用户安装前提。
- **Claude Code**：可用包内 `.claude-plugin`、`plugin.json` 和 `skills` 安装，作为开发、调试或可选兼容入口。

</details>

完整模式有 14 个工具，经济模式只显示 5 个工具，其余操作按需查询参数后调用。两种模式共用同一 Origin 内核；工具数量不是功能数量。实际支持边界与未验证功能见 [COVERAGE.md](COVERAGE.md)。

## ChatGPT 云端

本机已有的隧道、账户关联和密钥不会被安装器重置。升级后需要重新连接隧道来启动新引擎。首次使用按 [OpenAI 官方说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)创建账号支持的安全 MCP 隧道，使用自己的工作区、Tunnel ID 和本机密钥：

```powershell
.\Connect-ChatGPT.ps1 -TunnelId <自己的TunnelID> -TunnelClient <官方客户端路径> -Run
```

密钥只在本机设置，不写入源码或聊天。现有用户用自己的启动器重新连接；不要复制开发者的隧道配置、账户或密钥给同学。本机必须开机且隧道客户端在线。聊天附件不自动同步到 Windows，Agent 使用前需要本地副本或宿主支持的文件传输。

### 让云端连接独立于 Codex

已配置私有隧道，且限制用途的密钥已保存在本机 `.origin-agent/secrets/tunnel-key.dpapi` 的用户，可运行发行包旁的脚本：

```powershell
.\Enable-ChatGPT-Tunnel-Startup.ps1 -StartNow
```

这会创建名称以 `Origin Companion Private Tunnel` 开头的 Windows 当前用户登录任务。新安装附带当前用户 SID，避免不同 Windows 账号重名；本人的既有任务保持原名。任务使用普通用户权限、隐藏窗口、仅在用户登录时运行，退出 Codex 不影响该进程。包装脚本读取当前安装指针；隧道客户端处理网络重连，若进程意外结束，计划任务以一分钟间隔最多重启三次。不在注销、关机或休眠期间执行 Origin，也不替代 GUI 所需的未锁屏桌面。

连接配置统一保存在 `%USERPROFILE%\.origin-agent\cloud\profiles`。首次启用会复制本人的已有连接配置；其中密钥必须仍是环境变量引用，不会创建或复制其他人的凭据。此路径避免 MSIX 打包应用的 AppData 重定向导致后台任务读取不到配置。密钥仅在当前用户后台进程内解密，不写入参数、仓库或共享包。首次没有该加密密钥时脚本会报缺少前置配置，不会在后台弹出输入框。

核验应同时看计划任务状态、`tunnel-client runtimes status origin-agent --json` 以及 Work 中的真实 `origin_status` 调用。只看到后台进程不能证明云端已经连通。`.origin-agent/cloud/background-status.json` 和 `background-error.json` 分别保留最近成功与错误时间，旧错误不代表当前仍失败。

需要停用时，先停止并禁用本人的上述 Windows 计划任务，再对同一 `origin-agent` 别名执行 `tunnel-client runtimes stop origin-agent`；重新启用仍使用同一个脚本。不要只结束 Codex，也不要结束其他 Origin 实例。它不更改模型订阅或学校许可。

桥接代码为 MIT，插件本身没有模型中间层收费；Origin、Agent 及云端服务按各自许可/套餐使用。账号或服务价格需以提供商当前说明为准。

## 多电脑与卸载

同一个 ZIP 可在每台符合目标版本的 Windows 电脑单独安装，生成本机绝对路径。不要直接复制另一台机器生成的宿主 JSON。每位同学/教授使用自己的 Origin 授权和 Agent 账号。此处是可移植安装机制；第二台实体电脑的实测状态见 [VALIDATION.md](VALIDATION.md)。

卸载时先从宿主移除插件/MCP 连接或回滚安装配置，再删除程序版本目录。自己的 OPJU、数据与会话可以保留。通用 Python/LabTalk/Origin C 程序按当前 Windows 用户权限执行；按授权任务使用，不能把隔离工作进程当作脚本安全沙箱。

多模型/经济模式配置和实测边界见 [MODELS.md](MODELS.md)，学校模型服务说明见 [ELM.md](ELM.md)。

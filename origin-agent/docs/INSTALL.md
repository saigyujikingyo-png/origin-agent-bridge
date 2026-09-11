# 安装 Origin Companion 0.2

本版本只面向 **Origin 2026b SR2 10.350243、Windows x64、普通 Origin、非 Demo**。每台电脑先自行安装并激活这个 Origin 版本。插件不分发主程序或学校许可证，也不解除 OriginPro/第三方 App 的许可限制。

## 一键安装

1. 下载 `origin-agent-0.2.2-windows-x64.zip`，核对随发行提供的 SHA-256，解压到普通本地目录。
2. 双击 `Install.cmd`，输入希望配置的宿主名称，例如 `claude,workbuddy`。选择 `codex` 时需要本机有 Codex CLI；安装器通过其官方 `mcp add` 接口注册，并安装工作流 skill。直接回车只安装引擎和生成配置。
3. 安装器校验完整文件集合、复制独立运行时，再使用合成数据启动 Origin、检查指定版本和数值回读。通过后才合并宿主配置、切换活动版本。重新打开所选 Agent。
4. 让 Agent 先检查 Origin Companion 状态，再提交你的实际绘图、分析或编辑任务。

无需另装 Python、Node、uv 或编译器。默认程序在 `%USERPROFILE%\.origin-agent\app\0.2.2`，研究产物和会话在 `%USERPROFILE%\.origin-agent`。不改动 Origin 安装及许可，不注册开机自启。包没有商业代码签名；哈希证明传输完整性，不能替代发布者签名。

已有用户可无交互升级：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -NonInteractive -Hosts claude,workbuddy
```

安装器保留其他 MCP 和宿主设置。旧版程序保留，默认不删除研究数据。每次安装输出 `receipt_id`，备份保存在 `.origin-agent\installations\<receipt_id>`。升级失败自动恢复已修改的配置；如果文件随后被用户修改，回滚会报告冲突而保留该修改。主动回滚：

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.2\server\origin-agent.exe" rollback-install <receipt_id>
```

自检与诊断：

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.2\server\origin-agent.exe" doctor --native
```

`doctor` 本身只检查发现；加 `--native` 才会创建合成工程并验证原生回读。若有未结束的 GUI 事务，先完成或回滚事务再安装。GUI 操作需要可交互、未锁屏的 Windows 桌面；休眠、合盖或断电会中断本机任务，恢复后先读取作业/会话状态再继续。

## 各宿主

- **Claude Desktop**：选择 `claude` 自动合并配置。也可直接导入 `.mcpb`；它自带运行时，使用默认本机数据目录。是否自动加载 skill 取决于宿主，服务器同时提供紧凑工具说明。
- **WorkBuddy**：选择 `workbuddy` 自动合并 `~/.workbuddy/mcp.json` 并安装工作流 skill。包内 `workbuddy` 目录保留连接器元数据和蓝色圆环图标。
- **Codex**：选择 `codex` 自动配置 MCP 与全局 skill；这是无需手改 TOML 的安装路线。已用 personal marketplace 安装同名插件时，更新该插件而不要再添加一份 MCP；开发机采用此刷新方式，保留插件卡片和图标。
- **Claude Code 或其他 MCP Agent**：可用包内 `.claude-plugin`、`plugin.json` 和 `skills` 安装；通用配置在 `.origin-agent/host-configs/0.2.2/generic-mcp.json`。各宿主插件格式不同，运行引擎和工作流契约共用。

完整模式有 13 个工具，经济模式只显示 5 个工具，其余操作按需查询参数后调用。两种模式共用同一 Origin 内核；工具数量不是功能数量。实际支持边界与未验证功能见 [COVERAGE.md](COVERAGE.md)。

## ChatGPT 云端

本机已有的隧道、账户关联和密钥不会被安装器重置。升级后需要重新连接隧道来启动新引擎。首次使用按 [OpenAI 官方说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)创建账号支持的安全 MCP 隧道，使用自己的工作区、Tunnel ID 和本机密钥：

```powershell
.\Connect-ChatGPT.ps1 -TunnelId <自己的TunnelID> -TunnelClient <官方客户端路径> -Run
```

密钥只在本机设置，不写入源码或聊天。现有用户用自己的启动器重新连接；不要复制开发者的隧道配置、账户或密钥给同学。本机必须开机且隧道客户端在线。聊天附件不自动同步到 Windows，Agent 使用前需要本地副本或宿主支持的文件传输。

桥接代码为 MIT，插件本身没有模型中间层收费；Origin、Agent 及云端服务按各自许可/套餐使用。账号或服务价格需以提供商当前说明为准。

## 多电脑与卸载

同一个 ZIP 可在每台符合目标版本的 Windows 电脑单独安装，生成本机绝对路径。不要直接复制另一台机器生成的宿主 JSON。每位同学/教授使用自己的 Origin 授权和 Agent 账号。此处是可移植安装机制；第二台实体电脑的实测状态见 [VALIDATION.md](VALIDATION.md)。

卸载时先从宿主移除插件/MCP 连接或回滚安装配置，再删除程序版本目录。自己的 OPJU、数据与会话可以保留。通用 Python/LabTalk/Origin C 程序按当前 Windows 用户权限执行；按授权任务使用，不能把隔离工作进程当作脚本安全沙箱。

多模型/经济模式配置和实测边界见 [MODELS.md](MODELS.md)，学校模型服务说明见 [ELM.md](ELM.md)。

# 安装与使用

以下安装说明对应已发布的 0.1.0。开发分支的 0.2 通用执行原型尚未替换安装版。爱大统一全功能版的验收要求见 [EDINBURGH_PRODUCT.md](EDINBURGH_PRODUCT.md)。

已发布 0.1.0 原本接受 Windows x64 和 Origin 2021 或更新版本；实际验收版本为 Origin 2026b SR2 10.350243 普通版。后续个人分享开发版已经收窄到这一指定基线，并在实际执行前检查。插件不包含 Origin 主程序或学校许可证。

## Windows 安装包

1. 下载并解压 `origin-agent-0.1.0-windows-x64.zip`，核对发行页的 SHA-256。
2. 双击 `Install.cmd`，或在解压目录运行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1`。安装器检查包内文件哈希，复制到用户目录并运行安装诊断。
3. 安装目录中的 `host-configs` 提供 Claude、WorkBuddy 和通用 MCP 配置；路径是本机生成的，不包含开发者电脑路径。
4. 每台电脑独立安装一次。需要迁移研究数据时，复制自己的数据和已生成 OPJU；不复制学校许可文件。默认作业数据位于 `%USERPROFILE%\.origin-agent`。

ZIP 已包含 Python 及运行依赖，不需要另外安装 Python、Node、uv 或编译器。当前产物未做商业代码签名；校验和用于下载/复制完整性核对，不能代替发布者签名。安装不注册开机自启，不更改 Origin 的安装或许可。

## Claude Desktop

直接导入 `.mcpb`。它包含自足的服务器，不必先运行 Windows 安装器。

另一种方法是先运行 Windows 安装器，再把 `host-configs/claude-desktop.json` 中 `origin-agent` 这一项合并到 Claude 的 MCP 配置。安装器支持 `-ConfigureClaude`，合并时会先备份已有配置。重启 Claude 后验证工具发现。MCPB 中包含 skill 文件，但是否自动加载 skill 取决于宿主；服务器本身也提供工作流使用说明。

## Codex / Claude Code

安装运行时后，插件目录提供根 `plugin.json`、`mcp.json`、`.codex-plugin`、`.claude-plugin` 和 `skills`。通过各宿主本地插件机制安装该目录；本次 Codex 的安装结果记录在验收文档。

从源码开发使用 `uv sync --locked` 和 `uv run origin-agent serve`。源码清单默认读取安装器写入的 `%USERPROFILE%\.origin-agent/install.json`；若尚未安装二进制包，应把开发宿主命令明确配置为 `uv --directory <项目目录> run origin-agent serve`。

## WorkBuddy

安装运行时后，导入 `host-configs/workbuddy-connector.zip`，或在 MCP 设置中合并 `host-configs/workbuddy.json`。连接器带有中文/英文说明、图标和 skill。需要 WorkBuddy 4.24.0 以上支持此清单字段。

不要把电脑 A 生成的绝对路径配置直接复制到电脑 B；在电脑 B 运行同一安装器，会生成正确路径。发布用源清单也提供通过用户目录查找已安装运行时的入口。

## ChatGPT 云端

需要账号有开发者模式、Tunnel 的 Read/Use 权限，以及已经与目标 ChatGPT 工作区关联的 `tunnel_id`。这些账号条件无法写进插件包。

1. 按 [OpenAI 官方说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)创建隧道并下载官方 `tunnel-client`。
2. 在本机环境中设置 `CONTROL_PLANE_API_KEY`；不要把密钥发送到聊天或提交到 Git。
3. 运行安装目录的 `Connect-ChatGPT.ps1 -TunnelId <实际ID> -TunnelClient <实际程序路径> -Run`。脚本建立 stdio 配置并运行 doctor，再连接隧道。
4. 在 ChatGPT Plugins 的开发者连接界面选择 Tunnel，完成工具发现和调用测试。

本机必须开机，隧道客户端需要运行。云端 Agent 可以返回摘要和 PNG 预览；OPJU 主要通过本机路径或 MCP 二进制资源获取，具体下载展示取决于客户端。当前版本不自动把聊天附件同步到 Windows；文件须先放入受支持的数据目录。该机制用于私有使用，不等同于公开市场上架。

隧道运行密钥可设为 Restricted，仅开启 Tunnels Read/Use，并关闭模型 API 权限。选择有限有效期后，应在到期前更新本机密钥。专用密钥不需要模型调用权限；不要给长驻客户端管理员密钥。

桥接程序采用 MIT 许可且不收服务费；Origin 和 Agent 的原有许可/套餐另算。[ChatGPT 与 API 独立计费](https://help.openai.com/en/articles/9039756-managing-billing-settings-on-the-chatgpt-web-and-api-platform)。截至核查日期，官方隧道文档没有列出独立价格，本次创建隧道未要求付款；这不能当作永久免费承诺。

## 数据、诊断和卸载

默认允许用户 Documents、Desktop、Downloads 的实际系统路径及插件 inbox。`ORIGIN_AGENT_DATA_ROOTS` 可设置为 JSON 路径数组。服务器仅导入 CSV/TSV/XLSX；不开放通用文件读取或任意脚本执行。XLSX 多工作表要指定表名，含公式时要求用户提供值导出。

用 `server/origin-agent.exe status` 查看安装发现。运行失败请保留 job ID，检查作业目录的 `error.json` 和 `worker.log`；不要用未验证的半成品代替结果。修复环境后可在原工作流设置新的 `revision` 来明确重试。

卸载时从宿主移除插件/MCP 配置，再删除安装目录即可。研究结果保留在 `.origin-agent/jobs` 和 `.origin-agent/datasets` 中；只有确定不需要时才自行删除。安装器不会代替用户清理这些数据。

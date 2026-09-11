# 爱大统一 Origin Agent 插件：产品目标与复用决策

更新日期：2026-09-11。这是用户个人开发、可分享给同学和教授的插件。目标是在爱大提供的指定 Origin 版本上，让已获授权的学生、教授和研究人员通过 Claude、ChatGPT、Codex、WorkBuddy 等通用 Agent 使用该版本的全部功能，并保持安装简单、连续编辑顺畅。

项目不寻求学校官方发行；学校审批、校园 SSO 和集中管理不是交付前置条件。

## 统一版本的处理

用户明确以其爱大授权 Origin 版本为范围，因此固定开发和验收基线为当前机器已经验证的 **Origin 2026b SR2、内部版本 10.350243、Windows x64、普通版**。同学或教授安装后自动核对这一基线；其他版本明确标示未经验证，不承担所有历史版本的兼容。

插件分享包只包含插件和必要运行环境；接收者使用自己已经安装并激活的目标版本。"全部功能"以这个版本实际提供的功能为边界，涵盖非常用分析、图形编辑、Apps 和 GUI 交互；不把只有另一许可类型才提供的功能算作插件缺失。

## 现成项目核验

检索范围：GitHub 公开的 Origin/OriginPro MCP、自然语言自动化、Edinburgh/大学部署、安装和宿主支持资料。结论是**未发现有公开证据证明已完整满足本目标的现成发行版**，不等于证明 GitHub 上绝对不存在相关项目。

| 项目 | 可直接利用的成果 | 与本产品目标的差距/证据不足 |
|---|---|---|
| Ge-Shun/origin-mcp | Origin 2026/2026b 桥接；25 个 compact 工具与 full 模式；函数知识库；工作表、矩阵、图形、分析、模板；Origin Start/Stop OPX；单实例与恢复逻辑 | 当前仍标注 Alpha/testing；本机实测默认依赖安装后无法启动，需固定 MCP 1.x；结构化非线性拟合外层成功但实际未执行；OPX 安装与各宿主完整流程仍未验证 |
| garethbeaumo/originlab-mcp | originpro/COM；66 个工具；导入、图形编辑、非线性拟合；本地安装配置面板 | 功能列表不构成全 Origin 覆盖证明；未见满足统一校园部署和所有目标宿主的完整验证 |
| youngminsw/Origin-Pro-MCP | COM、独立会话、恢复、MCP/CLI；统计、信号、矩阵及绘图 | 作者明确实测 OriginPro 2020；2026b 普通版与全校部署仍需验证 |
| Yike-Ye/OriginLab-MCP | Windows/虚拟机远程控制、图形实际状态回读、较紧凑工具界面 | 重点在绘图和状态检查；作者报告 Origin 2024 实测，不是爱大全功能发行版 |

本次固定 Ge-Shun commit `fecb7226ed60d7651d921d2586eb9950bf16b618`（v0.1.4），先审查源码，再在独立 Python 环境中通过实际 MCP 调用本机 Origin，完成 17 步验证。固定兼容 MCP 1.30.0 后，数据导入、线性拟合数值、矩阵读写、连续修改、OPJU 保存并回读修改值通过；结构化 ExpDec1 拟合未通过，因此整体验收为失败。这个测试使用上游串行 bridge 类和独立外部 Origin 实例，不是 OPX 嵌入启动验收。详见 [实测与复用决策](CANDIDATE_EVALUATION.md)。

## 技术决策

**优先选择性复用 Ge-Shun/origin-mcp 的知识、通过验收的对象适配和持续会话设计**。实测不支持直接把其发行重新包装成完整版本。现有 Origin Agent Bridge 的便携运行环境、多宿主包装、输入快照和结果校验可以保留；已经通过同一版本数值断言的原生非线性拟合实现用于补上已发现缺口。

实现路线及模块契约见 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)。持续会话及检查点已进入实现并通过原生场景测试；之后补齐 GUI 操作、分享安装和完整功能分类验收。每项以实际结果和人工修正次数决定是否可交付。模块复用保留 MIT 许可/署名；目前候选源码只存在忽略的测试目录，没有并入本插件发行。

## “顺畅全功能版”的验收定义

| 方面 | 完成条件 |
|---|---|
| 安装 | 同一安装包；用户选择已装 Agent；自动发现 Origin、配置连接并完成合成数据自检；无需手改 JSON、安装 Python 或处理路径 |
| 功能 | 覆盖指定 Origin 版本的导入、工作表、矩阵、2D/3D、拟合、统计、信号、峰、模板、Apps 和工程交互；官方 API 之外的交互有 GUI 适配；逐类有验收结果 |
| 连续工作 | 在原工程上继续编辑；保留用户手动修改；能查看当前对象和图形；撤回或回到明确检查点；不会悄悄重建丢失内容 |
| 学习成本 | 用户表达实验/研究目标即可；Agent 找到功能并填写参数；仅询问影响科学结论的缺失信息；错误信息能说明问题和恢复步骤 |
| 结果 | 原生可编辑 OPJU；参数、数据来源和处理步骤可追溯；实际图像检查；关键数值有对应检验 |
| 师生共用 | 相同代码和界面；各用户独立数据、设置和 Agent 账号；不依赖开发者的路径、密钥或账号 |
| 多宿主 | 每个承诺支持的 Agent 都有实际模型调用验收；协议连接成功不替代宿主验收 |
| 性能与额度 | 按需检索工具和文档；批量执行；连续修改复用会话；默认小摘要；不增加额外模型服务；记录真实时间和调用次数 |
| 分享维护 | 可以直接发送安装包或下载链接；接收者无需开发者账号、密钥和本机路径；提供校验、升级和回滚；验证干净环境和不同 Windows 用户的安装；实际同学/教授试用用于改进体验，不等待学校官方发布 |

“全功能”表示指定授权版本的功能不被插件人为缩减；不表示 AI 不会犯错，也不以接口名称数量或能够执行任意脚本代替功能验收。

## 各宿主的连接差异

本地 MCP 是最少账号配置的默认路线，使用各用户自己的 Agent 账号。本地执行端仍在 Windows。ChatGPT 云端需要各接收者完成受支持连接及目标工作区权限；开发者个人 tunnel/key 不写进分享包。校园集中分发和 SSO 不在本项目范围。

统一的是安装体验、Origin 基线、能力和工作流，不是共享一个模型账号或一份私人密钥。Mac 用户需要可达的已授权 Windows 计算端或虚拟机，当前不宣称原生 macOS 运行 Origin。

## 当前状态

0.1.0 是已发布且本机验证的有限工作流版本。0.2 在开发分支中扩展通用官方编程接口，实际执行前核对指定版本；状态接口明确报告 `full_functionality_verified: false`。0.2 尚未替换本机已安装版。完整覆盖、GUI 会话、多宿主全流程和跨电脑验证仍是未完成工作，当前不宣称完整分享版已经完成。

来源：[学校化学学院软件页面](https://chem.ed.ac.uk/cto/student-support/computing-software)、[Ge-Shun 项目](https://github.com/Ge-Shun/origin-mcp)、[v0.1.4 发行](https://github.com/Ge-Shun/origin-mcp/releases/tag/v0.1.4)、[工具模式](https://github.com/Ge-Shun/origin-mcp/blob/main/docs/tools.md)、[原生工作流](https://github.com/Ge-Shun/origin-mcp/blob/main/.github/workflows/real-origin.yml)、[garethbeaumo](https://github.com/garethbeaumo/originlab-mcp)、[youngminsw](https://github.com/youngminsw/Origin-Pro-MCP)、[Yike-Ye](https://github.com/Yike-Ye/OriginLab-MCP)。

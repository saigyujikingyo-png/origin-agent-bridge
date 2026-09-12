# Origin Companion

属于 [Chembridge](CHEMBRIDGE.md)：面向爱大师生的便捷插件、专业软件插件与 Agent 自动化工作流总项目。

让师生在云端 Work、本地 Work、Claude、WorkBuddy 等通用 Agent 工作环境中，用自然语言完成本机 Origin 分析、绘图和工程编辑。

**Codex 用于本项目的开发、调试和维护。使用插件不要求进入代码开发环境、克隆源码仓库、安装 Git 或自行配置 Python。** 面向用户的流程是：安装插件 → 连接自己的 Agent → 提供研究数据和目标 → 查看图形、分析结果和可编辑工程。宿主需要资料目录时，使用研究文件夹即可，插件不要求它是 Git 仓库。

目标是供使用指定爱大授权 Origin 版本的同学、教授和研究人员个人分享使用。Origin 计算由 Windows 上的独立执行端完成；云端 Agent 经本人配置的安全连接调用，本地 Agent 经受支持的本机连接调用。常规任务优先批量原生操作，GUI 用于需要它的交互补充。

当前发行是 **[0.2.7 预览版](https://github.com/saigyujikingyo-png/origin-agent-bridge/releases/tag/v0.2.7)**。真实云端 Work 已有验收案例；本地 Work、其他宿主内的模型调用及第二台电脑仍需独立验收。列为目标使用场景，不等于已经全部验证。

- [下载后的安装与连接](origin-agent/docs/INSTALL.md)
- [自然语言试用示例](origin-agent/examples/README.md)
- [产品定位与交付标准](origin-agent/docs/EDINBURGH_PRODUCT.md)
- [云端文件交付修复与实际下载验收](WORK_DELIVERY_0.2.7.md)
- [云端卡住问题修复与复测](WORK_RECOVERY_0.2.6.md)
- [此前详尽 Work 验收](WORK_ACCEPTANCE_2026-09-11.md)
- [0.2.8 候选云端 Work 验收](WORK_ACCEPTANCE_0.2.8.md)
- [四套真实观测数据的原生核验](NIST_ACCEPTANCE_2026-09-12.md)
- [Chembridge 云存储安排](CLOUD_STORAGE.md)
- [后续开发路线](origin-agent/docs/ROADMAP.md)
- [开发者实现说明](origin-agent/README.md)

目标基线：Origin 2026 SR1 10.300197 和 2026b SR2 10.350243、Windows x64、普通 Origin。SR2 已有原生案例验收；SR1 已在第二台设备通过列出的四套公开数据原生测试；宿主启动兼容及该设备的云端 Work 仍在核验。项目不分发 Origin 或学校许可证。插件代码采用 MIT 许可；第三方库保持各自许可。

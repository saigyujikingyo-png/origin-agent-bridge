# Origin Agent Bridge

把本机正版 Origin 变成通用 Agent 可调用的科研工作流插件。

当前目标是面向爱大已获 Origin 授权的教授、研究人员和学生，形成统一、顺畅的完整功能版本。优先复用现有开源底座，具体范围、候选核验和完成标准见[爱大统一版产品定义](origin-agent/docs/EDINBURGH_PRODUCT.md)。0.2 通用执行原型仍在开发分支，已发布安装版仍为 0.1.0。

- [代码与入口](origin-agent/README.md)
- [具体实现架构](origin-agent/docs/ARCHITECTURE.md)
- [多电脑安装与各 Agent 接入](origin-agent/docs/INSTALL.md)
- [验证结果和支持边界](origin-agent/docs/VALIDATION.md)

Windows 执行器 + 标准 MCP + 宿主插件清单。支持数据检查、多曲线与误差棒、原生线性拟合/Beer–Lambert、批处理、可编辑 OPJU 和 PNG/PDF/SVG。

本项目不分发 Origin 或学校许可证。新桥接代码采用 MIT 许可；第三方库保持各自许可。

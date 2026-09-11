# 首次使用的合成示例

`synthetic-calibration.csv` 是软件测试数据，不是真实实验结果。

把它复制到 `origin_status` 返回的 inbox 目录，命名为 `origin-agent-demo.csv`。随后在已连接插件的 Agent 中发送：

> 使用 Origin 插件读取 inbox 下的 origin-agent-demo.csv。以 Concentration 为 X、Absorbance 为 Y，SD 只作为标准差误差棒。做普通最小二乘线性拟合，自由截距，不加权。X 标签为 Concentration (mmol/L)，Y 标签为 Absorbance，导出 PNG、PDF、SVG 和可编辑 OPJU；显示预览并报告验证结果。这是合成测试数据。

接着可以说：

> 保留原计划的科学设置，把曲线改为橙色、图宽改为 1600，生成一个新版本。

修改样式会从保存的快照重建新工程，原有结果仍然保留。

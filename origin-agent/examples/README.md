# First workflow: synthetic calibration

`synthetic-calibration.csv` contains software test data, not real experimental results.

Copy it to the inbox directory returned by `origin_status` and name it `origin-agent-demo.csv`. In the agent connected to Origin Companion, send:

> Use Origin Companion to read origin-agent-demo.csv from the inbox. Use Concentration as X and Absorbance as Y. Show SD only as standard-deviation error bars. Perform unweighted ordinary least-squares linear regression with a free intercept. Label X as Concentration (mmol/L) and Y as Absorbance. Export PNG, PDF, SVG and an editable OPJU project. Show a preview and report the verification results. These are synthetic test data.

Then try:

> Keep the scientific settings from the original plan. Change the curve to orange and the figure width to 1600, and create a new version.

A style revision rebuilds a new project from the saved snapshot and preserves the earlier results. Requests may use another language supported by your agent; English is not required for runtime use.

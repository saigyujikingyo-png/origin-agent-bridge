# Model support and efficient use of quota

Origin Companion adapts its MCP interface to model capabilities. Claude, Codex, WorkBuddy or another host still selects the model. The plugin has no built-in model API client, stores no model key and initiates no extra paid inference. A preset is neither model detection nor a way to give MCP support to a chat interface without tools.

The primary preference is **GPT-5.6 Terra + max reasoning**, retaining max at the user's confirmed cost preference. Optimisation focuses on tool definitions, on-demand guidance, batched native execution and fewer GUI round trips. The host applies reasoning settings; the plugin only communicates the preference. Other models use profiles suited to their actual tool and vision capabilities.

## Two interfaces, one Origin core

| Mode | Tools visible to the model | Use and trade-off |
| --- | --- | --- |
| `economy` | Five: status, simple recipe, on-demand help, general call, artifact/preview | Routine tasks, smaller models and limited quota; unfamiliar complex operations require a help lookup |
| `full` | Fourteen tools with typed arguments exposed directly | Repeated complex programming, or hosts that handle JSON-string arguments poorly; larger initial tool context |

Economy mode accesses every full-mode operation through `origin_call(operation, arguments_json)`, using the same Pydantic validation, deduplication, revision checks, checkpoints and serial Origin queue. The generic call is annotated for writes and external access, not as read-only. The direct `origin_recipe` tool handles standard plots and linear fits without generated Python or a JSON string.

Recipes require an inspected dataset and exact column names. Fits require explicit intercept and weighting. `action=run` validates and submits in one call without another approval round. Errors give short field guidance; the plugin does not silently repair JSON, replay GUI input or switch to an expensive model. Complex panels, error-bar configurations and nonlinear fits use the full workflow/program route; Beer–Lambert gained a simplified recipe in 0.2.6. Summaries do not truncate saved files; paginated text returns `next_offset`.

A local measurement on 2026-09-11 recorded **19,514 UTF-8 bytes** of full-mode tool definitions and **4,372 bytes** for economy, a **77.60%** reduction. This is compact tool-definition JSON, excluding conversation, skills, dynamic guidance and images. It is **not a billed-token or price reduction**. Later interfaces have their own version-specific measurements. Reproduce with `scripts/benchmark_profiles.py --output <report.json>`. Full mode may need fewer calls for some tasks; economy is not guaranteed to cost less every time.

## Configure capabilities

```powershell
$originInstall = Get-Content -Raw "$env:USERPROFILE\.origin-agent\install.json" | ConvertFrom-Json
& $originInstall.executable configure-model gpt-terra --profile economy --vision auto
```

This updates `.origin-agent/agent-profile.json`, keeping one backup. Reconnect MCP to apply it. Use `--profile full` to restore direct tools. A host can instead use `serve --profile economy --model-preset deepseek --vision off`, or `ORIGIN_AGENT_PROFILE`, `ORIGIN_AGENT_MODEL_PRESET` and `ORIGIN_AGENT_VISION`. Precedence is command line → environment → local configuration → default full mode.

`vision=off` rejects image previews and screenshot-driven input while retaining native programs, text-based UIA controls, menus and numerical read-back. With `auto`, the agent must confirm that its current model and host can read images; `on` records an operator-selected visual configuration. Neither is a vision benchmark. Screenshot actions still require a fresh observation, correct window and foreground checks. Vision support is not shared by every model of a brand.

| Preset | Starting point | Host responsibilities |
| --- | --- | --- |
| `deepseek` | economy; off for text-only models | Use a compatible tool adapter; provider strict mode accepts a specific JSON Schema subset, not every MCP schema automatically |
| `gpt-terra` | economy + max reasoning; compare full for repeated complex edits | Select `gpt-5.6-terra` and `max`; preserve the user's effort setting and optimise context/round trips, without changing account settings |
| `gemini` | economy + auto | Preserve complete call IDs, tool results and required thought signatures |
| `glm` | economy; off for text models | Preserve `reasoning_content` during interleaved thinking and assemble streamed arguments correctly; verify visual models separately |
| `kimi` | economy; auto for multimodal models | Use explicit steps/examples and retain required tool context; do not assume older text models support vision |
| `elm` | economy; check account models first | Use a host supporting both a custom ELM API and MCP; ELM web chat is not automatically a local MCP agent |

These are interface presets and host requirements, **not certifications of real API performance for every listed model**. Automated tests cover seven presets, local protocol, recipes, schema reachability and text-only restrictions. Model selection accuracy, scientific judgement and actual token costs require account/model-specific testing.

## Benchmark gates and recorded evidence

Compare economy/full on the same tasks: CSV scatter plots, free/zero-intercept calibration, missing-unit clarification, nonlinear fitting, continued OPJU editing, recovery from stale GUI observations and text-only operation. Use synthetic or authorised public data. Record success rate, native numerical read-back, reopen results, errors/retries, time and available actual provider input/cache/output/reasoning usage and charges.

A successful tool call does not replace figure/scientific review. Include retries, guidance and screenshots in quota comparisons; extend testing when the task or implementation changes.

The initial profile work did not conduct a cross-provider API benchmark. Later cloud Work evidence records **GPT-5.6 Sol with light reasoning** and a second-device **GPT-5.6 Terra with max reasoning** Norris workflow. Those cases do not establish a full cross-model success/cost comparison. See the [0.2.8 report](../../WORK_ACCEPTANCE_0.2.8.md). The plugin does not automatically upload experimental data for benchmarking.

## Sources checked on 2026-09-11

- [DeepSeek tool calls and strict mode](https://api-docs.deepseek.com/guides/tool_calls/): application-side tool execution and provider-adapter strict settings.
- [OpenAI GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra): tool calling, structured output and image input; verify current availability with the host.
- [Gemini thought signatures](https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures): preserve signatures required by that API; other APIs have their own contracts.
- [GLM thinking mode](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode): interleaved tool reasoning context and host-managed thinking settings.
- [Kimi prompting guidance](https://platform.moonshot.ai/docs/guide/prompt-best-practice): explicit steps, examples and relevant on-demand instructions.
- [ELM model and quota boundaries](ELM.md).


## 0.2.10 routing and model hints

Call the five advertised tools directly. To use an unfamiliar full-mode operation,
call `origin_help(operation="origin_get_job")`, then
`origin_call(operation="origin_get_job", arguments_json=...)` with the returned
schema and real job ID. The same rule covers `origin_run_workflow` and every name
in the help catalog, including `origin_recipe`. Do not nest `origin_call`.
Accidentally routing `origin_help` through `origin_call` now returns validated
help in the same request; it never executes a native operation. Unknown operations
return a small structured `recovery` instruction pointing to direct help.

`agent_profile.host_requirement` retains its string type and states the MCP host
requirement. `host_recommendation` carries the preset-specific advice;
`benchmark_preference` identifies Terra max with `required: false`. The host keeps
its selected model. `model_quality_verified: false` means there is no model-quality
certification, not that a native result failed.

The 0.2.10 compact tool definitions remain **5,129 UTF-8 bytes**, the same as the
measured 0.2.9 baseline. Full mode is 22,555 bytes. These counts exclude skills,
conversation, help responses, images and reasoning, and are not billed tokens.


## 0.2.11 output contracts

The five-tool economy catalog now includes validated output schemas: 36,317 UTF-8
bytes versus 178,008 in full mode using serialized tool metadata. This adds metadata
compared with the earlier release; exact operation schemas remain on demand through
`origin_help`. New limits guard schema growth and structured-output size. Local warm
status validation measured 0.1489 ms median across 500 iterations. No paid secondary
model layer or new runtime dependency was added. These measurements are not billed
tokens or a Terra max model benchmark. See [output contracts](OUTPUT_CONTRACTS.md)
and the version-specific acceptance report for verification and untested hosts.

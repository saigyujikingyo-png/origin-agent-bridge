# Deliver the actual Origin files

`origin_get_artifact(mode="download")` returns one standard MCP embedded binary resource (maximum 32 MiB), plus artifact identity, byte count and SHA256. Use the host's native file API when it can save these bytes. Local paths and `origin://` links alone are not cloud downloads.

For Work/code-orchestration hosts that expose the blob but do not automatically create an attachment, load [the receiver](../scripts/receive_artifact.js). An MCP-only economy connection can obtain exactly the same code through `origin_help(operation="origin_get_artifact", query="receiver")`. Load it only when needed and retain the function for the other artifacts.

Run the helper and the download inside the same orchestration invocation so the binary never becomes model text. Pass the raw MCP result (its `content` array includes metadata text and `resource.blob`) to `saveOriginDownload(result, {exec, directory, python, shell})`. Bind `exec` to the actual host command tool returning `{exit_code, output}`. Use a known absolute deliverable directory in the host; Python must be available there. Linux uses `shell="posix"`, Windows uses `shell="powershell"`; select the host's actual Python path. No Node runtime or browser globals are required by the helper.

The receiver sends at most 16384 base64 characters in each separate Python command, writes a new temporary file under a unique output directory, verifies the complete size and SHA256, and publishes it without overwriting existing files. It does not use `atob`, `Buffer`, imports, a long-running terminal or `write_stdin`. Do not replace its command-per-chunk transport with an interactive stdin stream: a non-TTY command may receive EOF immediately.

Output only the final receipt. Offer a host-supported file link/attachment only after successful verification. Review PNG directly; re-open/check the PDF, SVG and OPJU through appropriate tools. If a host has no authorized byte-saving or command facility, report that concrete delivery limitation; do not invent URLs, upload to third parties, or ask the user to decode data manually.

The receiver writes only files in the host output directory. It neither controls Origin nor requires a development checkout on the Origin computer. Follow user authorization and the host's tool permissions.

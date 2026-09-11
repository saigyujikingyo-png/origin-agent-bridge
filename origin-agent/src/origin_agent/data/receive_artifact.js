/* Host-side receiver for MCP embedded files. No browser globals, filesystem imports or live stdin.
 * Paste this function into the host orchestration runtime, then supply its command tool as exec.
 * Blob contents stay in program variables; only the final receipt should reach model text.
 */
async function saveOriginDownload(result, {exec, directory, python = "python3", shell = "posix"}) {
  if (!["posix", "powershell"].includes(shell)) throw new Error("Unsupported command shell");
  if (typeof exec !== "function") throw new Error("Supply the host command tool as exec");
  if (typeof directory !== "string" || !/^(\/|[A-Za-z]:[\\/])/.test(directory) || directory.includes("\0"))
    throw new Error("Use an absolute host output directory");
  if (result.isError || result.is_error) throw new Error("Origin download failed");
  const content = result.content || [];
  const resources = content.filter(c => c.type === "resource" && typeof c.resource?.blob === "string");
  const info = content.filter(c => c.type === "text").map(c => {
    try { return JSON.parse(c.text); } catch { return {}; }
  }).find(c => c.artifact_id && c.sha256);
  if (resources.length !== 1 || !info) throw new Error("Expected one binary resource and its receipt");
  const match = /^([a-f0-9]{32})\/([A-Za-z0-9][A-Za-z0-9._-]{0,120})$/.exec(info.artifact_id);
  if (!match || resources[0].resource.uri !== "origin://artifacts/" + info.artifact_id)
    throw new Error("Invalid artifact identity");
  if (!Number.isSafeInteger(info.bytes) || info.bytes < 0 || info.bytes > 32 * 1024 * 1024 ||
      !/^[a-f0-9]{64}$/.test(info.sha256)) throw new Error("Invalid size or digest");
  const blob = resources[0].resource.blob;
  if (blob.length !== Math.ceil(info.bytes / 3) * 4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(blob))
    throw new Error("Invalid base64 content");
  const quote = value => shell === "powershell"
    ? "'" + value.replace(/'/g, "''") + "'"
    : "'" + value.replace(/'/g, "'\\''") + "'";
  const command = script => (shell === "powershell" ? "& " : "") + quote(python) + " -c " + quote(script);
  // JSON encoding is only for Python string literals; quote() separately protects the shell.
  const literal = value => JSON.stringify(value);
  const folder = directory.replace(/[\\/]$/, "") + "/origin-" + match[1] + "-" +
    Date.now().toString(36) + "-" + Math.random().toString(16).slice(2, 10);
  const target = folder + "/" + match[2];
  const temporary = target + ".part";
  const run = async script => {
    const response = await exec({cmd: command(script), max_output_tokens: 500});
    if (response.exit_code !== 0)
      throw new Error("Host receiver command failed: " + String(response.output || response.exit_code).slice(-1200));
    return response;
  };
  for (let offset = 0; offset < Math.max(1, blob.length); offset += 16384) {
    const code = [
      "import base64",
      "from pathlib import Path",
      "p=Path(" + literal(temporary) + ")",
      ...(offset === 0 ? ["p.parent.mkdir(parents=True,exist_ok=False)"] : []),
      "data=base64.b64decode(" + literal(blob.slice(offset, offset + 16384)) + ",validate=True)",
      "with p.open(" + literal(offset === 0 ? "xb" : "ab") + ") as stream:",
      "    assert stream.write(data)==len(data)",
    ].join("\n");
    await run(code);
  }
  const checked = await run([
    "import hashlib,json,os",
    "from pathlib import Path",
    "p=Path(" + literal(temporary) + ")",
    "target=Path(" + literal(target) + ")",
    "size=p.stat().st_size",
    "assert size==" + info.bytes + ", 'Received size mismatch'",
    "with p.open('rb') as stream:",
    "    digest=hashlib.file_digest(stream,'sha256').hexdigest()",
    "assert digest==" + literal(info.sha256) + ", 'Received SHA256 mismatch'",
    "os.link(p,target)", // Atomically publish only after verification; never overwrite an existing file.
    "p.unlink()",
    "print(json.dumps(dict(path=str(target),bytes=size,sha256=digest)))",
  ].join("\n"));
  const receipt = JSON.parse(checked.output.trim().split(/\r?\n/).pop());
  if (receipt.bytes !== info.bytes || receipt.sha256 !== info.sha256) throw new Error("Invalid host receipt");
  return {...receipt, artifact_id: info.artifact_id};
}
if (typeof module !== "undefined") module.exports = {saveOriginDownload};

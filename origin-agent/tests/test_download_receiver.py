"""Real host-file reception without browser globals or an interactive stdin session."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

NODE_TEST = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const [source, directory, python] = process.argv.slice(1);
const context = vm.createContext({});
assert.equal(vm.runInContext('typeof atob', context), 'undefined');
assert.equal(vm.runInContext('typeof Buffer', context), 'undefined');
const receive = vm.runInContext(fs.readFileSync(source, 'utf8') + ';saveOriginDownload;', context);
let commands = 0;
const shell = os.platform() === 'win32' ? 'powershell' : 'posix';
const exec = async ({cmd}) => {
  commands++;
  const r = shell === 'powershell'
    ? spawnSync('pwsh', ['-NoProfile', '-NonInteractive', '-Command', cmd], {encoding:'utf8'})
    : spawnSync('sh', ['-c', cmd], {encoding:'utf8'});
  return {exit_code:r.status, output:r.stdout + r.stderr};
};
function response(payload) {
  const artifact_id = 'a'.repeat(32) + '/project.opju';
  const sha256 = crypto.createHash('sha256').update(payload).digest('hex');
  return {content:[
    {type:'text',text:JSON.stringify({artifact_id,sha256,bytes:payload.length})},
    {type:'resource',resource:{uri:'origin://artifacts/'+artifact_id,blob:payload.toString('base64')}}
  ]};
}
(async () => {
  const bytes = Buffer.alloc(131071);
  for (let i=0;i<bytes.length;i++) bytes[i]=(i*17)%256;
  const options = {exec, directory:path.join(directory, "space ' quote $ and &"), python, shell};
  const receipt = await receive(response(bytes), options);
  assert.deepEqual(fs.readFileSync(receipt.path), bytes);
  assert.equal(receipt.bytes, bytes.length);
  assert(!fs.existsSync(receipt.path+'.part'));
  assert(commands > 2);
  const previous=commands;
  const invalid=response(bytes);
  invalid.content[1].resource.blob='$(echo unsafe)';
  await assert.rejects(receive(invalid, options), /base64/);
  assert.equal(commands,previous);
  const wrong=response(Buffer.from('original data'));
  wrong.content[1].resource.blob=Buffer.from('modified data').toString('base64');
  await assert.rejects(receive(wrong, options), /SHA256 mismatch/);
  console.log(JSON.stringify({passed:true,bytes:receipt.bytes,commands,browser_globals_required:false}));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""


def test_receiver_across_real_shell_without_browser_globals(tmp_path):
    node = shutil.which("node")
    if not node or (os.name == "nt" and not shutil.which("pwsh")):
        pytest.skip("Node and the platform shell are needed only for this host-adapter test")
    helper = Path(__file__).resolve().parents[1] / "skills/origin-workflow/scripts/receive_artifact.js"
    result = subprocess.run(
        [node, "-e", NODE_TEST, str(helper), str(tmp_path), sys.executable],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed":true' in result.stdout

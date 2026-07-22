import assert from "node:assert/strict"
import { chmodSync, existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"
import { spawnSync } from "node:child_process"
import test from "node:test"
import { fileURLToPath } from "node:url"

import {
  buildUvArgs,
  cacheRoot,
  parsePythonVersion,
  supportsPython,
  venvPython,
} from "../lib/launcher.js"

const PACKAGE_ROOT = fileURLToPath(new URL("..", import.meta.url))
const PACKAGE_VERSION = JSON.parse(
  readFileSync(path.join(PACKAGE_ROOT, "package.json"), "utf8"),
).version

test("buildUvArgs pins the matching Python package version", () => {
  assert.deepEqual(
    buildUvArgs(["dashboard", "open"], "1.2.3"),
    ["tool", "run", "--from", "skillreg==1.2.3", "skillreg", "dashboard", "open"],
  )
})

test("Python version parsing enforces the supported minimum", () => {
  assert.deepEqual(parsePythonVersion("3.13\n"), [3, 13])
  assert.equal(supportsPython([3, 8]), false)
  assert.equal(supportsPython([3, 9]), true)
  assert.equal(supportsPython([4, 0]), true)
  assert.equal(supportsPython(null), false)
})

test("cache paths are platform aware and overridable", () => {
  assert.equal(cacheRoot({ SKILLREG_NPM_CACHE_DIR: "./cache" }, "linux", "/home/me"), path.resolve("cache"))
  assert.equal(cacheRoot({ XDG_CACHE_HOME: "/tmp/cache" }, "linux", "/home/me"), "/tmp/cache/skillreg/npm")
  assert.equal(cacheRoot({}, "darwin", "/Users/me"), "/Users/me/Library/Caches/skillreg/npm")
  assert.equal(venvPython("/tmp/venv", "linux"), "/tmp/venv/bin/python")
  assert.equal(venvPython("C:\\venv", "win32"), path.join("C:\\venv", "Scripts", "python.exe"))
})

test("CLI delegates arguments to uv with an exact skillreg version", { skip: process.platform === "win32" }, () => {
  const directory = mkdtempSync(path.join(os.tmpdir(), "skillreg-npm-test-"))
  const fakeUv = path.join(directory, "uv")
  writeFileSync(fakeUv, "#!/bin/sh\nprintf '%s\\n' \"$@\"\n", "utf8")
  chmodSync(fakeUv, 0o755)

  const result = spawnSync(
    process.execPath,
    [path.join(PACKAGE_ROOT, "bin", "skillreg.js"), "dashboard", "open"],
    {
      encoding: "utf8",
      env: { ...process.env, SKILLREG_UV: fakeUv },
    },
  )

  assert.equal(result.status, 0, result.stderr)
  assert.deepEqual(
    result.stdout.trim().split("\n"),
    ["tool", "run", "--from", `skillreg==${PACKAGE_VERSION}`, "skillreg", "dashboard", "open"],
  )
})

test("CLI bootstraps an isolated environment when uv is unavailable", { skip: process.platform === "win32" }, () => {
  const directory = mkdtempSync(path.join(os.tmpdir(), "skillreg-npm-python-test-"))
  const fakePython = path.join(directory, "python3")
  const cache = path.join(directory, "cache")
  writeFileSync(
    fakePython,
    [
      "#!/bin/sh",
      "if [ \"$1\" = \"-c\" ]; then echo 3.11; exit 0; fi",
      "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"venv\" ]; then",
      "  mkdir -p \"$3/bin\"",
      "  cp \"$0\" \"$3/bin/python\"",
      "  exit 0",
      "fi",
      "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"pip\" ]; then exit 0; fi",
      "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"skillreg.cli\" ]; then shift 2; printf '%s\\n' \"$@\"; fi",
      "",
    ].join("\n"),
    "utf8",
  )
  chmodSync(fakePython, 0o755)

  const result = spawnSync(
    process.execPath,
    [path.join(PACKAGE_ROOT, "bin", "skillreg.js"), "--version"],
    {
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: "/usr/bin:/bin",
        SKILLREG_PYTHON: fakePython,
        SKILLREG_NPM_CACHE_DIR: cache,
      },
    },
  )

  assert.equal(result.status, 0, result.stderr)
  assert.equal(result.stdout.trim(), "--version")
  assert.equal(
    existsSync(path.join(cache, "python", PACKAGE_VERSION, ".skillreg-package")),
    true,
  )
})

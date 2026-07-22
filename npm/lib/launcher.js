import { spawnSync } from "node:child_process"
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs"
import os from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"

const PACKAGE_ROOT = fileURLToPath(new URL("..", import.meta.url))
const PACKAGE_JSON = JSON.parse(readFileSync(path.join(PACKAGE_ROOT, "package.json"), "utf8"))
const PACKAGE_SPEC = `skillreg==${PACKAGE_JSON.version}`
const MINIMUM_PYTHON = [3, 9]
const BOOTSTRAP_LOCK_TIMEOUT_MS = 180_000
const STALE_LOCK_MS = 600_000
const sleepSignal = new Int32Array(new SharedArrayBuffer(4))

function spawn(command, args, options = {}) {
  return spawnSync(command, args, {
    windowsHide: true,
    ...options,
  })
}

function commandWorks(command, args) {
  const result = spawn(command, args, { stdio: "ignore" })
  return !result.error && result.status === 0
}

export function buildUvArgs(cliArgs, version = PACKAGE_JSON.version) {
  return ["tool", "run", "--from", `skillreg==${version}`, "skillreg", ...cliArgs]
}

export function parsePythonVersion(value) {
  const match = String(value).trim().match(/^(\d+)\.(\d+)$/)
  return match ? [Number(match[1]), Number(match[2])] : null
}

export function supportsPython(version) {
  if (!version) return false
  return version[0] > MINIMUM_PYTHON[0]
    || (version[0] === MINIMUM_PYTHON[0] && version[1] >= MINIMUM_PYTHON[1])
}

export function cacheRoot(env = process.env, platform = process.platform, home = os.homedir()) {
  if (env.SKILLREG_NPM_CACHE_DIR) return path.resolve(env.SKILLREG_NPM_CACHE_DIR)
  if (platform === "win32" && env.LOCALAPPDATA) {
    return path.join(env.LOCALAPPDATA, "skillreg", "npm")
  }
  if (platform === "darwin") return path.join(home, "Library", "Caches", "skillreg", "npm")
  if (env.XDG_CACHE_HOME) return path.join(env.XDG_CACHE_HOME, "skillreg", "npm")
  return path.join(home, ".cache", "skillreg", "npm")
}

export function venvPython(venv, platform = process.platform) {
  return platform === "win32"
    ? path.join(venv, "Scripts", "python.exe")
    : path.join(venv, "bin", "python")
}

function findUv(env) {
  if (env.SKILLREG_UV) return env.SKILLREG_UV
  return commandWorks("uv", ["--version"]) ? "uv" : null
}

function pythonCandidates(env, platform) {
  if (env.SKILLREG_PYTHON) return [{ command: env.SKILLREG_PYTHON, prefix: [] }]
  const candidates = [
    { command: "python3", prefix: [] },
    { command: "python", prefix: [] },
  ]
  if (platform === "win32") candidates.unshift({ command: "py", prefix: ["-3"] })
  return candidates
}

function findPython(env, platform) {
  for (const candidate of pythonCandidates(env, platform)) {
    const result = spawn(
      candidate.command,
      [...candidate.prefix, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
      { encoding: "utf8" },
    )
    if (!result.error && result.status === 0 && supportsPython(parsePythonVersion(result.stdout))) {
      return candidate
    }
  }
  return null
}

function runInherited(command, args) {
  const result = spawn(command, args, { stdio: "inherit" })
  if (result.error) {
    console.error(`无法启动 ${command}: ${result.error.message}`)
    return 1
  }
  return result.status ?? 1
}

function environmentReady(executable, marker) {
  if (!existsSync(executable) || !existsSync(marker)) return false
  return readFileSync(marker, "utf8").trim() === PACKAGE_SPEC
}

function lockOwnerIsRunning(lock) {
  try {
    const pid = Number(readFileSync(lock, "utf8").trim())
    if (!Number.isInteger(pid) || pid <= 0) return true
    process.kill(pid, 0)
    return true
  } catch (error) {
    return error?.code === "EPERM"
  }
}

function acquireBootstrapLock(lock) {
  const deadline = Date.now() + BOOTSTRAP_LOCK_TIMEOUT_MS
  while (Date.now() < deadline) {
    try {
      const descriptor = openSync(lock, "wx")
      writeFileSync(descriptor, `${process.pid}\n`, "utf8")
      return descriptor
    } catch (error) {
      if (error?.code !== "EEXIST") throw error
      let stale = false
      try {
        stale = Date.now() - statSync(lock).mtimeMs > STALE_LOCK_MS
      } catch (statError) {
        if (statError?.code === "ENOENT") continue
        throw statError
      }
      if (stale || !lockOwnerIsRunning(lock)) {
        try {
          unlinkSync(lock)
        } catch (unlinkError) {
          if (unlinkError?.code !== "ENOENT") throw unlinkError
        }
        continue
      }
      Atomics.wait(sleepSignal, 0, 0, 250)
    }
  }
  return null
}

function ensurePythonEnvironment(python, env) {
  const environment = path.join(cacheRoot(env), "python", PACKAGE_JSON.version)
  const executable = venvPython(environment)
  const marker = path.join(environment, ".skillreg-package")
  const lock = `${environment}.lock`

  if (environmentReady(executable, marker)) return executable

  mkdirSync(path.dirname(environment), { recursive: true })
  const lockDescriptor = acquireBootstrapLock(lock)
  if (lockDescriptor === null) {
    console.error("等待 skillreg 隔离环境安装超时，请稍后重试")
    return null
  }

  try {
    if (environmentReady(executable, marker)) return executable

    console.error(`首次运行，正在安装 ${PACKAGE_SPEC}`)
    rmSync(environment, { recursive: true, force: true })

    const createResult = spawn(
      python.command,
      [...python.prefix, "-m", "venv", environment],
      { stdio: "inherit" },
    )
    if (createResult.error || createResult.status !== 0) {
      console.error("无法创建 Python 隔离环境，请安装 uv 或完整的 Python 3.9+")
      return null
    }

    const installResult = spawn(
      executable,
      ["-m", "pip", "install", "--disable-pip-version-check", PACKAGE_SPEC],
      { stdio: "inherit" },
    )
    if (installResult.error || installResult.status !== 0) {
      console.error(`无法从 PyPI 安装 ${PACKAGE_SPEC}`)
      return null
    }

    writeFileSync(marker, `${PACKAGE_SPEC}\n`, "utf8")
    return executable
  } finally {
    closeSync(lockDescriptor)
    unlinkSync(lock)
  }
}

export function runSkillreg(cliArgs, env = process.env) {
  const uv = findUv(env)
  if (uv) return runInherited(uv, buildUvArgs(cliArgs))

  const python = findPython(env, process.platform)
  if (!python) {
    console.error("skillreg 需要 uv，或 Python 3.9 及以上版本")
    console.error("安装 uv: https://docs.astral.sh/uv/getting-started/installation/")
    return 1
  }

  const executable = ensurePythonEnvironment(python, env)
  if (!executable) return 1
  return runInherited(executable, ["-m", "skillreg.cli", ...cliArgs])
}

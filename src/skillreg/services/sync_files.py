"""File operations shared by local sync and the dependency-free SSH worker

Keep this module compatible with Python 3.6 on remote hosts
"""

import base64
import ctypes
import errno
import hashlib
import io
import json
import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import time
from pathlib import Path

MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 10000
IGNORED = {
    ".git",
    "__pycache__",
    ".DS_Store",
    "Thumbs.db",
    ".sync-manifest.json",
    ".venv",
    "venv",
    "node_modules",
}
AGENTS = ["claude", "tclaude", "codebuddy", "codex", "tcodex", "agents", "agent"]
MAX_INVENTORY = 1000
MAX_DOCUMENT = 256 * 1024


class SyncError(ValueError):
    def __init__(self, message, code="invalid", retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def name_checked(name):
    if (
        not isinstance(name, str)
        or not name
        or name.startswith(".")
        or any(c in name for c in "/\\\x00\r\n")
    ):
        raise SyncError("Invalid skill name")
    return name


def root_checked(value):
    if not isinstance(value, str) or not value or any(c in value for c in "\x00\r\n"):
        raise SyncError("Invalid target path")
    path = Path(value).expanduser()
    if (
        not path.is_absolute()
        or ".." in path.parts
        or path == Path(path.anchor)
        or path == Path.home()
    ):
        raise SyncError(
            "Target must be an absolute skill directory below a root or home directory"
        )
    for component in [path] + list(path.parents):
        if component.is_symlink():
            raise SyncError(
                "Symlink target paths are not supported: " + str(component),
                "unsafe-path",
            )
    if path.exists() and not path.is_dir():
        raise SyncError("Target is not a directory", "unsafe-path")
    return path


def tree_snapshot(root):
    root = Path(root)
    if root.is_symlink():
        raise SyncError(
            "Symlink skill directories are not supported: " + str(root), "unsafe-path"
        )
    if not root.exists():
        return {"exists": False, "digest": None, "files": {}, "bytes": 0}
    if not root.is_dir():
        raise SyncError(
            "Skill path is not a directory: " + str(root), "unsafe-path"
        )
    files = {}
    total = 0
    for directory, dirs, names in os.walk(str(root), followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED and not d.startswith("._"))
        for name in dirs + sorted(names):
            if name in IGNORED or name.startswith("._"):
                continue
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise SyncError(
                    "Only regular skill files and directories are supported: "
                    + str(path),
                    "unsafe-path",
                )
            if stat.S_ISDIR(mode):
                continue
            if name.endswith(".pyc"):
                continue
            size = path.stat().st_size
            total += size
            if total > MAX_BYTES or len(files) >= MAX_FILES:
                raise SyncError("Skill exceeds file or size limit", "resource-limit")
            with path.open("rb") as stream:
                content = stream.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise SyncError("Skill file exceeds size limit", "resource-limit")
            files[path.relative_to(root).as_posix()] = {
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
                "executable": bool(mode & 0o111),
            }
    digest = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"exists": True, "digest": digest, "files": files, "bytes": total}


def make_bundle(root):
    snapshot = tree_snapshot(root)
    if "SKILL.md" not in snapshot["files"]:
        raise SyncError("Skill has no SKILL.md")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for relative, info in sorted(snapshot["files"].items()):
            content = (Path(root) / relative).read_bytes()
            if hashlib.sha256(content).hexdigest() != info["sha256"]:
                raise SyncError(
                    "Source changed while preparing sync; preview again",
                    "source-changed",
                )
            member = tarfile.TarInfo(relative)
            member.size = len(content)
            member.mode = 0o755 if info["executable"] else 0o644
            archive.addfile(member, io.BytesIO(content))
    bundle = buffer.getvalue()
    return (
        snapshot,
        base64.b64encode(bundle).decode("ascii"),
        hashlib.sha256(bundle).hexdigest(),
    )


def unpack_bundle(encoded, digest, destination):
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise SyncError("Invalid sync bundle") from exc
    if len(raw) > MAX_BYTES + 1024 * 1024 or hashlib.sha256(raw).hexdigest() != digest:
        raise SyncError("Sync bundle checksum mismatch", "checksum-failed")
    count = total = 0
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            relative = Path(member.name)
            if (
                not member.isfile()
                or relative.is_absolute()
                or ".." in relative.parts
                or "\\" in member.name
                or ":" in member.name
                or member.name in seen
            ):
                raise SyncError("Unsafe sync archive member", "unsafe-path")
            if not relative.parts or any(p in IGNORED for p in relative.parts):
                raise SyncError("Reserved sync archive path", "unsafe-path")
            count += 1
            total += member.size
            if count > MAX_FILES or total > MAX_BYTES:
                raise SyncError("Skill exceeds file or size limit", "resource-limit")
            seen.add(member.name)
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, output.open("xb") as target:
                shutil.copyfileobj(source, target)
            output.chmod(0o755 if member.mode & 0o111 else 0o644)


def exchange_directories(left, right):
    """Atomically exchange two existing directories without an absent target window"""
    libc = ctypes.CDLL(None, use_errno=True)
    a, b = os.fsencode(str(left)), os.fsencode(str(right))
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(-100, ctypes.c_char_p(a), -100, ctypes.c_char_p(b), 2)
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(ctypes.c_char_p(a), ctypes.c_char_p(b), 2)
    else:
        raise SyncError(
            "Atomic directory exchange is unavailable on this host",
            "unsupported-platform",
        )
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            raise SyncError(
                "Target filesystem does not support atomic directory exchange",
                "unsupported-filesystem",
            )
        raise OSError(error, os.strerror(error))


def replace_directory(temporary, destination):
    """Replace an existing directory atomically when supported, with backup rollback fallback"""
    try:
        exchange_directories(temporary, destination)
        return
    except SyncError as exc:
        if exc.code not in ("unsupported-platform", "unsupported-filesystem"):
            raise
    backup = Path(
        tempfile.mkdtemp(prefix=".skillreg-backup-", dir=str(destination.parent))
    )
    os.rmdir(str(backup))
    moved_new = False
    os.rename(str(destination), str(backup))
    try:
        os.rename(str(temporary), str(destination))
        moved_new = True
    except Exception:
        if not destination.exists() and backup.exists():
            try:
                os.rename(str(backup), str(destination))
            except OSError:
                pass
        raise
    finally:
        if moved_new and backup.exists():
            shutil.rmtree(str(backup), ignore_errors=True)


def _acquire_file_lock(fd, timeout):
    try:
        import fcntl
    except ImportError:
        return
    deadline = time.monotonic() + max(0.0, float(timeout))
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            pass
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise
        if time.monotonic() >= deadline:
            raise SyncError("Another sync is writing this target", "target-busy", True)
        time.sleep(0.05)


def install(request):
    root = root_checked(request["path"])
    name = name_checked(request["name"])
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".skillreg-sync.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(lock_path), flags, 0o600)
    with os.fdopen(descriptor, "a") as lock:
        _acquire_file_lock(lock.fileno(), request.get("lockTimeout", 2.0))
        destination = root / name
        current = tree_snapshot(destination)
        if "expectedDigest" in request and current["digest"] != request.get(
            "expectedDigest"
        ):
            raise SyncError(
                "Target changed since preview; preview again", "target-changed", True
            )
        if (
            current["exists"]
            and current["digest"] != request["sourceDigest"]
            and not request.get("force")
        ):
            raise SyncError(
                "Target differs; confirm overwrite after preview", "conflict"
            )
        if current["digest"] == request["sourceDigest"]:
            return {"status": "synced", "changed": False, "digest": current["digest"]}
        temporary = Path(tempfile.mkdtemp(prefix=".skillreg-stage-", dir=str(root)))
        try:
            unpack_bundle(request["bundle"], request["bundleDigest"], temporary)
            prepared = tree_snapshot(temporary)
            if (
                "SKILL.md" not in prepared["files"]
                or prepared["digest"] != request["sourceDigest"]
            ):
                raise SyncError("Unpacked content checksum mismatch", "checksum-failed")
            marker = {
                "schemaVersion": 1,
                "workspaceId": request["workspaceId"],
                "runId": request["runId"],
                "digest": prepared["digest"],
            }
            (temporary / ".sync-manifest.json").write_text(
                json.dumps(marker), encoding="utf-8"
            )
            root_checked(str(root))
            if tree_snapshot(destination)["digest"] != current["digest"]:
                raise SyncError(
                    "Target changed while transferring; preview again",
                    "target-changed",
                    True,
                )
            if destination.exists():
                replace_directory(temporary, destination)
            else:
                os.rename(str(temporary), str(destination))
            verified = tree_snapshot(destination)
            if verified["digest"] != request["sourceDigest"]:
                raise SyncError(
                    "Installed content does not match source", "verification-failed"
                )
            return {"status": "synced", "changed": True, "digest": verified["digest"]}
        finally:
            if temporary.exists():
                shutil.rmtree(str(temporary))


def inventory(value):
    root = root_checked(value)
    result = {
        "path": str(root),
        "exists": root.exists(),
        "skills": [],
        "skipped": [],
        "truncated": False,
    }
    if not result["exists"]:
        return result
    with os.scandir(str(root)) as entries:
        for index, entry in enumerate(entries):
            if (
                index >= MAX_FILES
                or len(result["skills"]) + len(result["skipped"]) >= MAX_INVENTORY
            ):
                result["truncated"] = True
                break
            if entry.name.startswith("."):
                continue
            try:
                name_checked(entry.name)
                if entry.is_symlink():
                    raise SyncError(
                        "Symlink directories are not inspected", "unsafe-path"
                    )
                if not entry.is_dir(follow_symlinks=False):
                    continue
                document = Path(entry.path) / "SKILL.md"
                try:
                    info = document.lstat()
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise SyncError("SKILL.md must be a regular file", "unsafe-path")
                result["skills"].append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "documentSize": info.st_size,
                    }
                )
            except (OSError, SyncError) as exc:
                result["skipped"].append({"name": entry.name, "message": str(exc)})
    result["skills"].sort(key=lambda item: item["name"].lower())
    return result


def read_skill_document(value, name):
    root = root_checked(value)
    directory = root_checked(str(root / name_checked(name)))
    descriptor = os.open(
        str(directory / "SKILL.md"), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise SyncError("SKILL.md must be a regular file", "unsafe-path")
        content = stream.read(MAX_DOCUMENT + 1)
    return {
        "name": name,
        "content": content[:MAX_DOCUMENT].decode("utf-8", errors="replace"),
        "truncated": len(content) > MAX_DOCUMENT,
    }


def dispatch(request):
    operation = request.get("operation")
    if operation == "check":
        return {
            "hostname": platform.node(),
            "platform": sys.platform,
            "python": platform.python_version(),
            "home": str(Path.home()),
            "user": __import__("getpass").getuser(),
        }
    if operation == "discover":
        root = Path(request.get("root") or str(Path.home())).expanduser()
        if not root.is_absolute() or not root.is_dir():
            raise SyncError("Project directory does not exist")
        result = []
        for agent in AGENTS:
            if (root / ("." + agent)).is_dir():
                target = root / ("." + agent) / "skills"
                result.append(
                    {
                        "agentKind": agent,
                        "path": str(target),
                        "exists": target.is_dir(),
                        "scope": "project" if request.get("root") else "global",
                        "projectRoot": str(root) if request.get("root") else None,
                    }
                )
        return {"root": str(root), "targets": result}
    if operation == "inspect":
        root = root_checked(request["path"])
        parent = root
        while not parent.exists():
            parent = parent.parent
        return {
            "path": str(root),
            "exists": root.exists(),
            "writable": os.access(str(parent), os.W_OK),
            "skills": {
                name_checked(name): tree_snapshot(root / name)
                for name in request["names"]
            },
        }
    if operation == "install":
        return install(request)
    if operation == "inventory":
        return inventory(request["path"])
    if operation == "read-skill":
        return read_skill_document(request["path"], request["name"])
    raise SyncError("Unknown sync operation")


def main():
    try:
        raw = sys.stdin.buffer.read(48 * 1024 * 1024 + 1)
        if len(raw) > 48 * 1024 * 1024:
            raise SyncError("Request exceeds size limit", "resource-limit")
        result = dispatch(json.loads(raw.decode("utf-8")))
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "code": getattr(exc, "code", "io-error"),
                        "message": str(exc),
                        "retryable": getattr(exc, "retryable", False),
                    },
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

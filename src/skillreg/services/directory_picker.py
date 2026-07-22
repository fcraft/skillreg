"""Open a native directory picker on the machine running skillreg."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class DirectoryPickerUnavailableError(RuntimeError):
    """Raised when the current desktop has no supported directory picker."""


def select_directory(initial_path: str | None = None) -> str | None:
    """Return the selected absolute directory path, or ``None`` when cancelled."""
    initial = _resolve_initial_path(initial_path)

    if sys.platform == "darwin":
        result = _select_macos_directory(initial)
    elif sys.platform == "win32":
        result = _select_windows_directory(initial)
    else:
        result = _select_linux_directory(initial)

    if result is None:
        return None

    selected = Path(result).expanduser().resolve()
    if not selected.is_dir():
        raise ValueError(f"Selected path is not a directory: {selected}")
    return str(selected)


def _resolve_initial_path(initial_path: str | None) -> Path:
    if initial_path:
        candidate = Path(initial_path).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
        if candidate.parent.is_dir():
            return candidate.parent.resolve()
    return Path.home().resolve()


def _select_macos_directory(initial: Path) -> str | None:
    escaped_initial = str(initial).replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'POSIX path of (choose folder with prompt "选择 Skill Workspace" '
        f'default location (POSIX file "{escaped_initial}"))'
    )
    return _run_picker(["osascript", "-e", script], cancel_codes={1})


def _select_windows_directory(initial: Path) -> str | None:
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if not executable:
        raise DirectoryPickerUnavailableError("No native directory picker is available")

    selected_path = str(initial).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$dialog.Description = '选择 Skill Workspace'; "
        f"$dialog.SelectedPath = '{selected_path}'; "
        "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "[Console]::Out.Write($dialog.SelectedPath) }"
    )
    return _run_picker(
        [executable, "-NoProfile", "-STA", "-Command", script],
        cancel_codes=set(),
    )


def _select_linux_directory(initial: Path) -> str | None:
    zenity = shutil.which("zenity")
    if zenity:
        return _run_picker(
            [
                zenity,
                "--file-selection",
                "--directory",
                "--title=选择 Skill Workspace",
                f"--filename={initial}/",
            ],
            cancel_codes={1},
        )

    kdialog = shutil.which("kdialog")
    if kdialog:
        return _run_picker(
            [kdialog, "--getexistingdirectory", str(initial), "--title", "选择 Skill Workspace"],
            cancel_codes={1},
        )

    raise DirectoryPickerUnavailableError("No native directory picker is available")


def _run_picker(command: list[str], cancel_codes: set[int]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise DirectoryPickerUnavailableError("No native directory picker is available") from exc

    output = result.stdout.strip()
    if result.returncode == 0:
        return output or None
    if result.returncode in cancel_codes:
        return None

    message = result.stderr.strip() or "Native directory picker failed"
    raise RuntimeError(message)

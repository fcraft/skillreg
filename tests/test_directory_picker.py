"""Tests for the native directory picker service."""

from __future__ import annotations

import subprocess

import pytest

from skillreg.services import directory_picker


def test_macos_picker_returns_selected_directory(tmp_path, monkeypatch):
    selected = tmp_path / "selected-workspace"
    selected.mkdir()
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout=f"{selected}\n", stderr="")

    monkeypatch.setattr(directory_picker.sys, "platform", "darwin")
    monkeypatch.setattr(directory_picker.subprocess, "run", fake_run)

    result = directory_picker.select_directory(str(tmp_path))

    assert result == str(selected.resolve())
    assert captured["command"][:2] == ["osascript", "-e"]
    assert str(tmp_path) in captured["command"][2]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "check": False,
    }


def test_macos_picker_returns_none_when_cancelled(tmp_path, monkeypatch):
    monkeypatch.setattr(directory_picker.sys, "platform", "darwin")
    monkeypatch.setattr(
        directory_picker.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stdout="", stderr="cancelled"),
    )

    assert directory_picker.select_directory(str(tmp_path)) is None


def test_linux_picker_reports_unavailable(monkeypatch):
    monkeypatch.setattr(directory_picker.sys, "platform", "linux")
    monkeypatch.setattr(directory_picker.shutil, "which", lambda name: None)

    with pytest.raises(directory_picker.DirectoryPickerUnavailableError):
        directory_picker.select_directory()

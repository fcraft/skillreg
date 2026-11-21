"""Built-in AI Agent / Coding Agent skill directory conventions and auto-detection.

Directory layouts, environment variable overrides, shared-directory semantics,
and leftover-directory filtering are modeled on common coding agent conventions
(referencing https://github.com/yetone/magpie) while preserving existing
skillreg defaults.
"""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping

DEFAULT_CUSTOM_ICON = "custom"


# Runtime folders frequently left behind after uninstalling an agent (never
# sufficient by themselves to treat an agent as installed).
LEFTOVER_DIR_NAMES: frozenset[str] = frozenset({
    "logs",
    "log",
    "debug",
    "diagnostics",
    "cache",
})

IGNORED_DIR_ENTRIES: frozenset[str] = frozenset({
    ".DS_Store",
    "Thumbs.db",
})


@dataclass(frozen=True)
class AgentSpec:
    """Built-in specification for a coding agent's skill directories."""

    id: str
    name: str
    global_root: str
    icon: str
    skills_subdir: str = "skills"
    aliases: tuple[str, ...] = ()
    project_rel: str | None = None
    project_root: str | None = None
    env_var: str | None = None
    xdg_subpath: str | None = None
    bins: tuple[str, ...] = ()
    shared_skills: bool = False
    reads_shared: bool = False
    legacy: bool = False

    @property
    def default_rel_path(self) -> str:
        return f"{self.global_root}/{self.skills_subdir}"


BUILTIN_AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        id="agents",
        name="Shared Agents",
        icon="agents",
        aliases=("shared", "shared-agents"),
        global_root=".agents",
        project_rel=".agents/skills",
        project_root=".agents",
        shared_skills=True,
        reads_shared=True,
    ),
    AgentSpec(
        id="claude",
        name="Claude Code",
        icon="claude",
        aliases=("claude-code",),
        global_root=".claude",
        project_rel=".claude/skills",
        project_root=".claude",
        env_var="CLAUDE_CONFIG_DIR",
        bins=("claude",),
    ),
    AgentSpec(
        id="codex",
        name="Codex",
        icon="codex",
        aliases=("codex-cli",),
        global_root=".codex",
        project_rel=".codex/skills",
        project_root=".codex",
        env_var="CODEX_HOME",
        bins=("codex",),
        reads_shared=True,
    ),
    AgentSpec(
        id="cursor",
        name="Cursor",
        icon="cursor",
        aliases=("cursor-cli", "cursor-agent"),
        global_root=".cursor",
        project_rel=".cursor/skills",
        project_root=".cursor",
        bins=("cursor-agent",),
    ),
    AgentSpec(
        id="gemini",
        name="Gemini CLI",
        icon="gemini",
        aliases=("gemini-cli",),
        global_root=".gemini",
        project_rel=".gemini/skills",
        project_root=".gemini",
        bins=("gemini",),
        reads_shared=True,
    ),
    AgentSpec(
        id="antigravity",
        name="Antigravity",
        icon="antigravity",
        aliases=("agy",),
        global_root=".gemini/config",
        bins=("agy",),
    ),
    AgentSpec(
        id="copilot",
        name="GitHub Copilot",
        icon="copilot",
        aliases=("gh-copilot", "copilot-cli"),
        global_root=".copilot",
        project_rel=".copilot/skills",
        project_root=".copilot",
        env_var="COPILOT_HOME",
        bins=("copilot",),
    ),
    AgentSpec(
        id="opencode",
        name="OpenCode",
        icon="opencode",
        aliases=("oc",),
        global_root=".config/opencode",
        project_rel=".opencode/skills",
        project_root=".opencode",
        env_var="OPENCODE_CONFIG_DIR",
        xdg_subpath="opencode",
        bins=("opencode",),
        reads_shared=True,
    ),
    AgentSpec(
        id="codebuddy",
        name="CodeBuddy",
        icon="codebuddy",
        aliases=("codebuddy-code", "cbc"),
        global_root=".codebuddy",
        project_rel=".codebuddy/skills",
        project_root=".codebuddy",
        env_var="CODEBUDDY_CONFIG_DIR",
        bins=("codebuddy",),
    ),
    AgentSpec(
        id="workbuddy",
        name="WorkBuddy",
        icon="workbuddy",
        aliases=("workbuddy-ai",),
        global_root=".workbuddy",
        env_var="WORKBUDDY_CONFIG_DIR",
    ),
    AgentSpec(
        id="pi",
        name="Pi",
        icon="pi",
        aliases=("pi-coding-agent",),
        global_root=".pi/agent",
        project_rel=".pi/skills",
        project_root=".pi",
        env_var="PI_CODING_AGENT_DIR",
        reads_shared=True,
    ),
    AgentSpec(
        id="cline",
        name="Cline",
        icon="cline",
        aliases=("cline-cli",),
        global_root=".cline",
        project_rel=".cline/skills",
        project_root=".cline",
        bins=("cline",),
        reads_shared=True,
    ),
    AgentSpec(
        id="droid",
        name="Droid",
        icon="droid",
        aliases=("factory", "factory-droid"),
        global_root=".factory",
        project_rel=".factory/skills",
        project_root=".factory",
        bins=("droid",),
        reads_shared=True,
    ),
    AgentSpec(
        id="kimi",
        name="Kimi Code",
        icon="kimi",
        aliases=("kimi-code", "kimi-cli"),
        global_root=".kimi-code",
        env_var="KIMI_CODE_HOME",
        bins=("kimi",),
        reads_shared=True,
    ),
    AgentSpec(
        id="qwen",
        name="Qwen Code",
        icon="qwen",
        aliases=("qwen-code", "qwen-cli"),
        global_root=".qwen",
        project_rel=".qwen/skills",
        project_root=".qwen",
        env_var="QWEN_HOME",
        bins=("qwen",),
    ),
    AgentSpec(
        id="qoder",
        name="Qoder",
        icon="qoder",
        aliases=("qoder-cli", "qoder-cn"),
        global_root=".qoder",
        project_rel=".qoder/skills",
        project_root=".qoder",
        bins=("qoder",),
    ),
    AgentSpec(
        id="kiro",
        name="Kiro",
        icon="kiro",
        aliases=("kiro-cli",),
        global_root=".kiro",
        project_rel=".kiro/skills",
        project_root=".kiro",
        bins=("kiro-cli",),
    ),
    AgentSpec(
        id="crush",
        name="Crush",
        icon="crush",
        global_root=".config/crush",
        xdg_subpath="crush",
        bins=("crush",),
        reads_shared=True,
    ),
    AgentSpec(
        id="vibe",
        name="Mistral Vibe",
        icon="vibe",
        aliases=("mistral-vibe",),
        global_root=".vibe",
        env_var="VIBE_HOME",
        bins=("vibe",),
        reads_shared=True,
    ),
    AgentSpec(
        id="hermes",
        name="Hermes Agent",
        icon="hermes",
        aliases=("hermes-agent",),
        global_root=".hermes",
        env_var="HERMES_HOME",
        bins=("hermes",),
    ),
    AgentSpec(
        id="dsh",
        name="DeepSeek Harness",
        icon="dsh",
        aliases=("deepseek-harness",),
        global_root=".dsh",
        project_rel=".dsh/skills",
        project_root=".dsh",
        env_var="DSH_HOME",
        bins=("dsh",),
        reads_shared=True,
    ),
    AgentSpec(
        id="commandcode",
        name="Command Code",
        icon="commandcode",
        aliases=("command-code",),
        global_root=".commandcode",
        project_rel=".commandcode/skills",
        project_root=".commandcode",
        bins=("command-code",),
        reads_shared=True,
    ),
    AgentSpec(
        id="devin",
        name="Devin",
        icon="devin",
        aliases=("devin-cli",),
        global_root=".config/devin",
        xdg_subpath="devin",
        bins=("devin",),
        reads_shared=True,
    ),
    AgentSpec(
        id="grok",
        name="Grok Build",
        icon="grok",
        aliases=("grok-build",),
        global_root=".grok",
        env_var="GROK_HOME",
        reads_shared=True,
    ),
    AgentSpec(
        id="zcode",
        name="ZCode",
        icon="zcode",
        global_root=".zcode",
        reads_shared=True,
    ),
    AgentSpec(
        id="alma",
        name="Alma",
        icon="alma",
        global_root=".config/alma",
        reads_shared=True,
    ),
    AgentSpec(
        id="omp",
        name="Oh-My-Pi",
        icon="omp",
        aliases=("oh-my-pi",),
        global_root=".omp/agent",
        bins=("omp",),
        reads_shared=True,
    ),
    AgentSpec(
        id="minimax-code",
        name="MiniMax Code",
        icon="minimax-code",
        aliases=("minimax",),
        global_root=".minimax",
        env_var="MINIMAX_DATA_DIR",
    ),
    # Legacy skillreg conventions preserved for backward-compatible discovery.
    AgentSpec(
        id="tclaude",
        name="tclaude",
        icon="claude",
        global_root=".tclaude",
        project_rel=".tclaude/skills",
        project_root=".tclaude",
        legacy=True,
    ),
    AgentSpec(
        id="tcodex",
        name="tcodex",
        icon="codex",
        global_root=".tcodex",
        project_rel=".tcodex/skills",
        project_root=".tcodex",
        legacy=True,
    ),
    AgentSpec(
        id="agent",
        name="agent",
        icon="agent",
        global_root=".agent",
        project_rel=".agent/skills",
        project_root=".agent",
        legacy=True,
    ),
)

_BY_ID: dict[str, AgentSpec] = {spec.id: spec for spec in BUILTIN_AGENTS}


def list_builtin_agents(*, include_legacy: bool = False) -> list[AgentSpec]:
    """Return built-in agent specifications in display priority order."""
    if include_legacy:
        return list(BUILTIN_AGENTS)
    return [spec for spec in BUILTIN_AGENTS if not spec.legacy]


def project_agent_conventions() -> list[tuple[str, str]]:
    """Return (relative_skills_path, agent_id) tuples for project discovery."""
    return [
        (spec.project_rel, spec.id)
        for spec in BUILTIN_AGENTS
        if spec.project_rel is not None
    ]


def get_agent_spec(identifier: str) -> AgentSpec | None:
    """Resolve an AgentSpec by id, alias, or display name (case-insensitive)."""
    key = identifier.strip().lower()
    if not key:
        return None
    if key in _BY_ID:
        return _BY_ID[key]
    for spec in BUILTIN_AGENTS:
        if spec.name.lower() == key or any(alias.lower() == key for alias in spec.aliases):
            return spec
    return None


def make_builtin_target_id(path: str | Path) -> str:
    """Deterministic UUID5 matching sync_targets legacy local target IDs."""
    canonical = str(Path(path).expanduser().absolute())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "skillreg:local:" + canonical))


def _expand_abs_env(value: str | None, home: Path) -> Path | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned == "~":
        candidate = home
    elif cleaned.startswith(("~/", "~\\")):
        candidate = home / cleaned[2:]
    else:
        candidate = Path(cleaned)
    if not candidate.is_absolute():
        return None
    return Path(os.path.normpath(str(candidate)))


def _is_taken_by_non_dir(path: Path, stop_at: Path) -> bool:
    """Return True if path or an intermediate ancestor below stop_at is a non-dir."""
    current = path
    stop_norm = Path(os.path.normpath(str(stop_at)))
    while True:
        try:
            if current.exists() and not current.is_dir():
                return True
        except OSError:
            return True
        if Path(os.path.normpath(str(current))) == stop_norm or current.parent == current:
            break
        current = current.parent
    return False


def _dir_has_agent_evidence(
    root_dir: Path,
    skills_dir: Path,
    *,
    skills_subdir: str,
    shared_skills: bool,
) -> str | None:
    """Inspect a candidate agent directory and classify detection evidence.

    Follows magpie's false-positive guard:
    - A folder containing only leftover runtime folders (logs/log/debug/
      diagnostics/cache) or OS metadata (.DS_Store/Thumbs.db) is not treated
      as installed.
    - A folder containing only an empty ``skills/`` scaffold created by third-
      party skill installers is not treated as installed unless ``skills/``
      actually holds skill entries or the agent has its own config/state files
      beside it.
    - An empty root folder itself (0 entries) still counts as present to stay
      compatible with freshly created agent folders and tests.
    """
    if not root_dir.is_dir():
        return None

    try:
        entries = list(root_dir.iterdir())
    except OSError:
        return None

    if shared_skills:
        if skills_dir.is_dir():
            return "skills"
        if not entries:
            return "directory"
        for entry in entries:
            if entry.name in IGNORED_DIR_ENTRIES:
                continue
            if entry.is_dir() and entry.name.lower() in LEFTOVER_DIR_NAMES:
                continue
            return "directory"
        return None

    if not entries:
        return "directory"

    has_meaningful_entry = False
    for entry in entries:
        name = entry.name
        if name in IGNORED_DIR_ENTRIES:
            continue
        if name == skills_subdir:
            continue
        if entry.is_dir() and name.lower() in LEFTOVER_DIR_NAMES:
            continue
        has_meaningful_entry = True
        break

    if has_meaningful_entry:
        return "directory"

    if skills_dir.is_dir():
        try:
            if any(
                child.name not in IGNORED_DIR_ENTRIES
                for child in skills_dir.iterdir()
            ):
                return "skills"
        except OSError:
            pass

    return None


def _rel_display(skills_dir: Path, home: Path, fallback_rel: str) -> str:
    try:
        rel = skills_dir.relative_to(home)
        return rel.as_posix()
    except ValueError:
        return str(skills_dir)


def resolve_global_agent_paths(
    spec: AgentSpec,
    *,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[Path, Path, str]:
    """Resolve (root_dir, skills_dir, rel_path) for a built-in agent."""
    resolved_home = Path(home) if home is not None else Path.home()
    active_env = os.environ if env is None else env

    root_dir: Path | None = None
    if spec.env_var:
        root_dir = _expand_abs_env(active_env.get(spec.env_var), resolved_home)

    if root_dir is None and spec.xdg_subpath:
        xdg_base = _expand_abs_env(active_env.get("XDG_CONFIG_HOME"), resolved_home)
        if xdg_base is not None:
            root_dir = xdg_base / spec.xdg_subpath

    if root_dir is None:
        default_root = resolved_home / Path(*spec.global_root.split("/"))
        # Kimi Code 2.x uses ~/.kimi-code; fall back to legacy ~/.kimi when
        # ~/.kimi-code does not exist and ~/.kimi holds real files.
        if spec.id == "kimi" and not default_root.exists():
            legacy_kimi = resolved_home / ".kimi"
            if legacy_kimi.is_dir():
                default_root = legacy_kimi
        root_dir = default_root

    skills_dir = root_dir / spec.skills_subdir
    rel_path = _rel_display(skills_dir, resolved_home, spec.default_rel_path)
    return root_dir, skills_dir, rel_path


def detect_home_agents(
    *,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
    include_undetected: bool = False,
    include_legacy: bool = False,
) -> list[dict]:
    """Detect installed built-in agents under the user's home directory."""
    resolved_home = Path(home) if home is not None else Path.home()
    active_env = os.environ if env is None else env

    if which is not None:
        find_bin = which
    elif env is not None:
        path_val = active_env.get("PATH", "")

        def find_bin(name: str) -> str | None:
            return shutil.which(name, path=path_val) if path_val else None
    else:
        find_bin = shutil.which

    detected_items: list[dict] = []
    undetected_items: list[dict] = []
    seen_paths: set[str] = set()

    for spec in BUILTIN_AGENTS:
        root_dir, skills_dir, rel_path = resolve_global_agent_paths(
            spec, home=resolved_home, env=active_env
        )
        canonical_skills = str(skills_dir.absolute())
        if canonical_skills in seen_paths:
            continue

        taken = _is_taken_by_non_dir(skills_dir, resolved_home)
        detected_by: str | None = None
        detected_binary: str | None = None

        if not taken:
            detected_by = _dir_has_agent_evidence(
                root_dir,
                skills_dir,
                skills_subdir=spec.skills_subdir,
                shared_skills=spec.shared_skills,
            )
            if detected_by is None and spec.bins:
                for binary in spec.bins:
                    if find_bin(binary):
                        detected_by = "binary"
                        detected_binary = binary
                        break

        detected = detected_by is not None
        if not detected and (not include_undetected or (spec.legacy and not include_legacy)):
            continue

        seen_paths.add(canonical_skills)
        entry = {
            "id": spec.id,
            "agent": spec.id,
            "name": spec.name,
            "icon": spec.icon,
            "aliases": list(spec.aliases),
            "rel_path": rel_path,
            "root_path": str(root_dir.absolute()),
            "path": canonical_skills,
            "detected": detected,
            "detectedBy": detected_by,
            "detectedBinary": detected_binary,
            "exists": skills_dir.is_dir(),
            "shared": spec.shared_skills,
            "readsShared": spec.reads_shared,
            "legacy": spec.legacy,
            "envVar": spec.env_var,
            "projectRelPath": spec.project_rel,
            "targetId": make_builtin_target_id(canonical_skills),
        }
        if detected:
            detected_items.append(entry)
        else:
            undetected_items.append(entry)

    return detected_items + undetected_items


def discover_project_agent_dirs(root_path: str | Path) -> list[dict]:
    """Scan a project directory for known coding agent skill directories."""
    root = Path(root_path).expanduser().resolve()
    if not root.is_dir():
        return []

    found: list[dict] = []
    seen_paths: set[str] = set()
    for spec in BUILTIN_AGENTS:
        if not spec.project_rel or not spec.project_root:
            continue
        agent_root = root / Path(*spec.project_root.split("/"))
        skills_dir = root / Path(*spec.project_rel.split("/"))
        canonical = str(skills_dir)
        if canonical in seen_paths:
            continue
        if _is_taken_by_non_dir(skills_dir, root):
            continue
        detected_by = _dir_has_agent_evidence(
            agent_root,
            skills_dir,
            skills_subdir=spec.skills_subdir,
            shared_skills=spec.shared_skills,
        )
        if detected_by is None:
            continue
        seen_paths.add(canonical)
        found.append({
            "agent": spec.id,
            "id": spec.id,
            "name": spec.name,
            "icon": spec.icon,
            "rel_path": spec.project_rel,
            "path": canonical,
            "exists": skills_dir.is_dir(),
            "shared": spec.shared_skills,
        })
    return found


def match_agent_for_path(
    path: str | Path,
    *,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> AgentSpec | None:
    """Identify the built-in AgentSpec corresponding to a local target path."""
    resolved_home = Path(home) if home is not None else Path.home()
    active_env = os.environ if env is None else env
    candidate = Path(path).expanduser()
    canonical = str(candidate.absolute())

    # 1. Exact global path match (including env overrides & nested dirs like .config/opencode/skills)
    for spec in BUILTIN_AGENTS:
        _, skills_dir, _ = resolve_global_agent_paths(
            spec, home=resolved_home, env=active_env
        )
        if str(skills_dir.absolute()) == canonical:
            return spec

    # 2. Project-relative suffix match (e.g. /proj/.claude/skills, /proj/.cursor/skills)
    parts = candidate.parts
    for spec in BUILTIN_AGENTS:
        if not spec.project_rel:
            continue
        suffix = tuple(spec.project_rel.split("/"))
        if len(parts) >= len(suffix) and parts[-len(suffix):] == suffix:
            return spec

    return None


def _build_remote_suffix_table() -> list[tuple[tuple[str, ...], AgentSpec]]:
    entries: list[tuple[tuple[str, ...], AgentSpec]] = []
    for spec in BUILTIN_AGENTS:
        global_suffix = tuple(spec.default_rel_path.split("/"))
        entries.append((global_suffix, spec))
        if spec.id == "kimi":
            entries.append(((".kimi", spec.skills_subdir), spec))
        if spec.project_rel:
            project_suffix = tuple(spec.project_rel.split("/"))
            if project_suffix != global_suffix:
                entries.append((project_suffix, spec))
    # Match longer suffixes (e.g. .gemini/config/skills) before shorter ones (.gemini/skills).
    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return entries


_REMOTE_SUFFIX_TABLE: list[tuple[tuple[str, ...], AgentSpec]] = _build_remote_suffix_table()


def match_agent_for_remote_path(path: str | None) -> AgentSpec | None:
    """Identify a built-in AgentSpec from a remote/POSIX path by known suffixes."""
    if not path:
        return None
    normalized = str(path).replace("\\", "/").strip()
    if not normalized:
        return None
    parts = tuple(p for p in PurePosixPath(normalized).parts if p not in ("", "/", "~"))
    if not parts:
        return None
    for suffix, spec in _REMOTE_SUFFIX_TABLE:
        if len(parts) >= len(suffix) and parts[-len(suffix):] == suffix:
            return spec
    return None


def icon_for_agent(identifier: str | None) -> str:
    """Return the stable icon key for a built-in agent ID/alias, or default custom icon."""
    if not identifier:
        return DEFAULT_CUSTOM_ICON
    spec = get_agent_spec(identifier)
    return spec.icon if spec is not None else DEFAULT_CUSTOM_ICON


def icon_for_path(
    path: str | Path | None,
    *,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
    remote: bool = False,
) -> str:
    """Return the stable icon key inferred from a local or remote target path."""
    if not path:
        return DEFAULT_CUSTOM_ICON
    matched = (
        match_agent_for_remote_path(str(path))
        if remote
        else match_agent_for_path(path, home=home, env=env)
    )
    return matched.icon if matched is not None else DEFAULT_CUSTOM_ICON

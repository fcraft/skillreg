# self-skill (placeholder submodule)

skillreg's self-describing skill — a `SKILL.md` that registers skillreg itself
into the registry (bootstrap, PRD §2.4). The built artifact ships inside the
Python package (`skillreg/builtin/skillreg/SKILL.md`, read via
`importlib.resources`) and is injected into the workspace's
`.skillreg/builtin/skillreg/` reserved area at startup.

> **Status:** placeholder. The real `self-skill` submodule is wired up in a
> later issue. This directory exists only to reserve the monorepo layout — no
> `git submodule add` has been run yet.

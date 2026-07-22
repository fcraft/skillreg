# skillreg

Local AI agent skill manager distributed through npm

## Install

```bash
npm install --global skillreg
skillreg workspace create ~/my-skills
skillreg dashboard open
```

The npm launcher runs the matching Python `skillreg` package in an isolated
environment. It uses `uv` when available. Otherwise, it creates a private
virtual environment with Python 3.9 or newer on first use

The first invocation needs network access to download the Python package and
its dependencies from PyPI

Optional environment variables:

- `SKILLREG_UV`: path to the `uv` executable
- `SKILLREG_PYTHON`: path to a Python 3.9+ executable
- `SKILLREG_NPM_CACHE_DIR`: directory for the npm launcher's Python environment

Project documentation: <https://github.com/fcraft/skillreg>

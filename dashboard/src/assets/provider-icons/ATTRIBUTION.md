# Provider Icon Attribution & Licenses

All provider SVG icons in this directory are bundled locally for 100% offline
rendering in the `skillreg` Dashboard without any external CDN requests.

Legacy aliases `tclaude` and `tcodex` reuse `claude.svg` and `codex.svg` respectively.

## Upstream Repositories

- **[lobehub/lobe-icons](https://github.com/lobehub/lobe-icons/tree/9752d967494e48d8f83f2808feb2b0207bf70997)** — [MIT License](licenses/lobe-icons-MIT.txt)
- **[yetone/magpie](https://github.com/yetone/magpie/tree/0e95af7487e3cca6118c88ac86d582ab981727d3)** — [MIT License](licenses/magpie-MIT.txt)
- **[lucide-icons/lucide](https://github.com/lucide-icons/lucide/tree/c1a02a04d4f3f7049d44567d62b8b06cff0b9103)** — [ISC and inherited Feather MIT licenses](licenses/lucide-LICENSE.txt)
- **[can1357/oh-my-pi](https://github.com/can1357/oh-my-pi/tree/17e663b73667941db39271d90528a05c9c1e5f4b)** — [MIT License](licenses/oh-my-pi-MIT.txt), original source of the `omp` mark redistributed by magpie

The linked revisions pin the sources used below. Copyright notices and full
license terms are retained in `licenses/`. Lucide's `terminal` shape includes
the Feather-derived MIT terms in addition to ISC.

Local SVGs normalize fills to `currentColor` for theme contrast. CodeBuddy and
WorkBuddy retain their distinct gradients; WorkBuddy's blur filter is replaced
by a vector gradient. The Droid viewBox is cropped to its artwork. `iconData.js`
embeds these local files, with byte-for-byte parity checked by the unit tests.
The build retains this document and every license under `assets/provider-icons/`
in the Dashboard distribution, including the Python wheel's bundled Dashboard.

## Per-Icon Mapping

| Icon ID | Local File | Source Repository | Upstream Path | License | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `agents` | `agents.svg` | `lucide-icons/lucide` (`c1a02a04d4`) | `icons/layers.svg` | **ISC** | Lucide Contributors (generic shared-skills icon) |
| `claude` | `claude.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/claudecode.svg` | **MIT** | LobeHub; Claude trademark belongs to Anthropic |
| `codex` | `codex.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/codex.svg` | **MIT** | LobeHub; Codex trademark belongs to OpenAI |
| `cursor` | `cursor.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/cursor.svg` | **MIT** | LobeHub; Cursor trademark belongs to Anysphere |
| `gemini` | `gemini.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/geminicli.svg` | **MIT** | LobeHub; Gemini trademark belongs to Google |
| `antigravity` | `antigravity.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/antigravity.svg` | **MIT** | LobeHub; Antigravity trademark belongs to Google |
| `copilot` | `copilot.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/githubcopilot.svg` | **MIT** | LobeHub; GitHub Copilot trademark belongs to GitHub |
| `opencode` | `opencode.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/opencode.svg` | **MIT** | LobeHub; OpenCode mark belongs to Anomaly / SST |
| `codebuddy` | `codebuddy.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/codebuddy-color.svg` | **MIT** | LobeHub; CodeBuddy trademark belongs to Tencent |
| `workbuddy` | `workbuddy.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/workbuddy-color.svg` | **MIT** | LobeHub; WorkBuddy trademark belongs to Tencent (filter-free vector simplification) |
| `pi` | `pi.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/pi.svg` | **MIT** | LobeHub; Pi coding agent (pi.dev) |
| `cline` | `cline.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/cline.svg` | **MIT** | LobeHub; Cline Bot Inc. |
| `droid` | `droid.svg` | `yetone/magpie` (`0e95af7487`) | `internal/gui/assets/icons/factory.svg` | **MIT** | yetone/magpie; Factory / Droid trademark belongs to Factory |
| `kimi` | `kimi.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/kimi.svg` | **MIT** | LobeHub; Kimi trademark belongs to Moonshot AI |
| `qwen` | `qwen.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/qwen.svg` | **MIT** | LobeHub; Qwen trademark belongs to Alibaba Cloud |
| `qoder` | `qoder.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/qoder.svg` | **MIT** | LobeHub; Qoder trademark belongs to Alibaba |
| `kiro` | `kiro.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/kiro.svg` | **MIT** | LobeHub; Kiro trademark belongs to Amazon Web Services |
| `crush` | `crush.svg` | `lucide-icons/lucide` (`c1a02a04d4`) | `icons/sparkles.svg` | **ISC** | Lucide Contributors (semantic icon avoiding non-OSI FSL asset) |
| `vibe` | `vibe.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/mistral.svg` | **MIT** | LobeHub; Mistral trademark belongs to Mistral AI |
| `hermes` | `hermes.svg` | `yetone/magpie` (`0e95af7487`) | `internal/gui/assets/icons/hermes.svg` | **MIT** | yetone/magpie; Hermes Agent geometric mark |
| `dsh` | `dsh.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/deepseek.svg` | **MIT** | LobeHub; DeepSeek trademark belongs to DeepSeek |
| `commandcode` | `commandcode.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/commandcode.svg` | **MIT** | LobeHub; Command Code |
| `devin` | `devin.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/devin.svg` | **MIT** | LobeHub; Devin trademark belongs to Cognition |
| `grok` | `grok.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/grok.svg` | **MIT** | LobeHub; Grok trademark belongs to xAI |
| `zcode` | `zcode.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/zai.svg` | **MIT** | LobeHub; Z.ai / Zhipu AI |
| `alma` | `alma.svg` | `lucide-icons/lucide` (`c1a02a04d4`) | `icons/bot.svg` | **ISC** | Lucide Contributors (semantic icon for provider without open-source SVG) |
| `omp` | `omp.svg` | `yetone/magpie` (`0e95af7487`) | `internal/gui/assets/icons/omp.svg` | **MIT** | yetone/magpie (derived from can1357/oh-my-pi, MIT) |
| `minimax-code` | `minimax-code.svg` | `lobehub/lobe-icons` (`9752d96749`) | `packages/static-svg/icons/minimax.svg` | **MIT** | LobeHub; MiniMax trademark belongs to MiniMax |
| `agent` | `agent.svg` | `lucide-icons/lucide` (`c1a02a04d4`) | `icons/terminal.svg` | **ISC + MIT** | Lucide Contributors / Cole Bemis (legacy generic .agent icon) |
| `custom` | `custom.svg` | `lucide-icons/lucide` (`c1a02a04d4`) | `icons/folder.svg` | **ISC** | Lucide Contributors (default fallback icon for custom/unknown targets) |

## Trademark Notice

All product names, logos, and brand marks remain the property of their respective
owners and are used solely to identify local coding agent directories configured
by the user.

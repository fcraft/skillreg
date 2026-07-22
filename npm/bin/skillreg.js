#!/usr/bin/env node

import { runSkillreg } from "../lib/launcher.js"

process.exitCode = runSkillreg(process.argv.slice(2))

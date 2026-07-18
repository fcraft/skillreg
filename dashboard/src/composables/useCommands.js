import { reactive } from 'vue'
import { searchCommands as rankCommands } from '../search/searchCommands.js'

const commands = reactive([])

export function useCommands() {
  function registerCommand(cmd) {
    const existing = commands.findIndex(c => c.id === cmd.id)
    if (existing >= 0) {
      commands[existing] = cmd
    } else {
      commands.push(cmd)
    }
  }

  function replaceCommandsBySection(section, replacements) {
    const retained = commands.filter(command => command.section !== section)
    const normalized = replacements.map(command => ({ ...command, section }))
    commands.splice(0, commands.length, ...retained, ...normalized)
  }

  function getCommands() {
    return commands
  }

  function searchCommands(query) {
    return rankCommands(commands, query)
  }

  return { registerCommand, replaceCommandsBySection, getCommands, searchCommands }
}

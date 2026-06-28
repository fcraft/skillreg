import { reactive } from 'vue'

const commands = reactive([])

export function useCommands() {
  function registerCommand(cmd) {
    // cmd: { id, title, description?, icon?, section: 'navigation'|'action'|'skill', shortcut?, action: () => void }
    const existing = commands.findIndex(c => c.id === cmd.id)
    if (existing >= 0) {
      commands[existing] = cmd
    } else {
      commands.push(cmd)
    }
  }

  function unregisterCommandsBySection(section) {
    for (let i = commands.length - 1; i >= 0; i--) {
      if (commands[i].section === section) {
        commands.splice(i, 1)
      }
    }
  }

  function getCommands() {
    return commands
  }

  function searchCommands(query) {
    if (!query || !query.trim()) return commands
    const q = query.toLowerCase()
    return commands.filter(c =>
      c.title.toLowerCase().includes(q) ||
      (c.description && c.description.toLowerCase().includes(q))
    )
  }

  return { registerCommand, unregisterCommandsBySection, getCommands, searchCommands }
}

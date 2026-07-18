const COLLATOR = new Intl.Collator('zh-CN', {
  numeric: true,
  sensitivity: 'base',
})

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .toLocaleLowerCase()
    .replace(/[-_/\\.:]+/gu, ' ')
    .replace(/\s+/gu, ' ')
    .trim()
}

function normalizeKeywords(keywords) {
  const values = Array.isArray(keywords) ? keywords : [keywords]
  return values.map(normalizeText).filter(Boolean)
}

function phraseScore(title, titleWords, description, keywords, query) {
  if (title === query) return 10_000
  if (title.startsWith(query)) return 9_000
  if (titleWords.includes(query)) return 8_500
  if (titleWords.some(word => word.startsWith(query))) return 8_000
  if (title.includes(query)) return 7_000
  if (keywords.some(keyword => keyword === query)) return 6_000
  if (keywords.some(keyword => keyword.startsWith(query))) return 5_500
  if (keywords.some(keyword => keyword.includes(query))) return 5_000
  if (description.includes(query)) return 3_500
  return 0
}

function tokenScore(title, titleWords, description, keywords, token) {
  if (title === token || titleWords.includes(token)) return 800
  if (title.startsWith(token) || titleWords.some(word => word.startsWith(token))) return 700
  if (title.includes(token)) return 600
  if (keywords.some(keyword => keyword === token)) return 450
  if (keywords.some(keyword => keyword.startsWith(token))) return 400
  if (keywords.some(keyword => keyword.includes(token))) return 350
  if (description.includes(token)) return 200
  return null
}

function scoreCommand(command, normalizedQuery, queryTokens, originalIndex) {
  const title = normalizeText(command.title)
  const description = normalizeText(command.description)
  const keywords = normalizeKeywords(command.keywords)
  const titleWords = title.split(' ').filter(Boolean)
  let score = phraseScore(title, titleWords, description, keywords, normalizedQuery)

  for (const token of queryTokens) {
    const tokenMatchScore = tokenScore(title, titleWords, description, keywords, token)
    if (tokenMatchScore === null) return null
    score += tokenMatchScore
  }

  return {
    command,
    originalIndex,
    score,
    titleIndex: title.indexOf(queryTokens[0]),
    titleLength: title.length,
  }
}

export function searchCommands(commands, query) {
  const normalizedQuery = normalizeText(query)
  if (!normalizedQuery) return [...commands]

  const queryTokens = normalizedQuery.split(' ').filter(Boolean)
  return commands
    .map((command, index) => scoreCommand(command, normalizedQuery, queryTokens, index))
    .filter(Boolean)
    .sort((left, right) => (
      right.score - left.score
      || (left.titleIndex < 0 ? Number.MAX_SAFE_INTEGER : left.titleIndex)
        - (right.titleIndex < 0 ? Number.MAX_SAFE_INTEGER : right.titleIndex)
      || left.titleLength - right.titleLength
      || COLLATOR.compare(left.command.title, right.command.title)
      || left.originalIndex - right.originalIndex
    ))
    .map(result => result.command)
}

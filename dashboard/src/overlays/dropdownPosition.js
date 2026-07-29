export function positionDropdown(
  triggerRect,
  {
    viewportWidth,
    viewportHeight,
    menuWidth,
    menuHeight,
    gap = 4,
    padding = 8,
  },
) {
  const left = Math.min(
    Math.max(padding, triggerRect.right - menuWidth),
    viewportWidth - menuWidth - padding,
  )
  const spaceBelow = viewportHeight - triggerRect.bottom - padding
  const top = spaceBelow >= menuHeight + gap
    ? triggerRect.bottom + gap
    : Math.max(padding, triggerRect.top - menuHeight - gap)

  return { left, top }
}

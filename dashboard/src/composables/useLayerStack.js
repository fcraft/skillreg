/**
 * Layer Stack — dynamic z-index management for overlapping overlays.
 *
 * Provides sequential z-index increments so each large overlay (modal, drawer,
 * panel) reliably stacks above previously opened ones.
 *
 * Usage:
 *   const { acquire, release } = useLayerStack()
 *   const zIndex = acquire()   // returns 1020, then 1030, then 1040...
 *   // ... mount overlay with this zIndex ...
 *   // on unmount:
 *   release()
 */

const OVERLAY_BASE = 1010 // matches --z-overlay-panel
let overlaySeq = 0

export function useLayerStack() {
  function acquire() {
    return OVERLAY_BASE + (++overlaySeq * 10)
  }

  function release() {
    if (overlaySeq > 0) {
      overlaySeq--
    }
  }

  return { acquire, release }
}

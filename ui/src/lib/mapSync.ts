import type L from 'leaflet'

export interface MapSync {
  register(map: L.Map): () => void
}

/** Keeps several maps on the same view: pan or zoom one and the others follow. */
export function createMapSync(): MapSync {
  const maps = new Set<L.Map>()
  let syncing = false
  return {
    register(map) {
      maps.add(map)
      const follow = () => {
        if (syncing) return
        syncing = true
        try {
          for (const other of maps) {
            if (other !== map) other.setView(map.getCenter(), map.getZoom(), { animate: false })
          }
        } finally {
          syncing = false
        }
      }
      map.on('move zoomend', follow)
      return () => {
        map.off('move zoomend', follow)
        maps.delete(map)
      }
    },
  }
}

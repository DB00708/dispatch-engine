import L from 'leaflet'
import { useEffect, useMemo } from 'react'
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import type { Scenario, Ticket } from '../api/models'
import { capitalize, clock } from '../lib/format'
import type { MapLayers } from '../lib/mapLayers'
import type { MapSync } from '../lib/mapSync'

const BENGALURU: L.LatLngTuple = [12.97, 77.6]

const iconCache = new Map<string, L.DivIcon>()

function ticketIcon(ticket: Ticket, flags: string[]): L.DivIcon {
  const classes = ['ticket-marker', ticket.priority.toLowerCase(), ...flags].join(' ')
  const key = `${ticket.id}|${classes}`
  let icon = iconCache.get(key)
  if (!icon) {
    icon = L.divIcon({
      className: 'ticket-icon',
      html: `<span class="${classes}" data-ticket-id="${ticket.id}" data-priority="${ticket.priority}"></span>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    })
    iconCache.set(key, icon)
  }
  return icon
}

function SyncRegistrar({ sync }: { sync: MapSync }) {
  const map = useMap()
  useEffect(() => sync.register(map), [map, sync])
  return null
}

function ClickCatcher({ onClick }: { onClick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (event) => onClick(event.latlng.lat, event.latlng.lng) })
  return null
}

/**
 * Fit the view to the points whenever their bounding box changes. A map laid out while
 * hidden (background tab, collapsed pane) has no size yet, and fitting then would jump
 * to max zoom, so in that case the fit waits until the container gets a size.
 */
function FitToPoints({ boundsKey }: { boundsKey: string }) {
  const map = useMap()
  useEffect(() => {
    if (!boundsKey) return
    const [south, west, north, east] = boundsKey.split(',').map(Number)
    const container = map.getContainer()
    const hasSize = () => container.clientWidth > 0 && container.clientHeight > 0
    const fit = () => {
      map.invalidateSize({ pan: false })
      map.fitBounds(
        [
          [south, west],
          [north, east],
        ],
        { padding: [28, 28], maxZoom: 14, animate: false },
      )
    }
    if (hasSize()) {
      fit()
      return
    }
    const observer = new ResizeObserver(() => {
      if (!hasSize()) return
      observer.disconnect()
      fit()
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [map, boundsKey])
  return null
}

export interface MapViewProps {
  scenario: Scenario
  layers: MapLayers
  /** Used for data-testid and aria-label, e.g. "left". */
  name: string
  selectedTicketId?: string | null
  /** When set, tickets outside it are dimmed. */
  focusTicketIds?: Set<string>
  engineerNotes?: Record<string, string>
  onTicketClick?: (ticketId: string) => void
  onMapClick?: (lat: number, lng: number) => void
  sync?: MapSync
  height?: number
  crosshair?: boolean
}

export function MapView({
  scenario,
  layers,
  name,
  selectedTicketId,
  focusTicketIds,
  engineerNotes,
  onTicketClick,
  onMapClick,
  sync,
  height = 340,
  crosshair = false,
}: MapViewProps) {
  const engineers = useMemo(() => new Map(scenario.engineers.map((e) => [e.id, e])), [scenario])
  const tickets = useMemo(() => new Map(scenario.tickets.map((t) => [t.id, t])), [scenario])

  const boundsKey = useMemo(() => {
    const points = [...scenario.engineers, ...scenario.tickets].map((p) => p.location)
    if (points.length === 0) return ''
    const lats = points.map((p) => p.lat)
    const lngs = points.map((p) => p.lng)
    return [Math.min(...lats), Math.min(...lngs), Math.max(...lats), Math.max(...lngs)]
      .map((n) => n.toFixed(4))
      .join(',')
  }, [scenario])

  return (
    <div
      className={`map-frame${crosshair ? ' crosshair' : ''}`}
      style={{ height }}
      data-testid={`map-${name}`}
      aria-label={`Map: ${name}`}
    >
      <MapContainer center={BENGALURU} zoom={11} scrollWheelZoom style={{ height: '100%' }}>
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
        />
        <FitToPoints boundsKey={boundsKey} />
        {sync && <SyncRegistrar sync={sync} />}
        {onMapClick && <ClickCatcher onClick={onMapClick} />}

        {layers.lines.map((line) => {
          const engineer = engineers.get(line.engineerId)
          const ticket = tickets.get(line.ticketId)
          if (!engineer || !ticket) return null
          return (
            <Polyline
              key={`${line.ticketId}-${line.engineerId}-${line.kind}`}
              positions={[
                [engineer.location.lat, engineer.location.lng],
                [ticket.location.lat, ticket.location.lng],
              ]}
              // className is read only when Leaflet creates the layer, so it is a direct
              // prop (react-leaflet applies pathOptions later through setStyle).
              className={`map-line ${line.kind}`}
              bubblingMouseEvents={false}
              pathOptions={{ weight: line.kind === 'tight' ? 5 : line.kind === 'ghost' ? 2 : 3 }}
              eventHandlers={{ click: () => onTicketClick?.(line.ticketId) }}
            >
              {line.tooltip && <Tooltip sticky>{line.tooltip}</Tooltip>}
            </Polyline>
          )
        })}

        {scenario.engineers.map((engineer) => {
          const state = layers.engineerState[engineer.id] ?? 'neutral'
          const note = engineerNotes?.[engineer.id]
          return (
            <CircleMarker
              key={`${engineer.id}-${state}`}
              center={[engineer.location.lat, engineer.location.lng]}
              radius={7}
              className={`engineer-marker ${state}`}
              bubblingMouseEvents={false}
              pathOptions={{ weight: 2 }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <strong>
                  {engineer.id} {engineer.name}
                </strong>
                <br />
                {engineer.skills.map(capitalize).join(', ')} · shift {clock(engineer.shift_start)}–
                {clock(engineer.shift_end)}
                {note && (
                  <>
                    <br />
                    {note}
                  </>
                )}
              </Tooltip>
            </CircleMarker>
          )
        })}

        {scenario.tickets.map((ticket) => {
          const flags: string[] = []
          if (layers.unassigned.has(ticket.id)) flags.push('unassigned')
          if (ticket.id === selectedTicketId) flags.push('selected')
          if (focusTicketIds && !focusTicketIds.has(ticket.id)) flags.push('dimmed')
          return (
            <Marker
              key={ticket.id}
              position={[ticket.location.lat, ticket.location.lng]}
              icon={ticketIcon(ticket, flags)}
              keyboard={false}
              eventHandlers={{ click: () => onTicketClick?.(ticket.id) }}
            >
              <Tooltip direction="top" offset={[0, -8]}>
                <strong>
                  {ticket.id} · {ticket.priority}
                </strong>{' '}
                {ticket.fault_type} · due {clock(ticket.deadline)}
                {layers.unassigned.has(ticket.id) && (
                  <>
                    <br />
                    Unassigned
                  </>
                )}
              </Tooltip>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}

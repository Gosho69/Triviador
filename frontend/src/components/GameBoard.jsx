import { useSyncExternalStore } from 'react'
import { seatColour } from '../knights'
import { Castle } from './RealmMap'

// The project map has three rows of territories, sent in map order. Wide screens show the rows
// left to right; narrow screens turn the map on its side so names stay readable.
const ROWS = 3
const STEP = 180
const PAD = 92
const RADIUS = 38
const NARROW = '(max-width: 640px)'

let narrowQuery
const narrowQueryList = () => (narrowQuery ??= window.matchMedia(NARROW))

function subscribe(onChange) {
  const query = narrowQueryList()
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

function useNarrow() {
  return useSyncExternalStore(subscribe, () => narrowQueryList().matches)
}

function layout(territories, narrow) {
  const columns = Math.ceil(territories.length / ROWS)
  const points = new Map(
    territories.map((territory, index) => {
      const [row, column] = [Math.floor(index / columns), index % columns]
      const [x, y] = narrow ? [row, column] : [column, row]
      return [territory.slug, { x: PAD + x * STEP, y: PAD + y * STEP }]
    }),
  )
  const [across, down] = narrow ? [ROWS, columns] : [columns, ROWS]
  return { points, width: PAD * 2 + (across - 1) * STEP, height: PAD * 2 + (down - 1) * STEP }
}

function describe(territories, players) {
  const names = new Map(players.map((player) => [player.seat, player.nickname]))
  const capitals = territories
    .filter((territory) => territory.capital)
    .map((territory) => `${names.get(territory.owner_seat)} at ${territory.name}`)
  return `Map of ${territories.length} territories. Capitals: ${capitals.join(', ')}.`
}

export function GameBoard({ territories, players }) {
  const narrow = useNarrow()
  const { points, width, height } = layout(territories, narrow)
  const roads = territories.flatMap((territory) =>
    territory.neighbors
      .filter((neighbor) => territory.slug < neighbor && points.has(neighbor))
      .map((neighbor) => [points.get(territory.slug), points.get(neighbor)]),
  )

  return (
    <svg className="board" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={describe(territories, players)}>
      <g className="board__roads">
        {roads.map(([from, to]) => (
          <line key={`${from.x},${from.y}-${to.x},${to.y}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
        ))}
      </g>
      {territories.map((territory) => (
        <Territory key={territory.slug} territory={territory} point={points.get(territory.slug)} />
      ))}
    </svg>
  )
}

function Territory({ territory, point }) {
  const colour = territory.owner_seat ? seatColour(territory.owner_seat) : undefined
  const { capital } = territory

  return (
    <g
      className={`territory${capital ? ' territory--capital' : ''}`}
      data-colour={colour}
      data-seat={territory.owner_seat ?? undefined}
      transform={`translate(${point.x} ${point.y})`}
    >
      <circle r={RADIUS} className="territory__seal" />
      {capital && (
        <g className="territory__castle">
          <g transform="translate(0 12) scale(0.46)">
            <Castle x={0} y={0} colour={colour} />
          </g>
        </g>
      )}
      <text y={RADIUS + 24} className="territory__name">
        {territory.name}
      </text>
      {capital && (
        <g className="territory__health" transform={`translate(0 ${RADIUS + 44})`}>
          {Array.from({ length: capital.max_health }, (_, index) => (
            <circle key={index} cx={(index - (capital.max_health - 1) / 2) * 16} r="5.5" data-lost={index >= capital.health || undefined} />
          ))}
        </g>
      )}
    </g>
  )
}

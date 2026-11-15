import { level } from './steps.ts'
import type { ClassMap, GapMap, Picked } from './types.ts'

function short(label: string): string {
  return label.replace(' to ', '–').replace(/(%| kPa) and above/, '+').replace(/%| kPa/, '')
}

type Props = {
  map: GapMap
  fuel: ClassMap
  /** Suggestion number of each suggested empty cell of this fuel class, keyed "column,row". */
  ranks: Map<string, number>
  picked: Picked | null
  /** The cell a suggestion card is pointing at. */
  lit: Picked | null
  onHover: (text: string | null) => void
  onPick: (cell: Picked) => void
}

export function GapGrid({ map, fuel, ranks, picked, lit, onHover, onPick }: Props) {
  const cells = new Map(fuel.cells.map((cell) => [`${cell.column},${cell.row}`, cell]))
  const notStated = map.pressure_bins.length - 1
  const home = map.habitat_cell
  // Highest pressure at the top; the "not stated" row sits apart at the bottom.
  const rows = [...map.pressure_bins.keys()].filter((row) => row !== notStated).reverse()
  const same = (cell: Picked | null, column: number, row: number) =>
    cell !== null && cell.fuel_class === fuel.fuel_class && cell.column === column && cell.row === row

  const cell = (column: number, row: number) => {
    const found = cells.get(`${column},${row}`)
    const rank = ranks.get(`${column},${row}`)
    const isHome = column === home.column && row === home.row
    const inBounds = map.habitat.open_ended && row !== notStated && column >= home.column && row <= home.row
    const where = `${fuel.fuel_class}, ${map.oxygen_bins[column]} oxygen, pressure ${map.pressure_bins[row]}`
    const what = found
      ? `${found.rows} rows (${Object.entries(found.from).map(([name, count]) => `${name} ${count}`).join(', ')})`
      : 'no tests'
    const text = `${where}: ${what}${isHome ? `. This is the ${map.habitat.label} cell` : ''}${rank ? `. Suggestion ${rank} below` : ''}. Click to keep it open.`
    const classes = [
      'gap-cell',
      `level-${found ? level(found.rows) : 0}`,
      isHome && 'home',
      inBounds && 'in-bounds',
      rank && 'suggested',
      same(picked, column, row) && 'picked',
      same(lit, column, row) && 'lit',
    ]
    return (
      <button
        key={column}
        type="button"
        role="cell"
        title={text}
        aria-pressed={same(picked, column, row)}
        className={classes.filter(Boolean).join(' ')}
        onClick={() => onPick({ fuel_class: fuel.fuel_class, column, row })}
        onPointerEnter={() => onHover(text)}
        onPointerLeave={() => onHover(null)}
        onFocus={() => onHover(text)}
        onBlur={() => onHover(null)}
      >
        {found?.rows ?? (rank ? <span className="rank">{rank}</span> : null)}
      </button>
    )
  }

  const columns = [...map.oxygen_bins.keys()]
  return (
    <div className="gap-grid" role="table" aria-label={`Tests by oxygen and pressure, ${fuel.fuel_class}`}>
      {rows.map((row) => (
        <div key={row} role="row" className="gap-row">
          <span className="gap-label">{short(map.pressure_bins[row])}</span>
          {columns.map((column) => cell(column, row))}
        </div>
      ))}
      <div role="row" className="gap-row apart">
        <span className="gap-label">not stated</span>
        {columns.map((column) => cell(column, notStated))}
      </div>
      <div className="gap-row" aria-hidden="true">
        <span className="gap-label" />
        {columns.map((column) => (
          <span key={column} className="gap-axis">
            {short(map.oxygen_bins[column])}
          </span>
        ))}
      </div>
    </div>
  )
}

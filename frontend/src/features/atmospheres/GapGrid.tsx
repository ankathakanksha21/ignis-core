import { level } from './steps.ts'
import type { ClassMap, GapMap } from './types.ts'

function short(label: string): string {
  return label.replace(' to ', '–').replace(/(%| kPa) and above/, '+').replace(/%| kPa/, '')
}

export function GapGrid({ map, fuel, onHover }: { map: GapMap; fuel: ClassMap; onHover: (text: string | null) => void }) {
  const cells = new Map(fuel.cells.map((cell) => [`${cell.column},${cell.row}`, cell]))
  const notStated = map.pressure_bins.length - 1
  const home = map.habitat_cell
  // Highest pressure at the top; the "not stated" row sits apart at the bottom.
  const rows = [...map.pressure_bins.keys()].filter((row) => row !== notStated).reverse()

  const cell = (column: number, row: number) => {
    const found = cells.get(`${column},${row}`)
    const isHome = column === home.column && row === home.row
    const inBounds = map.habitat.open_ended && row !== notStated && column >= home.column && row <= home.row
    const where = `${fuel.fuel_class}, ${map.oxygen_bins[column]} oxygen, pressure ${map.pressure_bins[row]}`
    const what = found
      ? `${found.rows} rows (${Object.entries(found.from).map(([name, count]) => `${name} ${count}`).join(', ')})`
      : 'no tests'
    const text = `${where}: ${what}${isHome ? `. This is the ${map.habitat.label} cell` : ''}.`
    return (
      <div
        key={column}
        role="cell"
        tabIndex={0}
        title={text}
        className={`gap-cell level-${found ? level(found.rows) : 0}${isHome ? ' home' : ''}${inBounds ? ' in-bounds' : ''}`}
        onPointerEnter={() => onHover(text)}
        onPointerLeave={() => onHover(null)}
        onFocus={() => onHover(text)}
        onBlur={() => onHover(null)}
      >
        {found?.rows}
      </div>
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

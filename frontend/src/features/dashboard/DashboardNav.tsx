import { NavLink } from 'react-router-dom'

export function DashboardNav() {
  return (
    <nav className="subnav">
      <NavLink to="/dashboard" end>
        Browse
      </NavLink>
      <NavLink to="/dashboard/rank">Rank</NavLink>
      <NavLink to="/dashboard/compare">Compare</NavLink>
      <NavLink to="/dashboard/similar">Similar</NavLink>
      <NavLink to="/dashboard/earth">On Earth</NavLink>
    </nav>
  )
}

import { NavLink } from 'react-router-dom'

export function DashboardNav() {
  return (
    <nav className="subnav">
      <NavLink to="/dashboard" end>
        By pillar
      </NavLink>
      <NavLink to="/dashboard/rank">Rank for a mission</NavLink>
      <NavLink to="/dashboard/compare">Compare</NavLink>
      <NavLink to="/dashboard/similar">Similar tests</NavLink>
      <NavLink to="/dashboard/earth">On Earth</NavLink>
    </nav>
  )
}

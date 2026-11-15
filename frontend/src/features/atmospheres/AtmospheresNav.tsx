import { NavLink } from 'react-router-dom'

export function AtmospheresNav() {
  return (
    <nav className="subnav">
      <NavLink to="/atmospheres" end>
        Gap map
      </NavLink>
      <NavLink to="/atmospheres/quality">Data quality</NavLink>
    </nav>
  )
}

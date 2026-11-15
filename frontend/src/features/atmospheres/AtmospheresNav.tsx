import { NavLink } from 'react-router-dom'

export function AtmospheresNav() {
  return (
    <nav className="sub-nav">
      <NavLink to="/atmospheres" end>
        Gap map
      </NavLink>
      <NavLink to="/atmospheres/quality">Data quality</NavLink>
    </nav>
  )
}

import { NavLink, Route, Routes } from 'react-router-dom'
import { DropletLab } from './DropletLab.tsx'
import { Explorer } from './Explorer.tsx'
import './lab.css'

export function LabPage() {
  return (
    <section className="lab">
      <p className="eyebrow">Simulated and measured, side by side</p>
      <h1>Combustion lab</h1>
      <nav className="subnav">
        <NavLink to="/lab" end>
          Droplet lab
        </NavLink>
        <NavLink to="/lab/explore">Pattern explorer</NavLink>
      </nav>
      <Routes>
        <Route index element={<DropletLab />} />
        <Route path="explore" element={<Explorer />} />
      </Routes>
    </section>
  )
}

import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useTitle } from '../../useTitle.ts'
import { DropletLab } from './DropletLab.tsx'
import { Explorer } from './Explorer.tsx'
import './lab.css'

export function LabPage() {
  useTitle('Lab')
  return (
    <section className="lab">
      <header className="hero">
        <p className="eyebrow">Lab</p>
        <h1>
          Change the air. <span className="dim">Watch the flame.</span>
        </h1>
        <nav className="subnav">
          <NavLink to="/lab" end>
            Droplet
          </NavLink>
          <NavLink to="/lab/explore">Patterns</NavLink>
        </nav>
      </header>
      <Routes>
        <Route index element={<DropletLab />} />
        <Route path="explore" element={<Explorer />} />
        <Route path="*" element={<Navigate to="/lab" replace />} />
      </Routes>
    </section>
  )
}

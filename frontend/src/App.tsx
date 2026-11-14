import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { AskPage } from './features/ask/AskPage.tsx'
import { AtmospheresPage } from './features/atmospheres/AtmospheresPage.tsx'
import { DashboardPage } from './features/dashboard/DashboardPage.tsx'
import { LabPage } from './features/lab/LabPage.tsx'
import { ModelsPage } from './features/models/ModelsPage.tsx'

// Every feature page is already registered here, so feature work happens
// inside src/features/<name>/ and this file should not need editing.
const pages = [
  { path: '/dashboard', label: 'Dashboard', element: <DashboardPage /> },
  { path: '/atmospheres', label: 'Atmospheres', element: <AtmospheresPage /> },
  { path: '/models', label: 'Models', element: <ModelsPage /> },
  { path: '/lab', label: 'Lab', element: <LabPage /> },
  { path: '/ask', label: 'Ask', element: <AskPage /> },
]

export default function App() {
  return (
    <>
      <header className="app-header">
        <strong>Flame in Freefall</strong>
        <nav>
          {pages.map((page) => (
            <NavLink key={page.path} to={page.path}>
              {page.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          {pages.map((page) => (
            <Route key={page.path} path={`${page.path}/*`} element={page.element} />
          ))}
        </Routes>
      </main>
    </>
  )
}

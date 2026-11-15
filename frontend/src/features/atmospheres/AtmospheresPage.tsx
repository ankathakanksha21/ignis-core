import { Navigate, Route, Routes } from 'react-router-dom'
import { GapMapPage } from './GapMapPage.tsx'
import { QualityPage } from './QualityPage.tsx'
import './atmospheres.css'

export function AtmospheresPage() {
  return (
    <Routes>
      <Route index element={<GapMapPage />} />
      <Route path="quality" element={<QualityPage />} />
      <Route path="*" element={<Navigate to="/atmospheres" replace />} />
    </Routes>
  )
}

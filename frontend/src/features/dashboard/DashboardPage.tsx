import { Route, Routes } from 'react-router-dom'
import { InvestigationDetail } from './InvestigationDetail.tsx'
import { InvestigationList } from './InvestigationList.tsx'
import './dashboard.css'

export function DashboardPage() {
  return (
    <Routes>
      <Route index element={<InvestigationList />} />
      <Route path=":psiId" element={<InvestigationDetail />} />
    </Routes>
  )
}

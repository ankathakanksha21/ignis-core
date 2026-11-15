import { Route, Routes } from 'react-router-dom'
import { InvestigationDetail } from './InvestigationDetail.tsx'
import { InvestigationList } from './InvestigationList.tsx'
import { RankingPage } from './RankingPage.tsx'
import './dashboard.css'

export function DashboardPage() {
  return (
    <Routes>
      <Route index element={<InvestigationList />} />
      <Route path="rank" element={<RankingPage />} />
      <Route path=":psiId" element={<InvestigationDetail />} />
    </Routes>
  )
}

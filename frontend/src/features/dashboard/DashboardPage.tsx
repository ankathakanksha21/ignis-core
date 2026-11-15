import { Route, Routes } from 'react-router-dom'
import { ComparePage } from './ComparePage.tsx'
import { EarthPage } from './EarthPage.tsx'
import { InvestigationDetail } from './InvestigationDetail.tsx'
import { InvestigationList } from './InvestigationList.tsx'
import { RankingPage } from './RankingPage.tsx'
import { SimilarPage } from './SimilarPage.tsx'
import './dashboard.css'

export function DashboardPage() {
  return (
    <Routes>
      <Route index element={<InvestigationList />} />
      <Route path="rank" element={<RankingPage />} />
      <Route path="compare" element={<ComparePage />} />
      <Route path="similar" element={<SimilarPage />} />
      <Route path="earth" element={<EarthPage />} />
      <Route path=":psiId" element={<InvestigationDetail />} />
    </Routes>
  )
}

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppShell from './components/layout/AppShell'
import Dashboard from './pages/Dashboard'
import UploadPdf from './pages/UploadPdf'
import Ingestions from './pages/Ingestions'
import IngestionDetail from './pages/IngestionDetail'
import QuestionBank from './pages/QuestionBank'
import QuestionDetail from './pages/QuestionDetail'
import TestView from './pages/TestView'
import PaperGenerator from './pages/PaperGenerator'
import PaperDraft from './pages/PaperDraft'
import ApiDebug from './pages/ApiDebug'

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<UploadPdf />} />
            <Route path="ingestions" element={<Ingestions />} />
            <Route path="ingestions/:id" element={<IngestionDetail />} />
            <Route path="questions" element={<QuestionBank />} />
            <Route path="questions/:id" element={<QuestionDetail />} />
            <Route path="test" element={<TestView />} />
            <Route path="papers" element={<PaperGenerator />} />
            <Route path="papers/:id" element={<PaperDraft />} />
            <Route path="debug" element={<ApiDebug />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

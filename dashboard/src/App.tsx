import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Tickets } from './pages/Tickets'
import { TicketDetail } from './pages/TicketDetail'
import { Approvals } from './pages/Approvals'
import { CreateTicket } from './pages/CreateTicket'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/tickets/new" element={<CreateTicket />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/approvals" element={<Approvals />} />
      </Routes>
    </Layout>
  )
}

export default App

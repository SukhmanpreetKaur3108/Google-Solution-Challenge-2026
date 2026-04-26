import { Routes, Route } from 'react-router-dom'
import Landing    from './pages/Landing'
import Demo       from './pages/Demo'
import CertViewer from './pages/CertViewer'
import Explorer   from './pages/Explorer'
import Dashboard  from './pages/Dashboard'
import Navbar     from './components/Navbar'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/"              element={<Landing />} />
          <Route path="/demo"          element={<Demo />} />
          <Route path="/cert/:id"      element={<CertViewer />} />
          <Route path="/explorer"      element={<Explorer />} />
          <Route path="/dashboard"     element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}

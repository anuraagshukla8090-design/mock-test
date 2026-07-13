import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Upload, List, BookOpen,
  FileText, Bug, GraduationCap,
} from 'lucide-react'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload PDF' },
  { to: '/ingestions', icon: List, label: 'Ingestions' },
  { to: '/questions', icon: BookOpen, label: 'Question Bank' },
  { to: '/test', icon: GraduationCap, label: 'Test View' },
  { to: '/papers', icon: FileText, label: 'Paper Generator' },
  { to: '/debug', icon: Bug, label: 'API Debug' },
]

export default function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-gray-900 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-700">
          <p className="text-white font-semibold text-sm">Question Bank</p>
          <p className="text-gray-400 text-xs mt-0.5">Admin Panel · Dev Tool</p>
        </div>
        <nav className="flex-1 py-4 space-y-0.5">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-700">
          <p className="text-gray-500 text-xs">FastAPI → localhost:8000</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}

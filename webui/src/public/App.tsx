import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import ProductUsage from '../pages/ProductUsage';
import MonthlyUserPosts from '../pages/MonthlyUserPosts';
import ReportPlacementOverTime from '../pages/ReportPlacementOverTime';
import PublicHome from './PublicHome';

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? 'px-3 py-2 rounded-md text-sm font-medium bg-gray-700 text-white'
    : 'px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white';

export default function App() {
  return (
    <Router>
      <div className='min-h-screen bg-gray-900 text-white'>
        <header className='bg-gray-800 shadow'>
          <nav className='max-w-7xl mx-auto px-4 flex items-center gap-2 h-14'>
            <span className='font-bold mr-4'>SOTD Analytics</span>
            <NavLink to='/' end className={navClass}>
              Home
            </NavLink>
            <NavLink to='/product-usage' className={navClass}>
              Product Usage
            </NavLink>
            <NavLink to='/monthly-user-posts' className={navClass}>
              Monthly User Posts
            </NavLink>
            <NavLink to='/report-placement' className={navClass}>
              Placement Over Time
            </NavLink>
          </nav>
        </header>
        <main className='max-w-7xl mx-auto px-4 py-6'>
          <Routes>
            <Route path='/' element={<PublicHome />} />
            <Route path='/product-usage' element={<ProductUsage />} />
            <Route path='/monthly-user-posts' element={<MonthlyUserPosts />} />
            <Route path='/report-placement' element={<ReportPlacementOverTime />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

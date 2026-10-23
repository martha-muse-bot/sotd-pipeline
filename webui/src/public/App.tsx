import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import ProductUsage from '../pages/ProductUsage';
import MonthlyUserPosts from '../pages/MonthlyUserPosts';
import ReportPlacementOverTime from '../pages/ReportPlacementOverTime';
import PublicHome from './PublicHome';

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? 'block px-3 py-2 rounded-md text-sm font-medium bg-gray-700 text-white'
    : 'block px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white';

const navLinks = [
  { to: '/', label: 'Home', end: true },
  { to: '/product-usage', label: 'Product Usage' },
  { to: '/monthly-user-posts', label: 'Monthly User Posts' },
  { to: '/report-placement', label: 'Placement Over Time' },
];

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <Router>
      <div className='min-h-screen bg-gray-900 text-white'>
        <header className='bg-gray-800 shadow'>
          <nav className='max-w-7xl mx-auto px-4 h-14 flex items-center justify-between sm:justify-start sm:gap-2'>
            <span className='font-bold mr-4'>SOTD Analytics</span>
            {/* Desktop links */}
            <div className='hidden sm:flex items-center gap-2'>
              {navLinks.map(l => (
                <NavLink key={l.to} to={l.to} end={l.end} className={navClass}>
                  {l.label}
                </NavLink>
              ))}
            </div>
            {/* Mobile hamburger */}
            <button
              type='button'
              aria-label='Toggle navigation menu'
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(open => !open)}
              className='sm:hidden p-2 -mr-2 text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-500 rounded-md'
            >
              <svg className='h-6 w-6' fill='none' viewBox='0 0 24 24' stroke='currentColor'>
                {menuOpen ? (
                  <path
                    strokeLinecap='round'
                    strokeLinejoin='round'
                    strokeWidth={2}
                    d='M6 18L18 6M6 6l12 12'
                  />
                ) : (
                  <path
                    strokeLinecap='round'
                    strokeLinejoin='round'
                    strokeWidth={2}
                    d='M4 6h16M4 12h16M4 18h16'
                  />
                )}
              </svg>
            </button>
          </nav>
          {/* Mobile menu panel */}
          {menuOpen && (
            <div
              className='sm:hidden border-t border-gray-700 px-4 py-2 space-y-1'
              data-testid='mobile-nav'
            >
              {navLinks.map(l => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.end}
                  className={navClass}
                  onClick={() => setMenuOpen(false)}
                >
                  {l.label}
                </NavLink>
              ))}
            </div>
          )}
        </header>
        <main className='max-w-7xl mx-auto px-2 py-3 sm:px-4 sm:py-6'>
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

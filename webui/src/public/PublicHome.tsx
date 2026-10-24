import { Link } from 'react-router-dom';
import HomeDashboard from './HomeDashboard';

const cards = [
  {
    to: '/product-usage',
    title: 'Product Usage',
    desc: 'Explore which razors, blades, brushes, and soaps the community used each month.',
  },
  {
    to: '/monthly-user-posts',
    title: 'Monthly User Posts',
    desc: 'Who posted SOTDs this month, and how consistently.',
  },
  {
    to: '/report-placement',
    title: 'Placement Over Time',
    desc: 'How products moved through the monthly report rankings.',
  },
];

export default function PublicHome() {
  return (
    <div>
      <h1 className='text-2xl font-bold mb-2'>SOTD Analytics</h1>
      <p className='text-gray-400 mb-6'>
        Read-only statistics from the r/wetshaving Shave of the Day pipeline.
      </p>
      <HomeDashboard />
      <div className='grid gap-4 md:grid-cols-3 mt-4'>
        {cards.map(c => (
          <Link key={c.to} to={c.to} className='block rounded-lg bg-gray-800 p-5 hover:bg-gray-700'>
            <h2 className='text-lg font-semibold mb-1'>{c.title}</h2>
            <p className='text-sm text-gray-400'>{c.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

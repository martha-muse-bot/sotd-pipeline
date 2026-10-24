import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { buildMovers, buildPulseSeries, monthLabel } from './homeData';

interface PulsePoint {
  month: string;
  posts: number;
}

interface Mover {
  name: string;
  count: number;
  delta: number;
  is_new: boolean;
}

interface Overview {
  latest_month: string | null;
  pulse: PulsePoint[];
  tiles: {
    posts: number;
    shavers: number;
    top_razor: string | null;
    top_blade: string | null;
    top_soap: string | null;
    top_brush: string | null;
  } | null;
  movers: { razors: Mover[]; soaps: Mover[]; blades: Mover[] };
}

function MoverCard({ title, movers, month }: { title: string; movers: Mover[]; month: string }) {
  const rows = buildMovers(movers);
  const max = Math.max(1, ...rows.map(r => r.count));
  return (
    <div className='rounded-lg bg-gray-800 p-4'>
      <div className='flex items-baseline justify-between mb-2'>
        <h3 className='text-sm font-semibold text-gray-200'>{title}</h3>
        {month && <span className='text-xs text-gray-500'>{monthLabel(month)}</span>}
      </div>
      {rows.length === 0 ? (
        <p className='text-xs text-gray-500'>No data yet.</p>
      ) : (
        <ul className='space-y-1.5'>
          {rows.map(r => (
            <li key={r.name} className='text-xs'>
              <div className='flex items-baseline justify-between gap-2'>
                <span className='truncate text-gray-300'>{r.name}</span>
                <span
                  className={
                    r.direction === 'up'
                      ? 'text-green-400'
                      : r.direction === 'down'
                        ? 'text-red-400'
                        : 'text-gray-500'
                  }
                >
                  {r.display}
                </span>
              </div>
              <div className='mt-0.5 h-1.5 rounded bg-gray-700'>
                <div
                  className='h-1.5 rounded bg-blue-500'
                  style={{ width: `${(r.count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function HomeDashboard() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // jsdom (jest) has no fetch — degrade to the error card instead of
    // throwing inside the effect, which would crash the whole tree.
    if (typeof fetch !== 'function') {
      setError(true);
      return;
    }
    const qs = selectedMonth ? `?month=${selectedMonth}` : '';
    fetch(`/api/home/overview${qs}`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(body => {
        if (!cancelled) setOverview(body);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedMonth]);

  if (error) {
    return (
      <div className='rounded-lg bg-gray-800 p-6 text-sm text-gray-400'>
        Dashboard data unavailable right now.
      </div>
    );
  }
  if (!overview) {
    return <div className='h-96 rounded-lg bg-gray-800 animate-pulse' />;
  }

  const series = buildPulseSeries(overview.pulse);
  const latest = overview.latest_month;

  return (
    <div className='space-y-4'>
      {/* Community pulse hero */}
      <div className='rounded-lg bg-gray-800 p-4'>
        <div className='flex items-baseline justify-between mb-2'>
          <h2 className='text-lg font-semibold'>The Community Pulse</h2>
          <span className='text-xs text-gray-500'>SOTD posts per month, 2016 → today</span>
        </div>
        {series.length === 0 ? (
          <p className='text-sm text-gray-500'>No data yet.</p>
        ) : (
          <ResponsiveContainer width='100%' height={280}>
            <AreaChart
              data={series}
              margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
              onClick={(state: { activeLabel?: string | number }) => {
                const month =
                  typeof state?.activeLabel === 'string' ? state.activeLabel : undefined;
                if (month) {
                  setSelectedMonth(month);
                  navigate('/', { replace: true });
                }
              }}
            >
              <defs>
                <linearGradient id='pulseFill' x1='0' y1='0' x2='0' y2='1'>
                  <stop offset='0%' stopColor='#3b82f6' stopOpacity={0.45} />
                  <stop offset='100%' stopColor='#3b82f6' stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <XAxis dataKey='month' tick={{ fill: '#6b7280', fontSize: 11 }} minTickGap={48} />
              <YAxis hide domain={[0, 'auto']} />
              <Tooltip
                labelFormatter={(m: string | number) => monthLabel(String(m))}
                formatter={(value: number | string) => [value, 'SOTD posts']}
                contentStyle={{ background: '#1f2937', border: 'none', color: '#e5e7eb' }}
              />
              <Area
                type='monotone'
                dataKey='posts'
                stroke='#3b82f6'
                strokeWidth={2}
                fill='url(#pulseFill)'
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Selected month at a glance (chart click changes the month) */}
      {overview.tiles && latest && (
        <div className='grid grid-cols-2 gap-4 md:grid-cols-5'>
          <Link
            to={`/monthly-user-posts?months=${latest}`}
            className='rounded-lg bg-gray-800 p-4 hover:bg-gray-700'
          >
            <div className='text-2xl font-bold'>{overview.tiles.posts}</div>
            <div className='text-xs text-gray-400'>SOTDs in {monthLabel(latest)}</div>
          </Link>
          <Link
            to={`/monthly-user-posts?months=${latest}`}
            className='rounded-lg bg-gray-800 p-4 hover:bg-gray-700'
          >
            <div className='text-2xl font-bold'>{overview.tiles.shavers}</div>
            <div className='text-xs text-gray-400'>Shavers posting</div>
          </Link>
          {(
            [
              ['Top soap', overview.tiles.top_soap, 'soaps'],
              ['Top razor', overview.tiles.top_razor, 'razors'],
              ['Top blade', overview.tiles.top_blade, 'blades'],
            ] as Array<[string, string | null, string]>
          ).map(([label, value, tableId]) => (
            <Link
              key={label}
              to={
                value
                  ? `/report-placement?productType=${tableId}&item=${encodeURIComponent(value)}&from=${latest}`
                  : `/report-placement`
              }
              className='rounded-lg bg-gray-800 p-4 hover:bg-gray-700'
            >
              <div className='text-sm font-semibold truncate' title={value ?? undefined}>
                {value ?? '—'}
              </div>
              <div className='text-xs text-gray-400'>{label}</div>
            </Link>
          ))}
        </div>
      )}

      {/* On the move */}
      <div className='grid gap-4 md:grid-cols-3'>
        <MoverCard title='Soaps on the move' movers={overview.movers.soaps} month={latest ?? ''} />
        <MoverCard
          title='Razors on the move'
          movers={overview.movers.razors}
          month={latest ?? ''}
        />
        <MoverCard
          title='Blades on the move'
          movers={overview.movers.blades}
          month={latest ?? ''}
        />
      </div>
    </div>
  );
}

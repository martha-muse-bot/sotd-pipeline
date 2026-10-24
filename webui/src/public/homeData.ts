/** Derivations for the public home dashboard: pulse series, movers, labels. */

export interface PulsePoint {
  month: string;
  posts: number;
}

export interface ApiMover {
  name: string;
  count: number;
  delta: number;
  is_new: boolean;
}

export interface MoverRow {
  name: string;
  count: number;
  display: string;
  direction: 'up' | 'down' | 'new' | 'flat';
}

const MONTH_ABBR = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export function monthLabel(month: string): string {
  const [y, m] = month.split('-');
  const idx = parseInt(m, 10) - 1;
  return `${MONTH_ABBR[idx] ?? m} ${y}`;
}

export function buildPulseSeries(pulse: PulsePoint[]): Array<PulsePoint & { label: string }> {
  return pulse.map(p => ({ ...p, label: monthLabel(p.month) }));
}

export function buildMovers(movers: ApiMover[]): MoverRow[] {
  return movers.map(m => {
    if (m.is_new)
      return { name: m.name, count: m.count, display: 'new', direction: 'new' as const };
    if (m.delta > 0)
      return { name: m.name, count: m.count, display: `↑${m.delta}`, direction: 'up' as const };
    if (m.delta < 0)
      return { name: m.name, count: m.count, display: `↓${-m.delta}`, direction: 'down' as const };
    return { name: m.name, count: m.count, display: '—', direction: 'flat' as const };
  });
}

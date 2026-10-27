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

/** "Data through <coverage end>", or null when no value — never crash the
 * page. The bundle stamps the newest SOTD comment timestamp (ISO) at publish
 * time; the request-path fallback carries a date-only string. Timestamps
 * render in the viewer's local time (pass `timeZone` to pin it — tests do);
 * date-only values render pinned to UTC (a timezone shift would misreport
 * them). */
export function coverageLabel(
  dataThrough: string | null | undefined,
  timeZone?: string
): string | null {
  if (!dataThrough) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(dataThrough)) {
    const through = new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC', // date-only strings parse as UTC midnight — keep it
    }).format(new Date(dataThrough));
    return `Data through ${through}`;
  }
  const d = new Date(dataThrough);
  if (isNaN(d.getTime())) return null;
  const when = new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
    timeZoneName: 'short',
  }).format(d);
  return `Data through ${when}`;
}

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

/** "Data through <date> · updated <datetime>", or null when no stamp
 * (pre-generated_at bundles) or an unparseable stamp — never crash the page.
 * Coverage prefers the exact last posted date (the current month is partial);
 * falls back to the month label for bundles without it. Coverage is a
 * date-only value rendered pinned to UTC (a timezone shift would misreport
 * it); the update stamp renders in the viewer's local time (pass `timeZone`
 * to pin it — tests do). */
export function updatedAtLabel(
  generatedAt: string | null | undefined,
  dataThrough: string | null | undefined,
  latestMonth: string | null | undefined,
  timeZone?: string,
): string | null {
  if (!generatedAt) return null;
  const d = new Date(generatedAt);
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
  if (dataThrough && /^\d{4}-\d{2}-\d{2}$/.test(dataThrough)) {
    const through = new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC', // date-only strings parse as UTC midnight — keep it
    }).format(new Date(dataThrough));
    return `Data through ${through} · updated ${when}`;
  }
  return latestMonth
    ? `Data through ${monthLabel(latestMonth)} · updated ${when}`
    : `Updated ${when}`;
}

import { buildMovers, buildPulseSeries, coverageLabel, monthLabel } from '../homeData';

describe('monthLabel', () => {
  it('formats YYYY-MM as Mon YYYY', () => {
    expect(monthLabel('2026-10')).toBe('Oct 2026');
  });
});

describe('buildPulseSeries', () => {
  it('passes through pulse points with labels', () => {
    const series = buildPulseSeries([
      { month: '2026-08', posts: 9 },
      { month: '2026-10', posts: 7 },
    ]);
    expect(series).toHaveLength(2);
    expect(series[0]).toEqual({ month: '2026-08', posts: 9, label: 'Aug 2026' });
  });
});

describe('buildMovers', () => {
  const movers = [
    { name: 'Gillette NEW', count: 5, delta: 2, is_new: false },
    { name: 'Wolfman', count: 3, delta: -1, is_new: false },
    { name: 'Blackbird', count: 2, delta: 0, is_new: true },
  ];

  it('formats up movers with arrow', () => {
    expect(buildMovers(movers)[0].display).toBe('↑2');
  });
  it('formats down movers with arrow', () => {
    expect(buildMovers(movers)[1].display).toBe('↓1');
  });
  it('marks NEW entries', () => {
    expect(buildMovers(movers)[2].display).toBe('new');
  });
});

describe('coverageLabel', () => {
  // Tests pin the zone for exact assertions; the component passes no zone
  // so viewers get their local time for timestamps.
  const UTC = 'UTC';

  it('renders a publish-time ISO stamp in the given zone', () => {
    expect(coverageLabel('2026-10-27T14:06:59Z', UTC)).toBe(
      'Data through Oct 27, 2026, 2:06 PM UTC'
    );
  });
  it('renders timestamps in the viewer zone when not pinned (UTC vs Chicago)', () => {
    expect(coverageLabel('2026-10-27T14:06:59Z', 'America/Chicago')).toBe(
      'Data through Oct 27, 2026, 9:06 AM CDT'
    );
  });
  it('renders a date-only fallback value pinned to UTC', () => {
    expect(coverageLabel('2026-10-24', 'America/Chicago')).toBe('Data through Oct 24, 2026');
  });
  it('returns null for missing or unparseable values', () => {
    expect(coverageLabel(null, UTC)).toBeNull();
    expect(coverageLabel(undefined, UTC)).toBeNull();
    expect(coverageLabel('not a date', UTC)).toBeNull();
  });
});

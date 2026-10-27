import { buildMovers, buildPulseSeries, monthLabel, updatedAtLabel } from '../homeData';

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

describe('updatedAtLabel', () => {
  // Tests pin the stamp to UTC for exact assertions; the component passes
  // no zone so viewers get their local time.
  const UTC = 'UTC';

  it('formats the stamp with full date, time, and zone', () => {
    expect(updatedAtLabel('2026-10-26T02:10:00+00:00', UTC)).toBe(
      'Updated Oct 26, 2026, 2:10 AM UTC'
    );
  });
  it('renders the stamp in the given zone (UTC vs Chicago)', () => {
    expect(updatedAtLabel('2026-10-26T02:10:00+00:00', 'America/Chicago')).toBe(
      'Updated Oct 25, 2026, 9:10 PM CDT'
    );
  });
  it('renders local time when no zone is passed', () => {
    // Structure only — the runner's zone varies (CI is UTC, dev is not).
    expect(updatedAtLabel('2026-10-26T02:10:00+00:00')).toMatch(
      /^Updated Oct 2[56], 2026, \d{1,2}:\d{2} [AP]M [A-Z]+$/
    );
  });
  it('returns null for missing or unparseable stamps', () => {
    expect(updatedAtLabel(null, UTC)).toBeNull();
    expect(updatedAtLabel(undefined, UTC)).toBeNull();
    expect(updatedAtLabel('not a date', UTC)).toBeNull();
  });
});

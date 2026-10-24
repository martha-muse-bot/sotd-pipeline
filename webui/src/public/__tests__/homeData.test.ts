import { buildMovers, buildPulseSeries, monthLabel } from '../homeData';

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

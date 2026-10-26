import { createEmptyUserAnalysis, fillAbsentMonths } from '../userAnalysis';

describe('createEmptyUserAnalysis', () => {
  it('returns a zero-posting analysis with all days missed', () => {
    const result = createEmptyUserAnalysis('2019-08', 'Old_Hiker');

    expect(result.user).toBe('Old_Hiker');
    expect(result.posted_days).toBe(0);
    expect(result.missed_days).toBe(31); // August has 31 days
    expect(result.posted_dates).toEqual([]);
    expect(result.comment_ids).toEqual([]);
    expect(result.comments_by_date).toEqual({});
  });

  it('handles 30-day months', () => {
    const result = createEmptyUserAnalysis('2019-09', 'someone');
    expect(result.missed_days).toBe(30);
  });

  it('handles February in a leap year', () => {
    const result = createEmptyUserAnalysis('2020-02', 'someone');
    expect(result.missed_days).toBe(29);
  });

  it('includes empty product arrays so aggregation works', () => {
    const result = createEmptyUserAnalysis('2019-08', 'Old_Hiker');
    expect(result.razors).toEqual([]);
    expect(result.blades).toEqual([]);
    expect(result.brushes).toEqual([]);
    expect(result.soaps).toEqual([]);
  });
});

describe('fillAbsentMonths', () => {
  const foundAnalysis = {
    user: 'Old_Hiker',
    posted_days: 2,
    missed_days: 29,
    posted_dates: ['2019-07-01', '2019-07-02'],
    comment_ids: ['c1'],
    comments_by_date: { '2019-07-01': ['c1'] },
    razors: [],
    blades: [],
    brushes: [],
    soaps: [],
  };

  it('keeps found analyses and fills absent months with empty ones', () => {
    const result = fillAbsentMonths(
      ['2019-07', '2019-08', '2019-09'],
      { '2019-07': foundAnalysis, '2019-09': foundAnalysis },
      'Old_Hiker'
    );

    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ month: '2019-07', analysis: foundAnalysis });
    expect(result[1].month).toBe('2019-08');
    expect(result[1].analysis.posted_days).toBe(0);
    expect(result[1].analysis.missed_days).toBe(31);
    expect(result[2].analysis.posted_days).toBe(2);
  });

  it('preserves the caller month order (no sorting)', () => {
    const result = fillAbsentMonths(
      ['2019-09', '2019-07'],
      { '2019-07': foundAnalysis, '2019-09': foundAnalysis },
      'Old_Hiker'
    );
    expect(result.map(r => r.month)).toEqual(['2019-09', '2019-07']);
  });
});

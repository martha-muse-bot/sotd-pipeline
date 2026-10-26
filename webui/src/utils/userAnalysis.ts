/**
 * Helpers for user posting analyses.
 *
 * A user who posted nothing in a month has no entry in the pre-computed
 * user_analysis aggregates, so the API 404s. The calendar should still render
 * that month (all cells red), so callers synthesize an empty analysis here.
 */
export interface UserPostingAnalysis {
  user: string;
  posted_days: number;
  missed_days: number;
  posted_dates: string[];
  comment_ids: string[];
  comments_by_date: Record<string, string[]>;
  comment_urls?: Record<string, string>; // Optional for backward compatibility
  // Product usage data
  razors: Array<{
    key: string;
    brand: string;
    model: string;
    count: number;
    comment_ids: string[];
  }>;
  blades: Array<{
    key: string;
    brand: string;
    model: string;
    count: number;
    comment_ids: string[];
  }>;
  brushes: Array<{
    key: string;
    brand: string;
    model: string;
    handle_brand: string;
    knot_brand: string;
    knot_model: string;
    count: number;
    comment_ids: string[];
  }>;
  soaps: Array<{
    key: string;
    brand: string;
    model: string;
    count: number;
    comment_ids: string[];
  }>;
}

/** Days in a YYYY-MM month. */
const daysInMonth = (month: string): number => {
  const [year, mon] = month.split('-').map(Number);
  return new Date(year, mon, 0).getDate();
};

/** Synthesize a zero-posting analysis for a month the user is absent from. */
export const createEmptyUserAnalysis = (month: string, username: string): UserPostingAnalysis => ({
  user: username,
  posted_days: 0,
  missed_days: daysInMonth(month),
  posted_dates: [],
  comment_ids: [],
  comments_by_date: {},
  razors: [],
  blades: [],
  brushes: [],
  soaps: [],
});

/**
 * Pair analyses with their months, synthesizing empty analyses for months the
 * user is absent from (API 404 → all-red calendar instead of a skipped month).
 * The "user not found in any month" error case is the caller's job.
 */
export const fillAbsentMonths = (
  months: string[],
  found: Record<string, UserPostingAnalysis>,
  username: string
): Array<{ month: string; analysis: UserPostingAnalysis }> =>
  months.map(month => ({
    month,
    analysis: found[month] ?? createEmptyUserAnalysis(month, username),
  }));

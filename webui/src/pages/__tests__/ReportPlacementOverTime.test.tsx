import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

jest.mock('../../services/api', () => ({
  getReportRankingsTables: jest.fn(),
  getReportRankingsItems: jest.fn(),
  getReportRankingsSeries: jest.fn(),
  getReportRankingsPivoted: jest.fn(),
  handleApiError: jest.fn((err: unknown) => (err instanceof Error ? err.message : 'API Error')),
}));

import ReportPlacementOverTime, {
  RankChartTooltipContent,
  filterMonthsInRange,
  buildChartData,
  groupAggregationTables,
} from '../ReportPlacementOverTime';
import * as api from '../../services/api';

const mockGetTables = api.getReportRankingsTables as jest.MockedFunction<
  typeof api.getReportRankingsTables
>;
const mockGetItems = api.getReportRankingsItems as jest.MockedFunction<
  typeof api.getReportRankingsItems
>;
const mockGetSeries = api.getReportRankingsSeries as jest.MockedFunction<
  typeof api.getReportRankingsSeries
>;
const mockGetPivoted = api.getReportRankingsPivoted as jest.MockedFunction<
  typeof api.getReportRankingsPivoted
>;

describe('ReportPlacementOverTime', () => {
  // Radix DropdownMenu opens on the full pointer sequence; userEvent provides it.
  let aggUser: ReturnType<typeof userEvent.setup> | null = null;
  const openAggregationMenu = async () => {
    aggUser = aggUser ?? userEvent.setup();
    await aggUser.click(screen.getByRole('button', { name: 'Select aggregation' }));
  };
  const expandGroup = async (name: string) => {
    aggUser = aggUser ?? userEvent.setup();
    // Group headers carry aria-expanded; items don't.
    const headers = screen
      .queryAllByRole('menuitem')
      .filter(el => el.getAttribute('aria-expanded') != null);
    const header = headers.find(el => el.textContent?.startsWith(name));
    if (!header) throw new Error(`group header "${name}" not found`);
    await aggUser.click(header);
  };
  // Group headers and same-named items share text; items have no aria-expanded.
  const expectMenuItem = (name: string) => {
    const items = screen
      .queryAllByRole('menuitem')
      .filter(el => el.textContent === name && el.getAttribute('aria-expanded') == null);
    expect(items.length).toBeGreaterThan(0);
  };
  const selectAggregation = async (name: string) => {
    aggUser = aggUser ?? userEvent.setup();
    const items = screen
      .queryAllByRole('menuitem')
      .filter(el => el.textContent === name && el.getAttribute('aria-expanded') == null);
    expect(items.length).toBeGreaterThan(0);
    await aggUser.click(items[0]);
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetTables.mockResolvedValue([
      { id: 'razors', label: 'Razors' },
      { id: 'blades', label: 'Blades' },
    ]);
    mockGetItems.mockResolvedValue(['Razor A', 'Razor B', 'Razor C']);
    mockGetSeries.mockResolvedValue({
      months: ['2025-06', '2025-07'],
      series: [
        {
          item: 'Razor A',
          data: [
            { month: '2025-06', rank: 1, shaves: 100, unique_users: 10 },
            { month: '2025-07', rank: 2, shaves: 80, unique_users: 8 },
          ],
        },
        {
          item: 'Razor B',
          data: [
            { month: '2025-06', rank: 2, shaves: 80, unique_users: 8 },
            { month: '2025-07', rank: 1, shaves: 90, unique_users: 9 },
          ],
        },
      ],
    });
    mockGetPivoted.mockResolvedValue({
      months: ['2025-06', '2025-07'],
      lanes: [
        {
          rank: 1,
          points: [
            { month: '2025-06', item: 'Razor A', shaves: 100, unique_users: 10, prev_rank: null },
            { month: '2025-07', item: 'Razor B', shaves: 90, unique_users: 9, prev_rank: 2 },
          ],
        },
        {
          rank: 2,
          points: [
            { month: '2025-06', item: 'Razor B', shaves: 80, unique_users: 8, prev_rank: null },
            { month: '2025-07', item: 'Razor A', shaves: 80, unique_users: 8, prev_rank: 1 },
          ],
        },
      ],
    });
  });

  it('renders page title and description', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Rankings over time')).toBeInTheDocument();
    });
    expect(screen.getByText(/see how they ranked month over month/)).toBeInTheDocument();
  });

  it('fetches tables on mount', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
  });

  it('shows empty state when no aggregation selected', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    expect(
      screen.getByText(
        /Choose an aggregation and one or more items to see how they placed over time/
      )
    ).toBeInTheDocument();
  });

  it('shows aggregation dropdown with tables after load', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    // Sections start collapsed; open the two groups and check their items appear.
    await expandGroup('Razors');
    await expandGroup('Blades');
    expectMenuItem('Razors');
    expectMenuItem('Blades');
  });

  it('Load series button is disabled when no aggregation or items selected', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    const loadButton = screen.getByRole('button', { name: /Load series/i });
    expect(loadButton).toBeDisabled();
  });

  it('renders Controls card with aggregation and Load series button', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    expect(screen.getByText('Controls')).toBeInTheDocument();
    expect(screen.getByText('Aggregation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Load series/i })).toBeInTheDocument();
  });

  it('shows View mode toggle (By item / By position) when aggregation selected', async () => {
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await waitFor(() => {
      expect(screen.getByText('By item')).toBeInTheDocument();
      expect(screen.getByText('By position')).toBeInTheDocument();
    });
  });

  it('fetches pivoted data and shows swim lanes when By position selected', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /By position/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalledWith('razors');
    });
    await waitFor(
      () => {
        expect(screen.getByText('Swim lanes (top 20)')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
    expect(screen.getByText('Rank', { selector: 'th' })).toBeInTheDocument();
  });

  it('shows no pivoted data message when pivoted returns empty', async () => {
    mockGetPivoted.mockResolvedValueOnce({ months: [], lanes: [] });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('No pivoted data for this aggregation.')).toBeInTheDocument();
    });
  });

  it('clicking a swim lane cell with an item adds that item to selection', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalledWith('razors');
    });
    await waitFor(() => {
      expect(screen.getByText('Swim lanes (top 20)')).toBeInTheDocument();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    await user.click(screen.getByRole('tab', { name: /By item/i }));
    const loadButton = screen.getByRole('button', { name: /Load series/i });
    expect(loadButton).not.toBeDisabled();
  });

  it('shows highlighted cells in swim lane when items are pre-selected', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('Swim lanes (top 20)')).toBeInTheDocument();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    const cellsWithRazorA = screen.getAllByText(/Razor A/);
    const tableCellWithHighlight = cellsWithRazorA.find(
      el => el.closest('td')?.querySelector('span[style*="opacity"]') != null
    );
    expect(tableCellWithHighlight).toBeDefined();
  });

  it('shows shaves and unique users in By item data table when series has unique_users', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('Swim lanes (top 20)')).toBeInTheDocument();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    await user.click(screen.getByRole('tab', { name: /By item/i }));
    await waitFor(() => {
      expect(mockGetSeries).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('Data table')).toBeInTheDocument();
    });
    expect(screen.getByText(/100 shaves, 10 users/)).toBeInTheDocument();
  });

  it('shows placement summary above data table with 1st places, podiums, and top 10s', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    await user.click(screen.getByRole('tab', { name: /By item/i }));
    await waitFor(() => {
      expect(mockGetSeries).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('Data table')).toBeInTheDocument();
    });
    expect(screen.getByText(/1st places:/)).toBeInTheDocument();
    expect(screen.getByText(/Podiums \(1–3\):/)).toBeInTheDocument();
    expect(screen.getByText(/Top 10s:/)).toBeInTheDocument();
    const summaryDiv = screen.getByText(/1st places:/).closest('div');
    expect(summaryDiv).toHaveTextContent('2');
    expect(summaryDiv).toHaveTextContent('4');
  });

  it('chart metric control is present and switching to Shaves works', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    await user.click(screen.getByRole('tab', { name: /By item/i }));
    await waitFor(() => {
      expect(mockGetSeries).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('Chart metric')).toBeInTheDocument();
    });
    const shavesTab = screen.getByRole('tab', { name: /Shaves/i });
    await user.click(shavesTab);
    expect(screen.getByText('Rank over time')).toBeInTheDocument();
  });

  describe('groupAggregationTables', () => {
    const allTables = [
      { id: 'razors', label: 'Razors' },
      { id: 'blades', label: 'Blades' },
      { id: 'users', label: 'Users' },
      { id: 'some_future_table', label: 'Future Thing' },
    ];

    it('buckets tables into their groups in group order', () => {
      const groups = groupAggregationTables(allTables);
      expect(groups.map(g => g.label)).toEqual(['Razors', 'Blades', 'User stats', 'Other']);
      expect(groups[0].tables).toEqual([{ id: 'razors', label: 'Razors' }]);
      expect(groups[1].tables).toEqual([{ id: 'blades', label: 'Blades' }]);
      expect(groups[2].tables).toEqual([{ id: 'users', label: 'Users' }]);
    });

    it('puts unknown ids into Other', () => {
      const groups = groupAggregationTables(allTables);
      expect(groups[3].tables).toEqual([{ id: 'some_future_table', label: 'Future Thing' }]);
    });

    it('omits empty groups', () => {
      const groups = groupAggregationTables([{ id: 'soaps', label: 'Soaps' }]);
      expect(groups.map(g => g.label)).toEqual(['Soaps']);
    });
  });

  describe('filterMonthsInRange', () => {
    const months = ['2024-01', '2024-06', '2025-01', '2025-06', '2025-07'];

    it('returns all months when from/to are empty', () => {
      expect(filterMonthsInRange(months, '', '')).toEqual(months);
    });

    it('filters inclusive from and to bounds', () => {
      expect(filterMonthsInRange(months, '2024-06', '2025-06')).toEqual([
        '2024-06',
        '2025-01',
        '2025-06',
      ]);
    });

    it('returns empty when range excludes all months', () => {
      expect(filterMonthsInRange(months, '2026-01', '2026-12')).toEqual([]);
    });
  });

  it('renders chart time oldest-left and data table newest-first', async () => {
    const user = userEvent.setup();
    const mockGetSeriesResult = {
      months: ['2025-05', '2025-06', '2025-07'],
      series: [
        {
          item: 'Razor A',
          data: [
            { month: '2025-05', rank: 3, shaves: 50, unique_users: 5 },
            { month: '2025-06', rank: 1, shaves: 100, unique_users: 10 },
            { month: '2025-07', rank: 2, shaves: 80, unique_users: 8 },
          ],
        },
      ],
    };
    mockGetSeries.mockResolvedValue(mockGetSeriesResult);
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    // Add the item via a swim-lane cell (the reliable path used by other tests),
    // then return to By item — the view switch auto-loads the series.
    await user.click(screen.getByRole('tab', { name: /By position/i }));
    await waitFor(() => {
      expect(mockGetPivoted).toHaveBeenCalled();
    });
    const razorACells = screen.getAllByRole('button', { name: /Razor A/ });
    await user.click(razorACells[0]);
    await user.click(screen.getByRole('tab', { name: /By item/i }));
    await waitFor(() => {
      expect(mockGetSeries).toHaveBeenCalled();
    });

    // Chart data is chronological (oldest first → time runs left-to-right on the
    // chart). Chart internals aren't renderable in jsdom (ResponsiveContainer has
    // no width), so the ordering is asserted on the extracted builder.
    expect(buildChartData(mockGetSeriesResult)).toEqual([
      { month: '2025-05', 'Razor A': 3, 'Razor A_shaves': 50, 'Razor A_unique_users': 5 },
      { month: '2025-06', 'Razor A': 1, 'Razor A_shaves': 100, 'Razor A_unique_users': 10 },
      { month: '2025-07', 'Razor A': 2, 'Razor A_shaves': 80, 'Razor A_unique_users': 8 },
    ]);

    // Data table: newest month is the first row under the header.
    const tableRows = screen.getAllByRole('row').filter(row => row.textContent?.includes('2025-'));
    expect(tableRows[0]).toHaveTextContent('2025-07');
    expect(tableRows[tableRows.length - 1]).toHaveTextContent('2025-05');
  });

  it('shows From/To month filters after series loads and defaults to full range', async () => {
    const user = userEvent.setup();
    mockGetSeries.mockResolvedValue({
      months: ['2025-05', '2025-06', '2025-07'],
      series: [
        {
          item: 'Razor A',
          data: [
            { month: '2025-05', rank: 3, shaves: 50, unique_users: 5 },
            { month: '2025-06', rank: 1, shaves: 100, unique_users: 10 },
            { month: '2025-07', rank: 2, shaves: 80, unique_users: 8 },
          ],
        },
      ],
    });
    render(
      <MemoryRouter>
        <ReportPlacementOverTime />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(mockGetTables).toHaveBeenCalled();
    });
    await openAggregationMenu();
    await expandGroup('Razors');
    await selectAggregation('Razors');
    await waitFor(() => {
      expect(mockGetItems).toHaveBeenCalled();
    });
    const itemsTrigger = screen
      .getAllByRole('combobox')
      .find(el => el.textContent?.includes('Add an item'));
    fireEvent.click(itemsTrigger!);
    await waitFor(() => {
      expect(screen.getByText('Razor A')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Razor A'));
    await user.click(screen.getByRole('button', { name: /Load series/i }));
    await waitFor(() => {
      expect(screen.getByText('Chart metric')).toBeInTheDocument();
    });
    expect(screen.getByText('From')).toBeInTheDocument();
    expect(screen.getByText('To')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toHaveTextContent('2025-05');
    expect(screen.getByLabelText('To')).toHaveTextContent('2025-07');
  });

  it('chart tooltip content shows shaves and unique users for payload', () => {
    const payload = [
      {
        payload: {
          month: '2025-06',
          'Razor A': 1,
          'Razor A_shaves': 100,
          'Razor A_unique_users': 10,
        },
      },
    ];
    const series = [{ item: 'Razor A' }];
    const { container } = render(
      <>{RankChartTooltipContent({ active: true, payload, label: '2025-06' }, series)}</>
    );
    expect(container.textContent).toMatch(/100 shaves/);
    expect(container.textContent).toMatch(/10 users/);
  });

  describe('type-ahead when aggregation has more than 50 items', () => {
    const manyItems = [
      ...Array.from({ length: 48 }, (_, i) => `Soap ${i + 1}`),
      'Razor A',
      'Razor B',
      'Razor C',
    ];

    beforeEach(() => {
      mockGetItems.mockResolvedValue(manyItems);
      mockGetSeries.mockResolvedValue({
        months: ['2025-06', '2025-07'],
        series: [
          {
            item: 'Razor A',
            data: [
              { month: '2025-06', rank: 1, shaves: 100, unique_users: 10 },
              { month: '2025-07', rank: 2, shaves: 80, unique_users: 8 },
            ],
          },
        ],
      });
    });

    it('shows type-to-search input instead of Select when items exceed 50', async () => {
      render(
        <MemoryRouter>
          <ReportPlacementOverTime />
        </MemoryRouter>
      );
      await waitFor(() => {
        expect(mockGetTables).toHaveBeenCalled();
      });
      await openAggregationMenu();
      await expandGroup('Razors');
      await selectAggregation('Razors');
      await waitFor(() => {
        expect(mockGetItems).toHaveBeenCalledWith('razors');
      });
      const itemsInput = screen.getByPlaceholderText('Type to search…');
      expect(itemsInput).toBeInTheDocument();
      expect(itemsInput).toHaveAttribute('role', 'combobox');
    });

    it('typing filters the list and selecting an item adds it to selection', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <ReportPlacementOverTime />
        </MemoryRouter>
      );
      await waitFor(() => {
        expect(mockGetTables).toHaveBeenCalled();
      });
      await openAggregationMenu();
      await expandGroup('Razors');
      await selectAggregation('Razors');
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Type to search…')).toBeInTheDocument();
      });
      const itemsInput = screen.getByPlaceholderText('Type to search…');
      await user.click(itemsInput);
      await waitFor(() => {
        expect(screen.getByText('Soap 1')).toBeInTheDocument();
      });
      fireEvent.change(itemsInput, { target: { value: 'Razor' } });
      await waitFor(() => {
        expect(screen.getByText('Razor A')).toBeInTheDocument();
        expect(screen.getByText('Razor B')).toBeInTheDocument();
        expect(screen.getByText('Razor C')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Razor A'));
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Load series/i })).not.toBeDisabled();
      });
    });
  });
});

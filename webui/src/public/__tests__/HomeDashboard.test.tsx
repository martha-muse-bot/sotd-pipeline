import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HomeDashboard from '../HomeDashboard';

// The dashboard fetches on mount; jsdom has no fetch (the component guards
// this and shows its error card), so tests drive the component through its
// rendered output after mocking fetch to return a full overview payload.
beforeAll(() => {
  // @ts-expect-error jsdom lacks fetch; provide minimal impl for tests
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          latest_month: '2026-10',
          generated_at: '2026-10-26T02:10:00+00:00',
          data_through: '2026-10-24',
          pulse: [
            { month: '2026-09', posts: 10 },
            { month: '2026-10', posts: 7 },
          ],
          tiles: {
            posts: 7,
            shavers: 3,
            top_razor: 'Gillette NEW',
            top_blade: 'Personna GEM',
            top_soap: 'Catie’s Bubbles Tonsorium',
            top_brush: null,
          },
          movers: {
            razors: [{ name: 'Gillette NEW', count: 5, delta: 0, is_new: false }],
            soaps: [{ name: 'Catie’s Bubbles Tonsorium', count: 25, delta: 0, is_new: false }],
            blades: [{ name: 'Personna GEM', count: 9, delta: 1, is_new: false }],
          },
        }),
    })
  );
});

afterAll(() => {
  // @ts-expect-error test teardown
  delete global.fetch;
});

describe('HomeDashboard freshness line', () => {
  it('renders the data-freshness line at the top', async () => {
    render(
      <MemoryRouter>
        <HomeDashboard />
      </MemoryRouter>
    );
    const line = await screen.findByTestId('freshness');
    // The stamp renders in the viewer's (test runner's) local zone —
    // homeData.test.ts pins exact strings; here only the structure is pinned.
    expect(line.textContent).toMatch(/^Updated \w+ \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M [A-Z]+$/);
  });

  it('omits the freshness line for pre-generated_at payloads', async () => {
    const original = global.fetch;
    // @ts-expect-error jsdom lacks fetch; override with a stampless payload
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            latest_month: '2026-10',
            generated_at: null,
            data_through: null,
            pulse: [{ month: '2026-10', posts: 7 }],
            tiles: null,
            movers: { razors: [], soaps: [], blades: [] },
          }),
      })
    );
    render(
      <MemoryRouter>
        <HomeDashboard />
      </MemoryRouter>
    );
    await screen.findByText('The Community Pulse');
    expect(screen.queryByTestId('freshness')).toBeNull();
    global.fetch = original;
  });
});

describe('HomeDashboard mover links', () => {
  it('renders mover names as links to placement over time', async () => {
    render(
      <MemoryRouter>
        <HomeDashboard />
      </MemoryRouter>
    );
    const link = await screen.findByRole('link', { name: 'Catie’s Bubbles Tonsorium' });
    expect(link.getAttribute('href')).toBe(
      '/report-placement?productType=soaps&item=' + encodeURIComponent('Catie’s Bubbles Tonsorium')
    );
  });

  it('renders product tiles as placement deep-links', async () => {
    render(
      <MemoryRouter>
        <HomeDashboard />
      </MemoryRouter>
    );
    const tile = await screen.findByRole('link', { name: /Top soap/ });
    expect(tile.getAttribute('href')).toContain('/report-placement?productType=soaps');
  });
});

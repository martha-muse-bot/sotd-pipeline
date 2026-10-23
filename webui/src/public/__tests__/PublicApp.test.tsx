import { render, screen, within } from '@testing-library/react';
import App from '../App';

// Shared pages import from '@/services/api' — mirror that specifier exactly.
jest.mock('@/services/api', () => ({
  api: { get: jest.fn().mockResolvedValue({ data: [] }) },
  handleApiError: jest.fn((e: unknown) => String(e)),
}));

// App owns its own BrowserRouter (same pattern as the admin App), so tests
// render it directly — jsdom's default URL is at "/" and nesting a second
// Router would trip react-router's invariant.

describe('PublicApp', () => {
  it('renders home with links to the three analytics pages', () => {
    render(<App />);
    // Both nav links and home cards carry these names — scope to the nav.
    const nav = screen.getByRole('navigation');
    expect(screen.getByRole('heading', { name: /SOTD Analytics/i })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: /product usage/i })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: /monthly user posts/i })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: /placement/i })).toBeInTheDocument();
  });

  it('has no admin analyzer links', () => {
    render(<App />);
    expect(screen.queryByRole('link', { name: /mismatch/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /brush split/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /catalog validator/i })).not.toBeInTheDocument();
  });
});

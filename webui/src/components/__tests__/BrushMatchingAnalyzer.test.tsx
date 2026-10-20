import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BrushMatchingAnalyzer } from '../BrushMatchingAnalyzer';

const mockAnalyzeResponse = {
  results: [],
  winner: {
    strategy: 'test',
    score: 90,
    matchType: 'exact',
    pattern: 'test',
    scoreBreakdown: { baseScore: 90, modifiers: 0, modifierDetails: [] },
    matchedData: {},
  },
};

describe('BrushMatchingAnalyzer deep link', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAnalyzeResponse,
    }) as jest.Mock;
  });

  it('prefills input and auto-analyzes from ?brush= query param', async () => {
    const brush = 'Declaration Grooming B2 Badger';
    render(
      <MemoryRouter initialEntries={[`/brush-matching-analyzer?brush=${encodeURIComponent(brush)}`]}>
        <BrushMatchingAnalyzer />
      </MemoryRouter>
    );

    expect(screen.getByDisplayValue(brush)).toBeInTheDocument();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.brushString).toBe(brush);
  });

  it('prefers initialBrushString prop over query param', async () => {
    render(
      <MemoryRouter
        initialEntries={[`/brush-matching-analyzer?brush=${encodeURIComponent('From Query')}`]}
      >
        <BrushMatchingAnalyzer initialBrushString='From Prop' autoAnalyze />
      </MemoryRouter>
    );

    expect(screen.getByDisplayValue('From Prop')).toBeInTheDocument();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.brushString).toBe('From Prop');
  });

  it('does not auto-analyze when no brush source is provided', async () => {
    render(
      <MemoryRouter initialEntries={['/brush-matching-analyzer']}>
        <BrushMatchingAnalyzer />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText('Enter brush string to analyze...')).toHaveValue('');
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe('BrushMatchingAnalyzer inputParsing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders Parsed from input fiber and knot size', async () => {
    (global.fetch as jest.Mock) = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...mockAnalyzeResponse,
        winner: {
          ...mockAnalyzeResponse.winner,
          matchedData: { brand: 'Omega', model: 'Boar', fiber: 'Boar' },
        },
        inputParsing: { fiber: 'Boar', knot_size_mm: 26 },
      }),
    });

    render(
      <MemoryRouter
        initialEntries={[
          `/brush-matching-analyzer?brush=${encodeURIComponent('Omega 26mm Boar')}`,
        ]}
      >
        <BrushMatchingAnalyzer />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Parsed from input')).toBeInTheDocument();
    });
    expect(screen.getByTestId('input-parsing-fiber')).toHaveTextContent('Boar');
    expect(screen.getByTestId('input-parsing-knot-size')).toHaveTextContent('26mm');
    expect(screen.queryByTestId('input-parsing-fiber-mismatch')).not.toBeInTheDocument();
  });

  it('shows mismatch hint when parsed fiber differs from matched fiber', async () => {
    (global.fetch as jest.Mock) = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...mockAnalyzeResponse,
        winner: {
          ...mockAnalyzeResponse.winner,
          matchedData: {
            brand: 'Generic',
            model: 'Synthetic',
            fiber: 'Synthetic',
            knot: { brand: 'Generic', model: 'Synthetic', fiber: 'Synthetic' },
          },
        },
        inputParsing: { fiber: 'Boar', knot_size_mm: null },
      }),
    });

    render(
      <MemoryRouter
        initialEntries={[
          `/brush-matching-analyzer?brush=${encodeURIComponent('unknown - stiff bristle brush')}`,
        ]}
      >
        <BrushMatchingAnalyzer />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('input-parsing-fiber')).toHaveTextContent('Boar');
    });
    expect(screen.getByTestId('input-parsing-knot-size')).toHaveTextContent('none');
    expect(screen.getByTestId('input-parsing-fiber-mismatch')).toBeInTheDocument();
    expect(screen.getByTestId('input-parsing-fiber-mismatch')).toHaveTextContent(
      'Parsed fiber (Boar) differs from matched fiber (Synthetic)'
    );
  });
});

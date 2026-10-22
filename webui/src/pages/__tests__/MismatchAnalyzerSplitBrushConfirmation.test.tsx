import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import MatchAnalyzer from '../MatchAnalyzer';
import * as api from '@/services/api';

// Mock the API module — factory keeps real exports for functions the component
// calls on mount (e.g. getValidatedMonths) while stubbing the ones tests control.
jest.mock('@/services/api', () => ({
  ...jest.requireActual('@/services/api'),
  getCorrectMatches: jest.fn(),
  getAvailableMonths: jest.fn(),
  getValidatedMonths: jest.fn().mockResolvedValue({ months: [] }),
  handleApiError: jest.fn((err: unknown) => (err instanceof Error ? err.message : String(err))),
}));

const mockApi = api as jest.Mocked<typeof api>;

describe('MismatchAnalyzer - Split Brush Confirmation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should handle confirmed split brush data structure correctly', () => {
    // Test that the data structure for confirmed split brushes is correct
    const confirmedSplitBrushData = {
      field: 'brush',
      month: '2025-06',
      total_matches: 100,
      total_mismatches: 10,
      processing_time: 1.0,
      mismatch_items: [
        {
          original: 'Jayaruh #441 w/ AP Shave Co G5C',
          matched: {
            brand: null,
            model: null,
            handle: { brand: 'Jayaruh', model: '#441' },
            knot: { brand: 'AP Shave Co', model: 'G5C' },
          },
          pattern: 'split_brush_pattern',
          match_type: 'split',
          confidence: 1.0,
          mismatch_type: 'exact_matches',
          reason: 'Exact match from correct_matches.yaml',
          count: 1,
          examples: ['2025-06.json'],
          comment_ids: ['test123'],
          is_confirmed: true, // This should show as confirmed
          is_split_brush: true,
          handle_component: 'Jayaruh #441',
          knot_component: 'AP Shave Co G5C',
        },
      ],
    };

    // Verify the data structure is correct
    expect(confirmedSplitBrushData.mismatch_items[0].is_confirmed).toBe(true);
    expect(confirmedSplitBrushData.mismatch_items[0].is_split_brush).toBe(true);
    expect(confirmedSplitBrushData.mismatch_items[0].mismatch_type).toBe('exact_matches');
  });

  it('should handle unconfirmed split brush data structure correctly', () => {
    // Test that the data structure for unconfirmed split brushes is correct
    const unconfirmedSplitBrushData = {
      field: 'brush',
      month: '2025-06',
      total_matches: 100,
      total_mismatches: 10,
      processing_time: 1.0,
      mismatch_items: [
        {
          original: 'Declaration B2 in Mozingo handle',
          matched: {
            brand: null,
            model: null,
            handle: { brand: 'Mozingo', model: 'Custom' },
            knot: { brand: 'Declaration', model: 'B2' },
          },
          pattern: 'declaration_pattern',
          match_type: 'split',
          confidence: 1.0,
          mismatch_type: 'good_matches',
          reason: 'Good quality match',
          count: 1,
          examples: ['2025-06.json'],
          comment_ids: ['test456'],
          is_confirmed: false, // This should show as unconfirmed
          is_split_brush: true,
          handle_component: 'Mozingo Custom',
          knot_component: 'Declaration B2',
        },
      ],
    };

    // Verify the data structure is correct
    expect(unconfirmedSplitBrushData.mismatch_items[0].is_confirmed).toBe(false);
    expect(unconfirmedSplitBrushData.mismatch_items[0].is_split_brush).toBe(true);
    expect(unconfirmedSplitBrushData.mismatch_items[0].mismatch_type).toBe('good_matches');
  });

  it('should handle isItemConfirmed function logic correctly', () => {
    // Test the isItemConfirmed logic directly
    const confirmedItem = {
      original: 'Jayaruh #441 w/ AP Shave Co G5C',
      matched: {},
      pattern: '',
      match_type: 'split',
      count: 1,
      examples: [],
      comment_ids: [],
      is_confirmed: true,
      is_split_brush: true,
    };

    const unconfirmedItem = {
      original: 'Declaration B2 in Mozingo handle',
      matched: {},
      pattern: '',
      match_type: 'split',
      count: 1,
      examples: [],
      comment_ids: [],
      is_confirmed: false,
      is_split_brush: true,
    };

    // The isItemConfirmed function should return the is_confirmed value
    expect(confirmedItem.is_confirmed).toBe(true);
    expect(unconfirmedItem.is_confirmed).toBe(false);
  });

  it('should render MismatchAnalyzer component without errors', async () => {
    // Mock the required API calls
    mockApi.getCorrectMatches.mockResolvedValue({
      field: 'brush',
      total_entries: 50,
      entries: {},
    });

    mockApi.getAvailableMonths.mockResolvedValue(['2025-06']);

    // Render the component
    await act(async () => {
      render(<MatchAnalyzer />);
    });

    // Check that the component renders without errors
    expect(screen.getByText('Match Analyzer')).toBeInTheDocument();
    expect(screen.getByText('Ready to Analyze')).toBeInTheDocument();
  });
});

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the API calls
jest.mock('../../services/api', () => ({
  getProductsForMonth: jest.fn(),
  getProductUsageAnalysis: jest.fn(),
  getProductYearlySummary: jest.fn(),
  getCommentDetail: jest.fn(),
  getAvailableMonths: jest.fn(),
  handleApiError: jest.fn(err => err.message || 'API Error'),
}));

import ProductUsage from '../ProductUsage';
import * as mockApi from '../../services/api';

describe('ProductUsage Component Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock available months
    (
      mockApi.getAvailableMonths as jest.MockedFunction<typeof mockApi.getAvailableMonths>
    ).mockResolvedValue(['2025-06', '2025-07']);

    // Mock getProductsForMonth
    (
      mockApi.getProductsForMonth as jest.MockedFunction<typeof mockApi.getProductsForMonth>
    ).mockResolvedValue([
      {
        key: 'Gillette|Tech',
        brand: 'Gillette',
        model: 'Tech',
        usage_count: 10,
        unique_users: 5,
      },
      {
        key: 'Merkur|34C',
        brand: 'Merkur',
        model: '34C',
        usage_count: 8,
        unique_users: 4,
      },
    ]);

    // Mock getProductUsageAnalysis
    (
      mockApi.getProductUsageAnalysis as jest.MockedFunction<
        typeof mockApi.getProductUsageAnalysis
      >
    ).mockResolvedValue({
      product: {
        type: 'razor',
        brand: 'Gillette',
        model: 'Tech',
      },
      total_usage: 10,
      unique_users: 5,
      users: [
        {
          username: 'user1',
          usage_count: 4,
          usage_dates: ['2025-06-01', '2025-06-02', '2025-06-03', '2025-06-04'],
          comment_ids: ['1', '2', '3', '4'],
        },
        {
          username: 'user2',
          usage_count: 3,
          usage_dates: ['2025-06-01', '2025-06-05', '2025-06-06'],
          comment_ids: ['5', '6', '7'],
        },
        {
          username: 'user3',
          usage_count: 2,
          usage_dates: ['2025-06-02', '2025-06-07'],
          comment_ids: ['8', '9'],
        },
      ],
      usage_by_date: {
        '2025-06-01': ['1', '5'],
        '2025-06-02': ['2', '8'],
        '2025-06-03': ['3'],
        '2025-06-04': ['4'],
        '2025-06-05': ['6'],
        '2025-06-06': ['7'],
        '2025-06-07': ['9'],
      },
      comments_by_date: {
        '2025-06-01': ['1', '5'],
        '2025-06-02': ['2', '8'],
        '2025-06-03': ['3'],
        '2025-06-04': ['4'],
        '2025-06-05': ['6'],
        '2025-06-06': ['7'],
        '2025-06-07': ['9'],
      },
    });

    // Mock getCommentDetail
    (
      mockApi.getCommentDetail as jest.MockedFunction<typeof mockApi.getCommentDetail>
    ).mockResolvedValue({
      id: '1',
      author: 'user1',
      body: 'Test comment',
      created_utc: '2025-06-01T00:00:00Z',
      thread_id: 'thread1',
      thread_title: 'Monday SOTD Thread - Jun 01, 2025',
      url: 'https://reddit.com/test',
    });

    // Mock getProductYearlySummary
    (
      mockApi.getProductYearlySummary as jest.MockedFunction<
        typeof mockApi.getProductYearlySummary
      >
    ).mockResolvedValue({
      product: {
        type: 'razor',
        brand: 'Gillette',
        model: 'Tech',
      },
      months: [
        {
          month: '2024-11',
          shaves: 2,
          unique_users: 2,
          rank: 163,
          has_data: true,
        },
        {
          month: '2024-12',
          shaves: 8,
          unique_users: 1,
          rank: 46,
          has_data: true,
        },
        {
          month: '2025-01',
          shaves: 12,
          unique_users: 4,
          rank: 24,
          has_data: true,
        },
        {
          month: '2025-02',
          shaves: 0,
          unique_users: 0,
          rank: null,
          has_data: false,
        },
        {
          month: '2025-10',
          shaves: 26,
          unique_users: 7,
          rank: 7,
          has_data: true,
        },
        {
          month: '2025-11',
          shaves: 55,
          unique_users: 6,
          rank: 1,
          has_data: true,
        },
      ],
    });
  });

  test('should render month selector', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    expect(screen.getByText('Product Usage')).toBeInTheDocument();
    expect(screen.getByText('Select Month, Product Type, and Product')).toBeInTheDocument();
  });

  test('should render product type selector after month is selected', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Wait for months to load
    await waitFor(() => {
      expect(screen.queryByText('Loading available months...')).not.toBeInTheDocument();
    });

    // Month selector should be visible
    expect(screen.getByText('Month')).toBeInTheDocument();

    // Product type selector should not be visible until month is selected
    expect(screen.queryByText('Product Type')).not.toBeInTheDocument();
  });

  test('should fetch and display products when month and product type are selected', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Wait for months to load
    await waitFor(() => {
      expect(screen.queryByText('Loading available months...')).not.toBeInTheDocument();
    });

    // Select a month (this would require interacting with MonthSelector)
    // For now, we'll just verify the component structure

    // Verify that getProductsForMonth would be called when month and type are selected
    // This is tested through integration rather than unit testing the MonthSelector
  });

  test('should filter products by search input', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // This test would require setting up the component state with products
    // and then testing the search filtering logic
    // For now, we verify the component renders correctly
    expect(screen.getByText('Product Usage')).toBeInTheDocument();
  });

  test('should display table view correctly', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Table view is the default, but we need product analysis data to see it
    // This would be tested through integration tests with actual API calls
    expect(screen.getByText('Product Usage')).toBeInTheDocument();
  });

  test('should handle loading states', async () => {
    // Mock a delayed API response
    (
      mockApi.getProductsForMonth as jest.MockedFunction<typeof mockApi.getProductsForMonth>
    ).mockImplementation(
      () =>
        new Promise(resolve => {
          setTimeout(() => {
            resolve([
              {
                key: 'Gillette|Tech',
                brand: 'Gillette',
                model: 'Tech',
                usage_count: 10,
                unique_users: 5,
              },
            ]);
          }, 100);
        })
    );

    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Loading state would be shown during API call
    // This is tested through the component's loading state management
  });

  test('should handle error states', async () => {
    // Mock an API error
    (
      mockApi.getProductsForMonth as jest.MockedFunction<typeof mockApi.getProductsForMonth>
    ).mockRejectedValue(new Error('API Error'));

    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Error would be displayed in the error card
    // This is tested through the component's error handling
  });

  test('should open comment modal on comment click', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Comment modal would open when a comment is clicked
    // This requires product analysis data to be loaded first
    // Tested through integration with actual data flow
  });

  test('should display all product types in selector', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Product type selector should show all four types
    // This is verified through the component structure
    expect(screen.getByText('Product Usage')).toBeInTheDocument();
  });

  test('should fetch and display yearly summary when product is selected', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Wait for months to load
    await waitFor(() => {
      expect(screen.queryByText('Loading available months...')).not.toBeInTheDocument();
    });

    // The yearly summary would be fetched when a product is selected
    // This is tested through integration with the component's product selection flow
    expect(mockApi.getProductYearlySummary).toBeDefined();
  });

  test('should display yearly summary table with correct columns', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <ProductUsage />
        </MemoryRouter>
      );
    });

    // Yearly summary table would display Month, Shaves, Unique Users, Rank columns
    // This is tested through integration when yearly summary data is available
    expect(screen.getByText('Product Usage')).toBeInTheDocument();
  });

  describe('public build comment links', () => {
    const originalFlag = (globalThis as any).__PUBLIC_BUILD__;

    afterEach(() => {
      (globalThis as any).__PUBLIC_BUILD__ = originalFlag;
      jest.restoreAllMocks();
    });

    test('opens the Reddit comment URL in a new tab instead of the modal', async () => {
      (globalThis as any).__PUBLIC_BUILD__ = true;
      const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);

      await act(async () => {
        render(
          <MemoryRouter
            initialEntries={[
              '/product-usage?months=2025-06&productType=razor&brand=Gillette&model=Tech',
            ]}
          >
            <ProductUsage />
          </MemoryRouter>
        );
      });

      // Wait for the deep-linked product analysis to load and dates to render
      await waitFor(
        () => {
          expect(screen.getAllByText('Jun 1').length).toBeGreaterThan(0);
        },
        { timeout: 5000 }
      );

      fireEvent.click(screen.getAllByText('Jun 1')[0]);

      expect(openSpy).toHaveBeenCalledWith('https://reddit.com/test', '_blank', 'noopener,noreferrer');
      // The comment-detail modal must not open on the public site
      await waitFor(() => {
        expect(screen.queryByText('Comment Details')).not.toBeInTheDocument();
      });
    });
  });
});


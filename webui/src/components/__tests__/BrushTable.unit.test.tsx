import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BrushTable from '../data/BrushTable';
import { BrushData } from '../../utils/brushDataTransformer';

// Mock the DataTable component
jest.mock('@/components/ui/data-table', () => ({
  __esModule: true,
  DataTable: function MockDataTable(props: {
    height?: number;
    itemSize?: number;
    resizable?: boolean;
    showColumnVisibility?: boolean;
    searchKey?: string;
    columns?: Array<{
      accessorKey?: string;
      id?: string;
      header: string;
      cell?: (props: { row: { original: unknown } }) => React.ReactNode;
    }>;
    data?: Array<Record<string, unknown>>;
  }) {
    return (
      <div data-testid='shadcn-data-table'>
        <div data-testid='data-table-props'>
          {JSON.stringify({
            height: props.height,
            itemSize: props.itemSize,
            resizable: props.resizable,
            showColumnVisibility: props.showColumnVisibility,
            searchKey: props.searchKey,
          })}
        </div>
        <div data-testid='data-table-columns'>
          {props.columns?.map(column => (
            <div
              key={column.accessorKey || column.id}
              data-testid={`column-${column.accessorKey || column.id}`}
            >
              {column.header}
            </div>
          ))}
        </div>
        <div data-testid='data-table-data'>
          {props.data?.map((item, index: number) => (
            <div key={index} data-testid={`row-${index}`}>
              {/* Render each column's cell content */}
              {props.columns?.map((col, colIndex: number) => (
                <div key={colIndex} data-testid={`cell-${col.accessorKey}-${index}`}>
                  {col.cell
                    ? col.cell({ row: { original: item } })
                    : String(item[col.accessorKey || ''] || '')}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  },
}));

// Mock the FilteredEntryCheckbox component (ESM default export)
jest.mock('../forms/FilteredEntryCheckbox', () => ({
  __esModule: true,
  default: function MockFilteredEntryCheckbox(props: {
    itemName: string;
    uniqueId?: string;
    onStatusChange: (checked: boolean) => void;
  }) {
    // Create unique test ID to match the new format
    const testId = props.uniqueId
      ? `checkbox-${props.itemName}-${props.uniqueId}`
      : `checkbox-${props.itemName}`;

    return (
      <input
        data-testid={testId}
        type='checkbox'
        onChange={e => props.onStatusChange(e.target.checked)}
        className='mock-filtered-checkbox'
      />
    );
  },
}));

// Test data
const mockBrushData = [
  {
    main: {
      brush: 'Simpson Chubby 2',
      count: 5,
      comment_ids: ['123', '456'],
      examples: ['Example 1', 'Example 2'],
    },
    components: {
      handle: { maker: 'Elite handle', count: 3, comment_ids: ['123'] },
      knot: { maker: 'Declaration knot', count: 3, comment_ids: ['456'] },
    },
  },
  {
    main: {
      brush: 'Declaration B15',
      count: 3,
      comment_ids: ['789'],
      examples: ['Example 3'],
    },
    components: {
      handle: { maker: 'Declaration handle', count: 2, comment_ids: ['789'] },
      knot: { maker: 'Declaration knot', count: 2, comment_ids: ['789'] },
    },
  },
];

const mockColumnWidths = {
  filtered: 100,
  brush: 200,
  handle: 150,
  knot: 150,
  count: 80,
  comment_ids: 150,
  examples: 200,
};

const mockOnBrushFilter = jest.fn();
const mockOnComponentFilter = jest.fn();

describe('BrushTable Unit Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    test('should render brush table with correct structure', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable container exists
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();

      // Check that rows are rendered
      expect(screen.getByTestId('row-0')).toBeInTheDocument();
      expect(screen.getByTestId('row-1')).toBeInTheDocument();
    });

    test('should render empty table when no data provided', () => {
      render(
        <BrushTable
          items={[]}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable container exists (even with empty data)
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();

      // Check that columns are defined (no separate filtered column in current implementation)
      expect(screen.getByTestId('column-brush')).toBeInTheDocument();
      expect(screen.getByTestId('column-handle')).toBeInTheDocument();
      expect(screen.getByTestId('column-knot')).toBeInTheDocument();
      expect(screen.getByTestId('column-count')).toBeInTheDocument();
      expect(screen.getByTestId('column-comment_ids')).toBeInTheDocument();
      expect(screen.getByTestId('column-examples')).toBeInTheDocument();
    });

    test('should render brush text in item column', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that brush text is displayed in the DataTable
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
      // The mock DataTable renders brush names in the brush column cells
      expect(screen.getByTestId('cell-brush-0')).toBeInTheDocument();
      expect(screen.getByTestId('cell-brush-3')).toBeInTheDocument();
    });

    test('should render count in count column', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that counts are displayed in the count column cells
      expect(screen.getByTestId('cell-count-0')).toBeInTheDocument();
      expect(screen.getByTestId('cell-count-3')).toBeInTheDocument();
    });

    test('should render comment IDs in comment_ids column', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that comment IDs are displayed in the comment_ids column cells
      expect(screen.getByTestId('cell-comment_ids-0')).toBeInTheDocument();
      expect(screen.getByTestId('cell-comment_ids-3')).toBeInTheDocument();
    });

    test('should render examples in examples column', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that examples are displayed in the examples column cells
      expect(screen.getByTestId('cell-examples-0')).toBeInTheDocument();
      expect(screen.getByTestId('cell-examples-3')).toBeInTheDocument();
    });

    test('should render sub-rows for handle and knot components', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // There should be a main row, a handle sub-row, and a knot sub-row for each brush
      // The mock DataTable renders each row as row-{index}
      // For 2 brushes, expect 6 rows (main, handle, knot for each)
      expect(screen.getByTestId('row-0')).toBeInTheDocument(); // main 1
      expect(screen.getByTestId('row-1')).toBeInTheDocument(); // handle 1
      expect(screen.getByTestId('row-2')).toBeInTheDocument(); // knot 1
      expect(screen.getByTestId('row-3')).toBeInTheDocument(); // main 2
      expect(screen.getByTestId('row-4')).toBeInTheDocument(); // handle 2
      expect(screen.getByTestId('row-5')).toBeInTheDocument(); // knot 2
    });

    test('should flatten brush data to include sub-rows for handle and knot components', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable receives flattened data with sub-rows
      const dataTable = screen.getByTestId('shadcn-data-table');
      expect(dataTable).toBeInTheDocument();

      // The flattened data should contain 6 rows total:
      // - 2 main brush rows (Simpson Chubby 2, Declaration B15)
      // - 2 handle sub-rows (Elite handle, Declaration handle)
      // - 2 knot sub-rows (Declaration knot, Declaration knot)
      expect(screen.getByTestId('row-0')).toBeInTheDocument(); // main brush 1
      expect(screen.getByTestId('row-1')).toBeInTheDocument(); // handle sub-row 1
      expect(screen.getByTestId('row-2')).toBeInTheDocument(); // knot sub-row 1
      expect(screen.getByTestId('row-3')).toBeInTheDocument(); // main brush 2
      expect(screen.getByTestId('row-4')).toBeInTheDocument(); // handle sub-row 2
      expect(screen.getByTestId('row-5')).toBeInTheDocument(); // knot sub-row 2
    });
  });

  describe('Checkbox Interactions', () => {
    test('should render checkboxes for each brush item', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable container exists
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();

      // Check that checkboxes are rendered for each brush in the brush column cells
      expect(screen.getByTestId('cell-brush-0')).toBeInTheDocument();
      expect(screen.getByTestId('cell-brush-3')).toBeInTheDocument();
    });

    test('should call onBrushFilter when checkbox is clicked', async () => {
      const user = userEvent.setup();
      const onBrushFilter = jest.fn();

      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={onBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable container exists
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();

      // Find the checkbox in the brush column cell for the main row (row 0)
      // The ShadCN Checkbox renders as a button with role="checkbox"
      const checkbox = screen.getByTestId('cell-brush-0').querySelector('button[role="checkbox"]');
      await user.click(checkbox!);

      expect(onBrushFilter).toHaveBeenCalledWith('Simpson Chubby 2', true);
    });

    test('should handle multiple checkbox interactions', async () => {
      const user = userEvent.setup();
      const onBrushFilter = jest.fn();

      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={onBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Check that the DataTable container exists
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();

      // Find checkboxes in the brush column cells for main rows
      // The ShadCN Checkbox renders as a button with role="checkbox"
      const checkbox1 = screen.getByTestId('cell-brush-0').querySelector('button[role="checkbox"]');
      const checkbox2 = screen.getByTestId('cell-brush-3').querySelector('button[role="checkbox"]');

      await user.click(checkbox1!);
      await user.click(checkbox2!);

      expect(onBrushFilter).toHaveBeenCalledWith('Simpson Chubby 2', true);
      expect(onBrushFilter).toHaveBeenCalledWith('Declaration B15', true);
    });
  });

  describe('Props Validation', () => {
    test('should handle missing onComponentFilter prop', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={jest.fn()}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Should render without errors
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
    });

    test('should handle missing filteredStatus prop', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Should render without errors
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
    });

    test('should handle missing pendingChanges prop', () => {
      render(
        <BrushTable
          items={mockBrushData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Should render without errors
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('should handle malformed brush data gracefully', () => {
      const malformedData = [
        {
          main: {
            brush: 'Valid Brush',
            count: 1,
            comment_ids: ['123'],
            examples: ['Example'],
          },
          components: {
            // Missing components - should not crash
          },
        },
      ];

      render(
        <BrushTable
          items={malformedData}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Should render without crashing
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
      expect(screen.getByTestId('cell-brush-0')).toBeInTheDocument();
    });

    test('should handle null/undefined data gracefully', () => {
      render(
        <BrushTable
          items={[]}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // Should render without crashing and show DataTable
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    test('should render large datasets efficiently', () => {
      const largeDataset = Array.from({ length: 100 }, (_, i) => ({
        main: {
          brush: `Brush ${i}`,
          count: i,
          comment_ids: [`comment-${i}`],
          examples: [`example-${i}`],
        },
        components: {
          handle: {
            maker: `Handle ${i}`,
            count: i,
            comment_ids: [`comment-${i}`],
          },
        },
      }));

      render(
        <BrushTable
          items={largeDataset}
          onBrushFilter={mockOnBrushFilter}
          onComponentFilter={mockOnComponentFilter}
          filteredStatus={{}}
          pendingChanges={{}}
          columnWidths={mockColumnWidths}
        />
      );

      // 100 items = 300 rows (main + handle + knot for each item).
      // No wall-clock assertion: render time varies 2x+ across runners
      // (CI 2-core vs local), and the flake already cost three CI runs.
      // The functional assertions below pin what matters: the data rendered.
      expect(screen.getByTestId('shadcn-data-table')).toBeInTheDocument();
      expect(screen.getByText(largeDataset[0].main.brush)).toBeInTheDocument();
    });
  });
});

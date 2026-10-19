import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BrushSplitModal from '../BrushSplitModal';
import { BrushSplit } from '@/types/brushSplit';

// Mock the onSave / onDelete functions
const mockOnSave = jest.fn();
const mockOnDelete = jest.fn();
const mockOnClose = jest.fn();

const defaultProps = {
  isOpen: true,
  onClose: mockOnClose,
  original: 'Declaration Grooming B2 Badger',
  onSave: mockOnSave,
  onDelete: mockOnDelete,
};

describe('BrushSplitModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders modal with original brush string', () => {
    render(<BrushSplitModal {...defaultProps} />);

    expect(screen.getByText('Create Brush Split')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Declaration Grooming B2 Badger')).toBeInTheDocument();
  });

  it('shows edit title when existing split is provided', () => {
    const existingSplit: BrushSplit = {
      original: 'Declaration Grooming B2 Badger',
      handle: 'Declaration Grooming',
      knot: 'B2 Badger',
      corrected: false,
      validated_at: null,
      should_not_split: false,
      occurrences: [],
    };

    render(<BrushSplitModal {...defaultProps} existingSplit={existingSplit} />);

    expect(screen.getByText('Edit Brush Split')).toBeInTheDocument();
  });

  it('initializes form with existing split data', () => {
    const existingSplit: BrushSplit = {
      original: 'Declaration Grooming B2 Badger',
      handle: 'Declaration Grooming',
      knot: 'B2 Badger',
      corrected: false,
      validated_at: null,
      should_not_split: false,
      occurrences: [],
    };

    render(<BrushSplitModal {...defaultProps} existingSplit={existingSplit} />);

    expect(screen.getByDisplayValue('Declaration Grooming')).toBeInTheDocument();
    expect(screen.getByDisplayValue('B2 Badger')).toBeInTheDocument();
  });

  it('handles "Don\'t Split" checkbox correctly', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} />);

    const dontSplitCheckbox = screen.getByLabelText(/Don't Split/);
    await act(async () => {
      await user.click(dontSplitCheckbox);
    });

    // Should show high confidence for "Don't Split"
    expect(screen.getByText(/HIGH.*Confidence/)).toBeInTheDocument();
    expect(screen.getByText(/Brush marked as "Don't Split"/)).toBeInTheDocument();
  });

  it('validates delimiter-based splits with high confidence', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} original='Declaration Grooming w/ B2 Badger' />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'Declaration Grooming');
      await user.type(knotInput, 'B2 Badger');
    });

    expect(screen.getByText(/HIGH.*Confidence/)).toBeInTheDocument();
    expect(screen.getByText(/Delimiter split detected/)).toBeInTheDocument();
  });

  it('validates fiber-based splits correctly', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} original='Declaration Grooming B2 Badger' />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'Declaration Grooming');
      await user.type(knotInput, 'B2 Badger');
    });

    expect(screen.getByText(/HIGH.*Confidence/)).toBeInTheDocument();
    expect(screen.getByText(/Fiber-hint split: knot contains fiber indicator/)).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} />);

    const saveButton = screen.getByText('Save Split');
    await user.click(saveButton);

    expect(screen.getByText('Handle field is required')).toBeInTheDocument();
    expect(screen.getByText('Knot field is required')).toBeInTheDocument();
  });

  it('shows validation errors for short components', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'A');
      await user.type(knotInput, 'B');
    });

    expect(screen.getByText('Handle component is too short (<3 characters)')).toBeInTheDocument();
    expect(screen.getByText('Knot component is too short (<3 characters)')).toBeInTheDocument();
  });

  it('calls onSave with correct data when form is valid', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'Declaration Grooming');
      await user.type(knotInput, 'B2 Badger');
    });

    const saveButton = screen.getByText('Save Split');
    await act(async () => {
      await user.click(saveButton);
    });

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          original: 'Declaration Grooming B2 Badger',
          handle: 'Declaration Grooming',
          knot: 'B2 Badger',
          should_not_split: false,
          corrected: false,
        })
      );
    });
  });

  it('calls onClose when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(<BrushSplitModal {...defaultProps} />);

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('handles save errors gracefully', async () => {
    const user = userEvent.setup();
    mockOnSave.mockRejectedValueOnce(new Error('Save failed'));

    render(<BrushSplitModal {...defaultProps} />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'Declaration Grooming');
      await user.type(knotInput, 'B2 Badger');
    });

    const saveButton = screen.getByText('Save Split');
    await act(async () => {
      await user.click(saveButton);
    });

    await waitFor(() => {
      expect(screen.getByText('Save failed')).toBeInTheDocument();
    });
  });

  it('disables save button when form is invalid', async () => {
    render(<BrushSplitModal {...defaultProps} />);

    const saveButton = screen.getByText('Save Split');
    expect(saveButton).toBeDisabled();
  });

  it('shows loading state during save', async () => {
    const user = userEvent.setup();
    mockOnSave.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<BrushSplitModal {...defaultProps} />);

    const handleInput = screen.getByPlaceholderText('e.g., Declaration Grooming');
    const knotInput = screen.getByPlaceholderText('e.g., B2 Badger');

    await act(async () => {
      await user.type(handleInput, 'Declaration Grooming');
      await user.type(knotInput, 'B2 Badger');
    });

    const saveButton = screen.getByText('Save Split');
    await act(async () => {
      await user.click(saveButton);
    });

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();
  });

  describe('Revert to automatic', () => {
    const existingSplit: BrushSplit = {
      original: 'Declaration Grooming B2 Badger',
      handle: 'Declaration Grooming',
      knot: 'B2 Badger',
      corrected: true,
      validated_at: '2025-01-27T14:30:00Z',
      should_not_split: false,
      occurrences: [],
    };

    it('hides Revert to automatic when creating a new split', () => {
      render(<BrushSplitModal {...defaultProps} />);

      expect(screen.queryByText('Revert to automatic')).not.toBeInTheDocument();
    });

    it('shows Revert to automatic when editing an existing split', () => {
      render(<BrushSplitModal {...defaultProps} existingSplit={existingSplit} />);

      expect(screen.getByText('Revert to automatic')).toBeInTheDocument();
    });

    it('calls onDelete when Revert to automatic is confirmed', async () => {
      const user = userEvent.setup();
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      mockOnDelete.mockResolvedValueOnce(undefined);

      render(<BrushSplitModal {...defaultProps} existingSplit={existingSplit} />);

      await act(async () => {
        await user.click(screen.getByText('Revert to automatic'));
      });

      await waitFor(() => {
        expect(confirmSpy).toHaveBeenCalled();
        expect(mockOnDelete).toHaveBeenCalledWith('Declaration Grooming B2 Badger');
      });

      confirmSpy.mockRestore();
    });

    it('does not call onDelete when confirmation is cancelled', async () => {
      const user = userEvent.setup();
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

      render(<BrushSplitModal {...defaultProps} existingSplit={existingSplit} />);

      await act(async () => {
        await user.click(screen.getByText('Revert to automatic'));
      });

      expect(mockOnDelete).not.toHaveBeenCalled();
      confirmSpy.mockRestore();
    });
  });
});

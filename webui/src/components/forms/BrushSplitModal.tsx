import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, CheckCircle, Info, X, Search } from 'lucide-react';
import { BrushSplit } from '@/types/brushSplit';

export interface BrushSplitModalProps {
  isOpen: boolean;
  onClose: () => void;
  original: string;
  existingSplit?: BrushSplit;
  onSave: (split: BrushSplit) => Promise<void>;
  /** Remove override from YAML so default automated parsing applies. */
  onDelete?: (original: string) => Promise<void>;
}

export interface BrushSplitValidationResult {
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
  isValid: boolean;
  errors: string[];
}

export const BrushSplitModal: React.FC<BrushSplitModalProps> = ({
  isOpen,
  onClose,
  original,
  existingSplit,
  onSave,
  onDelete,
}) => {
  const [handle, setHandle] = useState<string>('');
  const [knot, setKnot] = useState<string>('');
  const [shouldNotSplit, setShouldNotSplit] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<BrushSplitValidationResult | null>(null);

  // Initialize form with existing split data or defaults
  useEffect(() => {
    if (existingSplit) {
      setHandle(existingSplit.handle || '');
      setKnot(existingSplit.knot || '');
      setShouldNotSplit(existingSplit.should_not_split);
    } else {
      // Initialize with empty values for new split
      setHandle('');
      setKnot('');
      setShouldNotSplit(false);
    }
    setError(null);
    setValidation(null);
  }, [existingSplit, original]);

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setHandle('');
      setKnot('');
      setShouldNotSplit(false);
      setError(null);
      setValidation(null);
    }
  }, [isOpen]);

  // Handle "Don't Split" checkbox change
  const handleShouldNotSplitChange = (checked: boolean) => {
    setShouldNotSplit(checked);
    if (checked) {
      setHandle('');
      setKnot(original); // Use original as knot when not splitting
    } else {
      setKnot('');
    }
  };

  // Real-time validation
  const validateSplit = useCallback(() => {
    if (shouldNotSplit) {
      setValidation({
        confidence: 'high',
        reasoning: 'Brush marked as "Don\'t Split" - using original text as knot',
        isValid: true,
        errors: [],
      });
      return;
    }

    const errors: string[] = [];
    let confidence: 'high' | 'medium' | 'low' = 'low';
    let reasoning = '';

    // Check for empty fields
    if (!handle.trim()) {
      errors.push('Handle field is required');
    }
    if (!knot.trim()) {
      errors.push('Knot field is required');
    }

    // Check for delimiter-based splits (most reliable)
    if (original.includes(' w/ ') || original.includes(' with ')) {
      confidence = 'high';
      reasoning = 'Delimiter split detected (w/ or with)';
    } else if (original.includes(' / ') || original.includes('/') || original.includes(' - ')) {
      confidence = 'high';
      reasoning = 'Delimiter split detected (/, -, or -)';
    } else {
      // Check for fiber indicators
      const fiberIndicators = ['badger', 'boar', 'synthetic', 'silvertip', 'syn'];
      const handleHasFiber = fiberIndicators.some(indicator =>
        handle.toLowerCase().includes(indicator)
      );
      const knotHasFiber = fiberIndicators.some(indicator =>
        knot.toLowerCase().includes(indicator)
      );

      if (handleHasFiber && !knotHasFiber) {
        confidence = 'high';
        reasoning = 'Fiber-hint split: handle contains fiber indicator';
      } else if (knotHasFiber && !handleHasFiber) {
        confidence = 'high';
        reasoning = 'Fiber-hint split: knot contains fiber indicator';
      } else if (handleHasFiber && knotHasFiber) {
        confidence = 'medium';
        reasoning = 'Fiber-hint split: both components contain fiber indicators';
      } else {
        // Analyze component quality
        const handleQuality = handle.length >= 5 && !handle.match(/^\d+$/);
        const knotQuality = knot.length >= 5 && !knot.match(/^\d+$/);

        if (handleQuality && knotQuality) {
          confidence = 'medium';
          reasoning = 'Unknown split type with good component quality';
        } else {
          confidence = 'low';
          reasoning = 'Unknown split type with poor component quality';
        }
      }
    }

    // Check for very short components
    if (handle.length > 0 && handle.length < 3) {
      errors.push('Handle component is too short (<3 characters)');
    }
    if (knot.length > 0 && knot.length < 3) {
      errors.push('Knot component is too short (<3 characters)');
    }

    setValidation({
      confidence,
      reasoning,
      isValid: errors.length === 0,
      errors,
    });
  }, [original, handle, knot, shouldNotSplit]);

  // Run validation when inputs change
  useEffect(() => {
    validateSplit();
  }, [validateSplit]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validation?.isValid) {
      setError('Please fix validation errors before saving');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const split: BrushSplit = {
        original,
        handle: shouldNotSplit ? null : handle.trim(),
        knot: shouldNotSplit ? original : knot.trim(),
        match_type: existingSplit?.match_type || null,
        corrected: existingSplit ? true : false,
        validated_at: new Date().toISOString(),
        system_handle: existingSplit?.system_handle || null,
        system_knot: existingSplit?.system_knot || null,
        system_confidence: existingSplit?.system_confidence || null,
        system_reasoning: existingSplit?.system_reasoning || null,
        should_not_split: shouldNotSplit,
        occurrences: existingSplit?.occurrences || [],
      };

      await onSave(split);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save brush split');
    } finally {
      setLoading(false);
    }
  };

  const handleRevertToAutomatic = async () => {
    if (!onDelete || !existingSplit) {
      return;
    }

    const confirmed = window.confirm(
      'Remove this override and revert to automatic splitting?\n\n' +
        'This deletes the entry from brush_splits.yaml (manual split or Don\'t Split).'
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      await onDelete(original);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove brush split override');
    } finally {
      setDeleting(false);
    }
  };

  const busy = loading || deleting;

  // Get confidence badge color
  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
      <div className='bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden'>
        {/* Header */}
        <div className='flex items-center justify-between p-4 border-b border-gray-200'>
          <h2 className='text-lg font-semibold text-gray-900'>
            {existingSplit ? 'Edit Brush Split' : 'Create Brush Split'}
          </h2>
          <button
            onClick={onClose}
            className='text-gray-400 hover:text-gray-600 transition-colors'
            aria-label='Close modal'
          >
            <X className='h-5 w-5' />
          </button>
        </div>

        {/* Content */}
        <div className='p-6 overflow-y-auto max-h-[calc(90vh-140px)]'>
          <form onSubmit={handleSubmit} className='space-y-6'>
            {/* Original Brush String */}
            <div className='space-y-2'>
              <div className='flex items-center justify-between gap-2'>
                <label htmlFor='original' className='block text-sm font-medium text-gray-700'>
                  Original Brush String
                </label>
                <Button
                  type='button'
                  variant='outline'
                  size='sm'
                  onClick={() => {
                    window.open(
                      `/brush-matching-analyzer?brush=${encodeURIComponent(original)}`,
                      '_blank',
                      'noopener,noreferrer'
                    );
                  }}
                >
                  <Search className='mr-1.5 h-3.5 w-3.5' />
                  Analyze matching
                </Button>
              </div>
              <Input
                id='original'
                value={original}
                readOnly
                className='bg-gray-50 cursor-text select-text'
              />
              <p className='text-sm text-gray-500'>
                This is the original brush string that needs to be split
              </p>
            </div>

            {/* Don't Split Checkbox */}
            <div className='flex items-center space-x-2'>
              <Checkbox
                id='shouldNotSplit'
                checked={shouldNotSplit}
                onCheckedChange={handleShouldNotSplitChange}
              />
              <label htmlFor='shouldNotSplit' className='text-sm font-medium text-gray-700'>
                Don't Split (use original as single component)
              </label>
            </div>

            {/* Handle and Knot Fields */}
            {!shouldNotSplit && (
              <div className='grid grid-cols-2 gap-4'>
                <div className='space-y-2'>
                  <label htmlFor='handle' className='block text-sm font-medium text-gray-700'>
                    Handle Component
                  </label>
                  <Input
                    id='handle'
                    value={handle}
                    onChange={e => setHandle(e.target.value)}
                    placeholder='e.g., Declaration Grooming'
                    className={
                      validation?.errors.some(e => e.includes('Handle')) ? 'border-red-500' : ''
                    }
                  />
                </div>
                <div className='space-y-2'>
                  <label htmlFor='knot' className='block text-sm font-medium text-gray-700'>
                    Knot Component
                  </label>
                  <Input
                    id='knot'
                    value={knot}
                    onChange={e => setKnot(e.target.value)}
                    placeholder='e.g., B2 Badger'
                    className={
                      validation?.errors.some(e => e.includes('Knot')) ? 'border-red-500' : ''
                    }
                  />
                </div>
              </div>
            )}

            {/* Validation Results */}
            {validation && (
              <div className='space-y-3'>
                <div className='flex items-center gap-2'>
                  <Badge variant='outline' className={getConfidenceColor(validation.confidence)}>
                    {validation.confidence.toUpperCase()} Confidence
                  </Badge>
                  {validation.isValid ? (
                    <CheckCircle className='h-4 w-4 text-green-600' />
                  ) : (
                    <AlertCircle className='h-4 w-4 text-red-600' />
                  )}
                </div>

                <div className='text-sm text-gray-700'>
                  <strong>Reasoning:</strong> {validation.reasoning}
                </div>

                {validation.errors.length > 0 && (
                  <div className='bg-red-50 border border-red-200 rounded-md p-3'>
                    <div className='flex items-center gap-2 mb-2'>
                      <AlertCircle className='h-4 w-4 text-red-600' />
                      <span className='text-sm font-medium text-red-800'>Validation Errors</span>
                    </div>
                    <ul className='list-disc list-inside space-y-1 text-sm text-red-700'>
                      {validation.errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className='bg-red-50 border border-red-200 rounded-md p-3'>
                <div className='flex items-center gap-2'>
                  <AlertCircle className='h-4 w-4 text-red-600' />
                  <span className='text-sm text-red-800'>{error}</span>
                </div>
              </div>
            )}

            {/* Help Text */}
            <div className='bg-blue-50 border border-blue-200 rounded-md p-3'>
              <div className='flex items-start gap-2'>
                <Info className='h-4 w-4 text-blue-600 mt-0.5' />
                <div className='text-sm text-blue-800'>
                  <strong>Tips:</strong>
                  <ul className='list-disc list-inside mt-2 space-y-1'>
                    <li>Use "Don't Split" for brushes that shouldn't be separated</li>
                    <li>
                      Use "Revert to automatic" to remove an override and restore default parsing
                    </li>
                    <li>
                      Use "Analyze matching" to open Brush Matching Analyzer on this string (new
                      tab)
                    </li>
                    <li>Look for delimiters like "w/", "with", "/", or "-"</li>
                    <li>Check for fiber indicators (badger, boar, synthetic)</li>
                    <li>Ensure both components are meaningful and complete</li>
                  </ul>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className='flex items-center justify-between gap-3 p-4 border-t border-gray-200'>
          <div>
            {existingSplit && onDelete && (
              <Button
                type='button'
                variant='outline'
                onClick={handleRevertToAutomatic}
                disabled={busy}
                className='text-red-700 border-red-200 hover:bg-red-50'
              >
                {deleting && (
                  <Loader2 className='mr-2 h-4 w-4 animate-spin' data-testid='delete-spinner' />
                )}
                Revert to automatic
              </Button>
            )}
          </div>
          <div className='flex items-center gap-3'>
            <Button type='button' variant='outline' onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type='submit' disabled={busy || !validation?.isValid} onClick={handleSubmit}>
              {loading && (
                <Loader2 className='mr-2 h-4 w-4 animate-spin' data-testid='loading-spinner' />
              )}
              {existingSplit ? 'Update Split' : 'Save Split'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BrushSplitModal;

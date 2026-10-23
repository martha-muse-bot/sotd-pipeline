import React, { useEffect, useState } from 'react';
import { CommentDetail, saveExtractOverrides } from '../../services/api';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ProductDataTable, { ProductFieldKey } from './ProductDataTable';

interface CommentModalProps {
  comment: CommentDetail | null;
  commentId?: string;
  isOpen: boolean;
  onClose: () => void;
  // New props for multi-comment navigation
  comments?: CommentDetail[];
  currentIndex?: number;
  onNavigate?: (direction: 'prev' | 'next') => Promise<void>;
  // Additional props for lazy loading
  remainingCommentIds?: string[];
  /** Optional: refresh comment after override save */
  onOverridesSaved?: () => void | Promise<void>;
}

const EMPTY_EDIT: Record<ProductFieldKey, string> = {
  razor: '',
  blade: '',
  brush: '',
  soap: '',
};

function initialEditValues(comment: CommentDetail | null): Record<ProductFieldKey, string> {
  const values = { ...EMPTY_EDIT };
  if (!comment?.product_data) {
    return values;
  }
  (Object.keys(EMPTY_EDIT) as ProductFieldKey[]).forEach(key => {
    const field = comment.product_data?.[key];
    values[key] = field?.override_value || '';
  });
  return values;
}

const CommentModal: React.FC<CommentModalProps> = ({
  comment,
  isOpen,
  onClose,
  comments = [],
  currentIndex = 0,
  onNavigate,
  remainingCommentIds = [],
  onOverridesSaved,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<ProductFieldKey, string>>(EMPTY_EDIT);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Compute navigation state unconditionally (before any early return) so hook order is stable
  const totalCommentCount = comments.length + remainingCommentIds.length;
  const hasMultipleComments = totalCommentCount > 1;
  const canGoPrev = hasMultipleComments && currentIndex > 0;
  const canGoNext =
    hasMultipleComments && (currentIndex < comments.length - 1 || remainingCommentIds.length > 0);

  // Reset edit state when comment changes or modal closes
  useEffect(() => {
    if (!isOpen || !comment) {
      setIsEditing(false);
      setSaveMessage(null);
      setSaveError(null);
      return;
    }
    setEditValues(initialEditValues(comment));
    setIsEditing(false);
    setSaveMessage(null);
    setSaveError(null);
  }, [isOpen, comment?.id, comment?.month]);

  // Handle keyboard navigation - must run unconditionally (Rules of Hooks)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return;
      if (isEditing) {
        if (event.key === 'Escape') {
          event.preventDefault();
          setIsEditing(false);
          setEditValues(initialEditValues(comment));
          setSaveError(null);
        }
        return;
      }

      switch (event.key) {
        case 'ArrowLeft':
          if (canGoPrev && onNavigate) {
            event.preventDefault();
            onNavigate('prev');
          }
          break;
        case 'ArrowRight':
          if (canGoNext && onNavigate) {
            event.preventDefault();
            onNavigate('next');
          }
          break;
        case 'Escape':
          event.preventDefault();
          onClose();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isEditing, canGoPrev, canGoNext, onNavigate, onClose, comment]);

  // Early return after all hooks to satisfy Rules of Hooks
  if (!isOpen || !comment) {
    return null;
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const formatBody = (body: string) => {
    // Convert markdown-style formatting to HTML while preserving user intent
    return body
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
      .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
      .replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline">$1</a>'
      ) // Links
      .replace(/\n/g, '<br />'); // Line breaks
  };

  const handleEditChange = (field: ProductFieldKey, value: string) => {
    setEditValues(prev => ({ ...prev, [field]: value }));
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditValues(initialEditValues(comment));
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!comment.month) {
      setSaveError('Comment month is unknown; cannot save extract overrides.');
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      const response = await saveExtractOverrides(comment.month, comment.id, {
        razor: editValues.razor,
        blade: editValues.blade,
        brush: editValues.brush,
        soap: editValues.soap,
      });
      setIsEditing(false);
      setSaveMessage(response.message);
      await onOverridesSaved?.();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : 'Failed to save overrides');
      setSaveError(String(detail));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
      <div className='bg-white rounded-lg shadow-xl max-w-5xl w-full mx-2 sm:mx-4 max-h-[90vh] overflow-hidden flex flex-col'>
        {/* Header */}
        <div className='flex items-center justify-between p-4 border-b border-gray-200'>
          <div className='flex items-center space-x-4'>
            <div>
              <h2 className='text-lg font-semibold text-gray-900'>Comment Details</h2>
              <p className='text-sm text-gray-500'>
                ID: {comment.id} • {formatDate(comment.created_utc)}
                {comment.month && <span className='ml-2 text-gray-400'>• {comment.month}</span>}
                {hasMultipleComments && (
                  <span className='ml-2 text-gray-400'>
                    ({currentIndex + 1} of {totalCommentCount})
                  </span>
                )}
              </p>
            </div>

            {/* Navigation arrows */}
            {hasMultipleComments && !isEditing && (
              <div className='flex items-center space-x-2'>
                <button
                  onClick={() => onNavigate?.('prev')}
                  disabled={!canGoPrev}
                  className='p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500'
                  aria-label='Previous comment'
                >
                  <ChevronLeft className='h-5 w-5' />
                </button>
                <button
                  onClick={() => onNavigate?.('next')}
                  disabled={!canGoNext}
                  className='p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500'
                  aria-label='Next comment'
                >
                  <ChevronRight className='h-5 w-5' />
                </button>
              </div>
            )}
          </div>

          <button
            onClick={onClose}
            className='text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600'
            aria-label='Close modal'
          >
            <svg className='h-6 w-6' fill='none' viewBox='0 0 24 24' stroke='currentColor'>
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M6 18L18 6M6 6l12 12'
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className='p-4 overflow-y-auto flex-1 min-h-0'>
          {/* Comment Info */}
          <div className='mb-4 p-3 bg-gray-50 rounded-lg'>
            <div className='grid grid-cols-1 md:grid-cols-2 gap-3 text-sm'>
              <div>
                <span className='font-medium text-gray-700'>Author:</span>
                <span className='ml-2 text-gray-900'>{comment.author}</span>
              </div>
              <div>
                <span className='font-medium text-gray-700'>Thread:</span>
                <span className='ml-2 text-gray-900'>{comment.thread_title}</span>
              </div>
              <div>
                <span className='font-medium text-gray-700'>Created:</span>
                <span className='ml-2 text-gray-900'>{formatDate(comment.created_utc)}</span>
              </div>
              <div>
                <span className='font-medium text-gray-700'>URL:</span>
                <a
                  href={comment.url}
                  target='_blank'
                  rel='noopener noreferrer'
                  className='ml-2 text-blue-600 hover:text-blue-800 underline'
                >
                  View on Reddit
                </a>
              </div>
            </div>
          </div>

          {/* Comment Body */}
          <div>
            <h3 className='text-sm font-medium text-gray-700 mb-2'>Comment Content:</h3>
            <div
              className='bg-gray-50 p-4 rounded-lg text-sm text-gray-900 whitespace-pre-wrap'
              dangerouslySetInnerHTML={{ __html: formatBody(comment.body) }}
            />
          </div>

          {/* Product Data */}
          <ProductDataTable
            productData={comment.product_data}
            dataSource={comment.data_source}
            isEditing={isEditing}
            editValues={editValues}
            onEditChange={handleEditChange}
          />

          {saveMessage && (
            <p className='mt-3 text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2'>
              {saveMessage}
            </p>
          )}
          {saveError && (
            <p className='mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2'>
              {saveError}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className='flex justify-between items-center p-4 border-t border-gray-200'>
          <div className='flex gap-2'>
            {!isEditing ? (
              <button
                onClick={() => {
                  setEditValues(initialEditValues(comment));
                  setIsEditing(true);
                  setSaveMessage(null);
                  setSaveError(null);
                }}
                className='px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              >
                Edit overrides
              </button>
            ) : (
              <>
                <button
                  onClick={handleSave}
                  disabled={isSaving || !comment.month}
                  className='px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50'
                >
                  {isSaving ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                  className='px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500'
                >
                  Cancel
                </button>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className='px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500'
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommentModal;

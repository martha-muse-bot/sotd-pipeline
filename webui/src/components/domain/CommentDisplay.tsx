import React, { useState } from 'react';
import { Camera } from 'lucide-react';

interface CommentDisplayProps {
  commentIds: string[];
  onCommentClick: (commentId: string) => void;
  commentLoading?: boolean;
  maxDisplay?: number;
  className?: string;
  displayMode?: 'comments' | 'dates';
  dates?: string[];
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
  /** First SOTD header markdown link URL, if any */
  photoUrl?: string;
}

export const CommentDisplay: React.FC<CommentDisplayProps> = ({
  commentIds = [],
  onCommentClick,
  commentLoading = false,
  maxDisplay = 3,
  className = '',
  displayMode = 'comments',
  dates = [],
  expanded: externalExpanded,
  onExpandChange,
  photoUrl,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(false);

  // Use external expanded state if provided, otherwise use internal state
  const isExpanded = externalExpanded !== undefined ? externalExpanded : internalExpanded;

  const handleExpandToggle = () => {
    const newExpanded = !isExpanded;

    // Update internal state if no external control
    if (externalExpanded === undefined) {
      setInternalExpanded(newExpanded);
    }

    // Notify parent of state change
    if (onExpandChange) {
      onExpandChange(newExpanded);
    }
  };

  // Handle empty state
  if (!commentIds || commentIds.length === 0) {
    return <span className='text-sm text-gray-500'>-</span>;
  }

  // Filter out empty comment IDs
  const validCommentIds = commentIds.filter(id => id && id.trim() !== '');

  if (validCommentIds.length === 0) {
    return <span className='text-sm text-gray-500'>-</span>;
  }

  // Format date helper function
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString + 'T00:00:00'); // Add time to avoid timezone issues
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return dateString; // Fallback to original string if parsing fails
    }
  };

  // Determine display text for each item
  const getDisplayText = (index: number): string => {
    if (displayMode === 'dates' && dates && dates[index]) {
      return formatDate(dates[index]);
    }
    return validCommentIds[index];
  };

  // Determine which comments to show
  const displayCount = isExpanded
    ? validCommentIds.length
    : Math.min(maxDisplay, validCommentIds.length);
  const displayComments = validCommentIds.slice(0, displayCount);
  const remainingCount = validCommentIds.length - maxDisplay;
  const canExpand = !isExpanded && remainingCount > 0;

  const handleExpandClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    handleExpandToggle();
  };

  const handleCollapseClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    handleExpandToggle();
  };

  const handlePhotoClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {photoUrl && (
        <a
          href={photoUrl}
          target='_blank'
          rel='noopener noreferrer'
          onClick={handlePhotoClick}
          aria-label='View SOTD photo'
          title='View SOTD photo'
          className='inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 hover:bg-amber-200 hover:text-amber-900'
        >
          <Camera className='h-3.5 w-3.5' aria-hidden='true' />
          <span>Photo</span>
        </a>
      )}

      {displayComments.map((commentId, index) => (
        <button
          key={commentId}
          onClick={() => onCommentClick(commentId)}
          disabled={commentLoading}
          className='block py-0.5 text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left text-sm'
        >
          {getDisplayText(index)}
        </button>
      ))}

      {/* Expand/Collapse controls */}
      {canExpand && (
        <button
          onClick={handleExpandClick}
          className='text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-sm'
        >
          +{remainingCount} more
        </button>
      )}

      {isExpanded && remainingCount > 0 && (
        <button
          onClick={handleCollapseClick}
          className='text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-sm'
        >
          Show less
        </button>
      )}
    </div>
  );
};

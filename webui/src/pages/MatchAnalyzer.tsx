import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { SortingState } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { Filter, Eye, EyeOff } from 'lucide-react';
import MismatchAnalyzerDataTable from '@/components/data/MismatchAnalyzerDataTable';
import GroupedDataTable from '@/components/data/GroupedDataTable';
import AgentReviewPanel from '@/components/data/AgentReviewPanel';
import { SOAP_MASHUP_MATCH_ONLY_NOTE } from '@/utils/soapMashup';
import {
  analyzeMismatch,
  MismatchAnalysisResult,
  CommentDetail,
  CorrectMatchesResponse,
  getCommentDetail,
  getCorrectMatches,
  getQueueErrors,
  markMatchesAsCorrect,
  removeMatchesFromCorrect,
  updateFilteredEntries,
  handleApiError,
  saveBrushSplit,
  deleteBrushSplit,
  loadYamlBrushSplits,
  getSoapGroupByMatched,
  GroupByMatchedResult,
  GroupedDataItem,
  AnalyzerDataItem,
  isGroupedDataItem,
  QueueErrorsResponse,
  QueueErrorEntry,
  VerifiedData,
  ProposedData,
  getVerifiedData,
  getProposedData,
  getValidatedMonths,
} from '@/services/api';

import LoadingSpinner from '@/components/layout/LoadingSpinner';
import ErrorDisplay from '@/components/feedback/ErrorDisplay';
import DecisionToast, {
  PendingDecision,
  DecisionAction,
  UNDO_DELAY_MS,
} from '@/components/feedback/DecisionToast';
import MonthSelector from '@/components/forms/MonthSelector';
import CommentModal from '@/components/domain/CommentModal';
import DeltaMonthsInfoPanel from '@/components/domain/DeltaMonthsInfoPanel';
import BrushSplitModal from '@/components/forms/BrushSplitModal';
import { BrushSplit } from '@/types/brushSplit';
import { structureBrushDataForAPI } from '@/utils/brushDataUtils';
import { calculateDeltaMonths, formatDeltaMonths } from '@/utils/deltaMonths';

const MatchAnalyzer: React.FC = () => {
  const [selectedField, setSelectedField] = useState<string>('razor');
  const [selectedMonths, setSelectedMonths] = useState<string[]>([]);
  const [deltaMonths, setDeltaMonths] = useState<string[]>([]);
  const [threshold, setThreshold] = useState<number>(0);
  const [useEnrichedData, setUseEnrichedData] = useState<boolean>(false);
  const [groupByMatched, setGroupByMatched] = useState<boolean>(false);
  const [displayMode, setDisplayMode] = useState<
    | 'mismatches'
    | 'all'
    | 'unconfirmed'
    | 'regex'
    | 'unmatched'
    | 'intentionally_unmatched'
    | 'complete_brushes'
    | 'matches'
    | 'brand'
    | 'dash_split'
  >('mismatches');
  /** null = no cap (return all grouped rows from the API) */
  const [resultLimit, setResultLimit] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<MismatchAnalysisResult | null>(null);
  const [groupedResults, setGroupedResults] = useState<GroupByMatchedResult | null>(null);
  const [selectedComment, setSelectedComment] = useState<CommentDetail | null>(null);
  const [commentModalOpen, setCommentModalOpen] = useState(false);
  const [commentLoading, setCommentLoading] = useState(false);
  // Multi-comment navigation state
  const [allComments, setAllComments] = useState<CommentDetail[]>([]);
  const [currentCommentIndex, setCurrentCommentIndex] = useState<number>(0);
  const [remainingCommentIds, setRemainingCommentIds] = useState<string[]>([]);

  // Correct matches state
  const [correctMatches, setCorrectMatches] = useState<CorrectMatchesResponse | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [markingCorrect, setMarkingCorrect] = useState(false);
  const [removingCorrect, setRemovingCorrect] = useState(false);
  const [visibleRows, setVisibleRows] = useState<AnalyzerDataItem[]>([]);
  
  // Pending items state - tracks items submitted (optimistic) but not yet processed by queue
  const [pendingItems, setPendingItems] = useState<Set<string>>(new Set());

  // Undo queue - decisions waiting to be committed (delayed API calls)
  const [decisionQueue, setDecisionQueue] = useState<PendingDecision[]>([]);
  const decisionQueueRef = useRef<PendingDecision[]>([]);
  // Keep ref in sync so flush/cleanup can access latest queue without stale closures
  useEffect(() => {
    decisionQueueRef.current = decisionQueue;
  }, [decisionQueue]);

  // Queue errors from GET /api/analysis/queue-errors; failedItemKeys derived from errors
  const [queueErrors, setQueueErrors] = useState<QueueErrorsResponse | null>(null);

  // Reason for marking as unmatched
  const [reasonText, setReasonText] = useState<string>('');
  const [updatingFiltered, setUpdatingFiltered] = useState(false);

  // Agent review mode state
  const [reviewMode, setReviewMode] = useState<'live' | 'agent_review'>('live');
  const [verifiedData, setVerifiedData] = useState<VerifiedData | null>(null);
  const [proposedData, setProposedData] = useState<ProposedData | null>(null);
  const [validatedMonths, setValidatedMonths] = useState<string[]>([]);
  const [agentLoading, setAgentLoading] = useState(false);

  // Brush split modal state
  const [brushSplitModalOpen, setBrushSplitModalOpen] = useState(false);
  const [selectedBrushItem, setSelectedBrushItem] = useState<
    MismatchAnalysisResult['mismatch_items'][0] | null
  >(null);
  const [existingBrushSplit, setExistingBrushSplit] = useState<BrushSplit | undefined>(undefined);
  const [savingBrushSplit, setSavingBrushSplit] = useState(false);

  // YAML brush splits state for lookup
  const [yamlBrushSplits, setYamlBrushSplits] = useState<BrushSplit[]>([]);

  // Keyboard navigation state
  const [activeRowIndex, setActiveRowIndex] = useState<number>(-1);
  const [keyboardNavigationEnabled, setKeyboardNavigationEnabled] = useState<boolean>(false);

  // Table UI state (preserved across analyze operations)
  const [tableSorting, setTableSorting] = useState<SortingState>([]);
  const [tableSearch, setTableSearch] = useState<string>('');
  const [tableUseRegex, setTableUseRegex] = useState<boolean>(false);
  const [matchTypeFilter, setMatchTypeFilter] = useState<Set<string>>(new Set());
  const [brushTypeFilter, setBrushTypeFilter] = useState<Set<string>>(new Set());
  const [strategyFilter, setStrategyFilter] = useState<Set<string>>(new Set());

  // Callback for delta months
  const handleDeltaMonthsChange = useCallback((months: string[]) => {
    setDeltaMonths(months);
  }, []);

  // Clear selections on component mount to ensure clean state
  useEffect(() => {
    setSelectedItems(new Set());
  }, []);

  const loadCorrectMatches = useCallback(async () => {
    try {
      const data = await getCorrectMatches(selectedField);
      console.log('🔍 DEBUG: loadCorrectMatches loaded data:', {
        field: selectedField,
        totalEntries: data.total_entries,
        hasData: !!data,
        dataKeys: data ? Object.keys(data) : [],
      });
      setCorrectMatches(data);
    } catch (err: unknown) {
      console.warn('Failed to load correct matches:', err);
      // Don't show error to user, just log it
    }
  }, [selectedField]);

  const fetchQueueErrors = useCallback(async () => {
    try {
      const data = await getQueueErrors();
      setQueueErrors(data);
    } catch (err: unknown) {
      console.warn('Failed to fetch queue errors:', err);
      setQueueErrors(null);
    }
  }, []);

  const loadYamlBrushSplitsData = useCallback(async () => {
    try {
      const data = await loadYamlBrushSplits();
      setYamlBrushSplits(data.brush_splits);
    } catch (err: unknown) {
      console.warn('Failed to load YAML brush splits:', err);
      // Don't show error to user, just log it
    }
  }, []);

  // --- Undo queue helpers ---

  const enqueueDecision = useCallback(
    (
      action: DecisionAction,
      field: string,
      itemKeys: Set<string>,
      execute: () => Promise<void>
    ) => {
      const id = crypto.randomUUID();
      const createdAt = Date.now();

      const timerId = setTimeout(async () => {
        // Timer expired — commit the decision
        try {
          await execute();
        } catch (err) {
          console.error(`Decision ${id} failed:`, err);
          setError(handleApiError(err));
        }
        // Remove from queue after execution
        setDecisionQueue(prev => prev.filter(d => d.id !== id));
      }, UNDO_DELAY_MS);

      const decision: PendingDecision = {
        id,
        action,
        field,
        itemCount: itemKeys.size,
        itemKeys,
        execute,
        timerId,
        createdAt,
      };

      // Add item keys to pendingItems (optimistic hide)
      setPendingItems(prev => {
        const next = new Set(prev);
        itemKeys.forEach(k => next.add(k));
        return next;
      });

      setDecisionQueue(prev => [...prev, decision]);
      setSelectedItems(new Set());
    },
    []
  );

  const undoDecision = useCallback((id: string) => {
    setDecisionQueue(prev => {
      const decision = prev.find(d => d.id === id);
      if (!decision) return prev;

      // Cancel the timer
      clearTimeout(decision.timerId);

      // Remove item keys from pendingItems (unhide rows)
      setPendingItems(prevPending => {
        const next = new Set(prevPending);
        decision.itemKeys.forEach(k => next.delete(k));
        return next;
      });

      return prev.filter(d => d.id !== id);
    });
  }, []);

  const flushDecisionQueue = useCallback(async () => {
    const queue = decisionQueueRef.current;
    if (queue.length === 0) return;

    // Clear all timers and execute immediately
    for (const decision of queue) {
      clearTimeout(decision.timerId);
      try {
        await decision.execute();
      } catch (err) {
        console.error(`Flush: decision ${decision.id} failed:`, err);
      }
    }

    setDecisionQueue([]);
  }, []);

  // Flush queue on unmount
  useEffect(() => {
    return () => {
      const queue = decisionQueueRef.current;
      for (const decision of queue) {
        clearTimeout(decision.timerId);
        decision.execute().catch(err =>
          console.error(`Cleanup: decision ${decision.id} failed:`, err)
        );
      }
    };
  }, []);

  // Derive failed item keys from queue-errors (field:original.toLowerCase()) for row highlighting
  const failedItemKeys = useMemo(() => {
    if (!queueErrors?.errors?.length) return new Set<string>();
    const keys = new Set<string>();
    for (const e of queueErrors.errors) {
      keys.add(`${e.field}:${(e.original || '').toLowerCase()}`);
    }
    return keys;
  }, [queueErrors?.errors]);

  // Load correct matches when field changes
  useEffect(() => {
    if (selectedField) {
      loadCorrectMatches();
      // Clear selections when field changes to avoid key format mismatches
      setSelectedItems(new Set());
    }
  }, [selectedField, loadCorrectMatches]);

  // Load YAML brush splits on component mount
  useEffect(() => {
    loadYamlBrushSplitsData();
  }, [loadYamlBrushSplitsData]);

  // Fetch queue errors on page load and when field or month changes
  useEffect(() => {
    fetchQueueErrors();
  }, [selectedField, selectedMonths, fetchQueueErrors]);

  // Load validated months on mount
  useEffect(() => {
    getValidatedMonths().then(data => setValidatedMonths(data.months)).catch(() => {});
  }, []);

  // Load agent data handler
  const loadAgentData = useCallback(async (month: string) => {
    setAgentLoading(true);
    try {
      const [verifiedResult, proposedResult] = await Promise.allSettled([
        getVerifiedData(month),
        getProposedData(month),
      ]);
      setVerifiedData(verifiedResult.status === 'fulfilled' ? verifiedResult.value : null);
      setProposedData(proposedResult.status === 'fulfilled' ? proposedResult.value : null);
    } catch (err) {
      console.error('Failed to load agent data:', err);
    } finally {
      setAgentLoading(false);
    }
  }, []);

  // Auto-load agent data when switching to agent_review mode if a month is selected
  useEffect(() => {
    if (reviewMode === 'agent_review' && selectedMonths.length > 0) {
      loadAgentData(selectedMonths[0]);
    }
  }, [reviewMode, selectedMonths, loadAgentData]);

  const handleAnalyze = useCallback(async (overrideGroupByMatched?: boolean) => {
    if (selectedMonths.length === 0) {
      setError('Please select at least one month to analyze');
      return;
    }

    try {
      // Flush any pending undo-queue decisions before re-analyzing
      await flushDecisionQueue();

      setLoading(true);
      setError(null);
      setResults(null);
      setGroupedResults(null);
      setSelectedItems(new Set()); // Clear selections
      // Clear pendingItems so table reflects server state after full load
      setPendingItems(new Set());

      // When delta months are enabled, selectedMonths already contains all months (primary + delta)
      // So we use selectedMonths directly to avoid double-counting
      const allMonths = selectedMonths;

      // Use override value if provided, otherwise use current state
      // Ensure we have a proper boolean value
      const shouldGroupByMatched = overrideGroupByMatched !== undefined 
        ? Boolean(overrideGroupByMatched) 
        : Boolean(groupByMatched);

      // Check if we should use grouped data (soap field with groupByMatched enabled)
      if (selectedField === 'soap' && shouldGroupByMatched) {
        const groupedResult = await getSoapGroupByMatched({
          months: allMonths.join(','),
          group_by_matched: true,
        });
        setGroupedResults(groupedResult);
        // Clear regular results when using grouped data
        setResults(null);
      } else {
        // Always request full data; filtering by display mode is done on the frontend.
        // Passing display_mode to the API would re-fetch a reduced list when switching tabs,
        // causing mismatch count to change (e.g. "Mismatches (3)" → "Mismatches (1)").
        const result = await analyzeMismatch({
          field: selectedField,
          months: allMonths,
          threshold,
          use_enriched_data: useEnrichedData,
          display_mode: 'all',
          ...(resultLimit != null && resultLimit > 0 ? { limit: resultLimit } : {}),
        });

        setResults(result);
        // Clear grouped results when using regular data
        setGroupedResults(null);
      }
    } catch (err: unknown) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
      // Refresh queue errors so panel shows current failures (even if month/field unchanged)
      fetchQueueErrors();
    }
  }, [selectedMonths, selectedField, threshold, useEnrichedData, groupByMatched, resultLimit, fetchQueueErrors, flushDecisionQueue]);

  const handleCommentClick = async (commentId: string, allCommentIds?: string[]) => {
    if (!commentId) return;

    try {
      setCommentLoading(true);

      // Always load just the clicked comment initially for fast response
      // When delta months are enabled, selectedMonths already contains all months (primary + delta)
      const allMonths = selectedMonths;
      const comment = await getCommentDetail(commentId, allMonths);
      setSelectedComment(comment);
      setCurrentCommentIndex(0);
      setCommentModalOpen(true);

      // Store the comment IDs for potential future loading
      if (allCommentIds && allCommentIds.length > 1) {
        setAllComments([comment]); // Start with just the first comment
        // Store the remaining IDs for lazy loading
        setRemainingCommentIds(allCommentIds.filter(id => id !== commentId));
      } else {
        setAllComments([comment]);
        setRemainingCommentIds([]);
      }
    } catch (err: unknown) {
      setError(handleApiError(err));
    } finally {
      setCommentLoading(false);
    }
  };

  const handleCommentNavigation = async (direction: 'prev' | 'next') => {
    if (allComments.length <= 1 && remainingCommentIds.length === 0) return;

    let newIndex = currentCommentIndex;
    if (direction === 'prev') {
      newIndex = Math.max(0, currentCommentIndex - 1);
      setCurrentCommentIndex(newIndex);
      setSelectedComment(allComments[newIndex]);
    } else {
      // Next - check if we need to load more comments
      if (currentCommentIndex === allComments.length - 1 && remainingCommentIds.length > 0) {
        // Load the next comment
        try {
          setCommentLoading(true);
          const nextCommentId = remainingCommentIds[0];
          // When delta months are enabled, selectedMonths already contains all months (primary + delta)
          const allMonths = selectedMonths;
          const nextComment = await getCommentDetail(nextCommentId, allMonths);

          setAllComments(prev => [...prev, nextComment]);
          setRemainingCommentIds(prev => prev.slice(1));
          setCurrentCommentIndex(allComments.length);
          setSelectedComment(nextComment);
        } catch (err: unknown) {
          setError(handleApiError(err));
        } finally {
          setCommentLoading(false);
        }
      } else {
        // Navigate to existing comment
        newIndex = Math.min(allComments.length - 1, currentCommentIndex + 1);
        setCurrentCommentIndex(newIndex);
        setSelectedComment(allComments[newIndex]);
      }
    }
  };

  const handleCloseCommentModal = () => {
    setCommentModalOpen(false);
    setSelectedComment(null);
    setAllComments([]);
    setCurrentCommentIndex(0);
    setRemainingCommentIds([]);
  };

  // Brush split handlers
  const handleBrushSplitClick = (item: MismatchAnalysisResult['mismatch_items'][0]) => {
    setSelectedBrushItem(item);

    // Convert comment_ids to proper occurrence format using comment_sources
    const occurrences: Array<{ file: string; comment_ids: string[] }> = [];

    if (item.comment_ids && item.comment_ids.length > 0) {
      if (item.comment_sources) {
        // Group comment_ids by source file
        const fileGroups: Record<string, string[]> = {};
        for (const commentId of item.comment_ids) {
          const sourceFile = item.comment_sources[commentId];
          if (sourceFile) {
            if (!fileGroups[sourceFile]) {
              fileGroups[sourceFile] = [];
            }
            fileGroups[sourceFile].push(commentId);
          } else {
            // Fallback to current month if no source file mapping
            const fallbackFile = `${selectedMonths[0]}.json`;
            if (!fileGroups[fallbackFile]) {
              fileGroups[fallbackFile] = [];
            }
            fileGroups[fallbackFile].push(commentId);
          }
        }

        // Convert to occurrences format
        for (const [file, commentIds] of Object.entries(fileGroups)) {
          occurrences.push({ file, comment_ids: commentIds });
        }
      } else {
        // Fallback: use current month for all comment_ids
        occurrences.push({
          file: `${selectedMonths[0]}.json`,
          comment_ids: item.comment_ids,
        });
      }
    }

    // Look up existing split from YAML data
    const existingYamlSplit = yamlBrushSplits.find(split => split.original === item.original);

    // Create existing split data if available
    let existingSplit: BrushSplit | undefined = undefined;

    if (existingYamlSplit) {
      // Use existing YAML split data
      existingSplit = {
        ...existingYamlSplit,
        occurrences: occurrences, // Use current occurrences
      };
    } else if (
      (item as any).is_split_brush &&
      ((item as any).handle_component || (item as any).knot_component)
    ) {
      // Use split data from the item itself
      existingSplit = {
        original: item.original,
        handle: (item as any).handle_component || null,
        knot: (item as any).knot_component || null,
        corrected: false,
        validated_at: null,
        should_not_split: false,
        occurrences: occurrences,
      };
    } else {
      // For new splits, create a template with occurrences
      existingSplit = {
        original: item.original,
        handle: null,
        knot: null,
        corrected: false,
        validated_at: null,
        should_not_split: false,
        occurrences: occurrences,
      };
    }
    setExistingBrushSplit(existingSplit);
    setBrushSplitModalOpen(true);
  };

  const handleBrushSplitClose = () => {
    setBrushSplitModalOpen(false);
    setSelectedBrushItem(null);
    setExistingBrushSplit(undefined);
  };

  const handleBrushSplitSave = async (split: BrushSplit) => {
    if (!selectedBrushItem) return;

    try {
      setSavingBrushSplit(true);

      // Call the API to save the brush split
      const response = await saveBrushSplit({
        original: split.original,
        handle: split.handle,
        knot: split.knot || split.original, // Use original as knot if knot is null
        should_not_split: split.should_not_split,
        occurrences: split.occurrences,
      });

      if (response.success) {
        // Close modal after successful save
        handleBrushSplitClose();

        // Refresh YAML brush splits data
        await loadYamlBrushSplitsData();

        // Re-run analysis to get updated data
        if (selectedMonths.length > 0) {
          await handleAnalyze();
        }
      } else {
        setError(`Failed to save brush split: ${response.message}`);
      }
    } catch (error) {
      console.error('Failed to save brush split:', error);
      setError(handleApiError(error));
    } finally {
      setSavingBrushSplit(false);
    }
  };

  const handleBrushSplitDelete = async (original: string) => {
    try {
      setSavingBrushSplit(true);

      const response = await deleteBrushSplit(original);

      if (response.success) {
        handleBrushSplitClose();
        await loadYamlBrushSplitsData();

        if (selectedMonths.length > 0) {
          await handleAnalyze();
        }
      } else {
        setError(`Failed to remove brush split override: ${response.message}`);
        throw new Error(response.message);
      }
    } catch (error) {
      console.error('Failed to delete brush split:', error);
      setError(handleApiError(error));
      throw error;
    } finally {
      setSavingBrushSplit(false);
    }
  };

  const handleMonthChange = (months: string[]) => {
    setSelectedMonths(months);
  };

  const handleItemSelection = useCallback((itemKey: string, selected: boolean) => {
    setSelectedItems(prevSelected => {
      const newSelected = new Set(prevSelected);
      if (selected) {
        newSelected.add(itemKey);
      } else {
        newSelected.delete(itemKey);
      }
      return newSelected;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (!visibleRows.length) return;

    const allKeys = visibleRows.map(item => {
      // Since backend groups by case-insensitive original text, use that as the key
      return `${selectedField}:${item.original.toLowerCase()}`;
    });
    setSelectedItems(new Set(allKeys));
  }, [visibleRows, selectedField]);

  const handleClearSelection = useCallback(() => {
    setSelectedItems(new Set());
  }, []);

  const handleVisibleRowsChange = useCallback((rows: AnalyzerDataItem[]) => {
    setVisibleRows(rows);
    // Reset active row index when visible rows change
    setActiveRowIndex(-1);
  }, []);

  // Memoize item keys to avoid repeated operations
  const visibleItemKeys = useMemo(() => {
    return visibleRows.map(item => {
      if (isGroupedDataItem(item)) {
        // For grouped data, use matched_string as the key
        return `${selectedField}:${item.matched_string?.toLowerCase() || 'unknown'}`;
      } else {
        // For regular data, use original text as the key
        return `${selectedField}:${item.original?.toLowerCase() || 'unknown'}`;
      }
    });
  }, [visibleRows, selectedField]);

  // Count selected items that are currently visible on the page
  const visibleSelectedCount = useMemo(() => {
    if (!visibleRows.length) return 0;

    return visibleItemKeys.filter(key => selectedItems.has(key)).length;
  }, [visibleItemKeys, selectedItems]);

  const handleMarkAsCorrect = async () => {
    if (selectedItems.size === 0) {
      setError('Please select items to mark as correct');
      return;
    }

    try {
      setMarkingCorrect(true);

      let matches: Array<{ original: string; matched: any }> = [];

      // Handle grouped data (soap field with groupByMatched enabled)
      if (groupedResults?.groups) {
        // For grouped data, extract all patterns from selected groups
        const selectedGroups = groupedResults.groups.filter(group => {
          const itemKey = `${selectedField}:${group.matched_string?.toLowerCase() || 'unknown'}`;
          return selectedItems.has(itemKey);
        });

        for (const group of selectedGroups) {
          // Use the actual brand and scent fields from the grouped data
          const brand = group.brand;
          const scent = group.scent;

          // Create matches for all patterns in this group
          for (const pattern of group.all_patterns) {
            matches.push({
              original: pattern.original,
              matched: {
                brand: brand,
                scent: scent,
              },
            });
          }
        }
      } else if (results?.mismatch_items) {
        // Handle regular data (existing logic)
        matches = results.mismatch_items
          .filter(item => {
            const itemKey = `${selectedField}:${item.original.toLowerCase()}`;
            return selectedItems.has(itemKey);
          })
          .map(item => {
            // For brush field, use the shared utility to structure data correctly
            if (selectedField === 'brush' && item.matched) {
              const { data } = structureBrushDataForAPI(item.matched, item.original);
              return {
                original: item.original,
                matched: data,
              };
            }

            // For blade field, include razor format context for correct section placement
            if (selectedField === 'blade' && item.matched) {
              // Ensure the format field is present for correct section placement in correct_matches directory
              // The backend expects a 'format' field to determine which section to place the entry in
              const bladeData = {
                ...item.matched,
                // Use existing format field, but warn if it's missing
                format:
                  item.matched.format ||
                  (() => {
                    console.warn(
                      `Blade match missing format field for "${item.original}". This may cause incorrect placement in correct_matches directory.`
                    );
                    // Try to infer format from other fields or use a more specific default
                    if (item.matched.brand && item.matched.model) {
                      // Check if we can infer the format from the brand/model combination
                      console.warn(
                        `Attempting to infer format from brand: ${item.matched.brand}, model: ${item.matched.model}`
                      );
                    }
                    // For now, use 'DE' as fallback, but this should be fixed in the backend
                    return 'DE';
                  })(),
              };

              // Debug logging for blade format handling
              console.log('Blade match data:', {
                original: item.original,
                originalMatched: item.matched,
                processedMatched: bladeData,
                format: bladeData.format,
                hasFormatField: 'format' in item.matched,
                formatFieldValue: item.matched.format,
              });

              return {
                original: item.original,
                matched: bladeData,
              };
            }

            // For soap field, no mapping needed - brand and scent fields are already correct
            if (selectedField === 'soap' && item.matched) {
              // Soap data already has brand and scent fields, no mapping needed
              const soapData = {
                ...item.matched,
              };

              // Debug logging for soap field data
              console.log('Soap match data:', {
                original: item.original,
                originalMatched: item.matched,
                processedMatched: soapData,
                brand: item.matched.brand,
                scent: item.matched.scent,
              });

              return {
                original: item.original,
                matched: soapData,
              };
            }

            // For non-brush fields, return as-is
            return {
              original: item.original,
              matched: item.matched,
            };
          });
      }

      if (matches.length === 0) {
        setError('No valid matches found to mark as correct');
        return;
      }

      const capturedField = selectedField;
      const capturedItemKeys = new Set(selectedItems);

      enqueueDecision('mark_correct', capturedField, capturedItemKeys, async () => {
        const response = await markMatchesAsCorrect({
          field: capturedField,
          matches,
          force: true,
        });
        if (!response.success) {
          setError(`Failed to queue operation: ${response.message}`);
        }
      });

      setError(null);
    } catch (err: unknown) {
      setError(handleApiError(err));
    } finally {
      setMarkingCorrect(false);
    }
  };

  const handleRemoveFromCorrect = async () => {
    if (selectedItems.size === 0) {
      setError('Please select items to remove from correct matches');
      return;
    }

    try {
      setRemovingCorrect(true);

      let matches: Array<{ original: string; matched: any }> = [];

      // Handle grouped data (soap field with groupByMatched enabled)
      if (groupedResults?.groups) {
        // For grouped data, extract all patterns from selected groups
        const selectedGroups = groupedResults.groups.filter(group => {
          const itemKey = `${selectedField}:${group.matched_string?.toLowerCase() || 'unknown'}`;
          return selectedItems.has(itemKey);
        });

        for (const group of selectedGroups) {
          // Use the actual brand and scent fields from the grouped data
          const brand = group.brand;
          const scent = group.scent;

          // Create matches for all patterns in this group
          for (const pattern of group.all_patterns) {
            matches.push({
              original: pattern.original,
              matched: {
                brand: brand,
                scent: scent,
              },
            });
          }
        }
      } else if (results?.mismatch_items) {
        // Handle regular data (existing logic)
        matches = results.mismatch_items
          .filter(item => {
            const itemKey = `${selectedField}:${item.original.toLowerCase()}`;
            return selectedItems.has(itemKey);
          })
          .map(item => {
            // For brush field, use the shared utility to structure data correctly
            if (selectedField === 'brush' && item.matched) {
              const { data } = structureBrushDataForAPI(item.matched, item.original);
              return {
                original: item.original,
                matched: data,
              };
            }

            // For blade field, include razor format context for correct section placement
            if (selectedField === 'blade' && item.matched) {
              // Ensure the format field is present for correct section placement in correct_matches directory
              // The backend expects a 'format' field to determine which section to place the entry in
              const bladeData = {
                ...item.matched,
                // Use existing format field, but warn if it's missing
                format:
                  item.matched.format ||
                  (() => {
                    console.warn(
                      `Blade match missing format field for "${item.original}" (remove). This may cause incorrect placement in correct_matches directory.`
                    );
                    // Try to infer format from other fields or use a more specific default
                    if (item.matched.brand && item.matched.model) {
                      // Check if we can infer the format from the brand/model combination
                      console.warn(
                        `Attempting to infer format from brand: ${item.matched.brand}, model: ${item.matched.model}`
                      );
                    }
                    // For now, use 'DE' as fallback, but this should be fixed in the backend
                    return 'DE';
                  })(),
              };

              // Debug logging for blade format handling
              console.log('Blade match data (remove):', {
                original: item.original,
                originalMatched: item.matched,
                processedMatched: bladeData,
                format: bladeData.format,
                hasFormatField: 'format' in item.matched,
                formatFieldValue: item.matched.format,
              });

              return {
                original: item.original,
                matched: bladeData,
              };
            }

            // For soap field, no mapping needed - brand and scent fields are already correct
            if (selectedField === 'soap' && item.matched) {
              // Soap data already has brand and scent fields, no mapping needed
              const soapData = {
                ...item.matched,
              };

              // Debug logging for soap field mapping
              console.log('Soap match data (remove):', {
                original: item.original,
                originalMatched: item.matched,
                processedMatched: soapData,
                brandToMaker: item.matched.brand,
                modelToScent: item.matched.model,
              });

              return {
                original: item.original,
                matched: soapData,
              };
            }

            // For non-brush fields, return as-is
            return {
              original: item.original,
              matched: item.matched,
            };
          });
      }

      if (matches.length === 0) {
        setError('No valid matches found to remove from correct matches');
        return;
      }

      const capturedField = selectedField;
      const capturedItemKeys = new Set(selectedItems);

      enqueueDecision('remove_correct', capturedField, capturedItemKeys, async () => {
        const response = await removeMatchesFromCorrect({
          field: capturedField,
          matches,
          force: true,
        });
        if (!response.success) {
          setError(`Failed to queue operation: ${response.message}`);
        }
      });

      setError(null);
    } catch (err: unknown) {
      setError(handleApiError(err));
    } finally {
      setRemovingCorrect(false);
    }
  };

  const handleMarkAsIntentionallyUnmatched = async () => {
    if (selectedItems.size === 0) {
      setError('Please select items to mark as intentionally unmatched');
      return;
    }

    try {
      setUpdatingFiltered(true);

      // Convert selected items to filtered entries format
      const allEntries: Array<{
        name: string;
        action: 'add' | 'remove';
        comment_id: string;
        source: string;
        month: string;
      }> = [];

      if (!results?.mismatch_items) return;

      results.mismatch_items
        .filter(item => {
          const itemKey = `${selectedField}:${item.original.toLowerCase()}`;
          return selectedItems.has(itemKey);
        })
        .forEach(item => {
          if (item.comment_ids && item.comment_ids.length > 0) {
            // Use the first comment_id as representative
            const firstCommentId = item.comment_ids[0];
            if (firstCommentId) {
              // Determine action based on current mismatch_type
              const action = item.mismatch_type === 'intentionally_unmatched' ? 'remove' : 'add';

              allEntries.push({
                name: item.original,
                action,
                comment_id: firstCommentId,
                source: 'user',
                month: selectedMonths[0], // Use first month for backward compatibility
              });
            }
          }
        });

      if (allEntries.length === 0) {
        setError('No valid entries to update');
        return;
      }

      const capturedField = selectedField;
      const capturedItemKeys = new Set(selectedItems);
      const capturedReason = reasonText.trim() || undefined;

      enqueueDecision('mark_unmatched', capturedField, capturedItemKeys, async () => {
        const response = await updateFilteredEntries({
          category: capturedField,
          entries: allEntries,
          reason: capturedReason,
        });
        if (!response.success) {
          setError(`Failed to update filtered entries: ${response.message}`);
        }
      });

      setReasonText('');
      setError(null);
    } catch (err: unknown) {
      setError(handleApiError(err));
    } finally {
      setUpdatingFiltered(false);
    }
  };

  const handleMarkAsIncorrect = async () => {
    if (selectedItems.size === 0) {
      setError('Please select items to mark as incorrect');
      return;
    }

    if (!results?.mismatch_items) return;

    try {
      // Send the complete match data directly
      const matches = results.mismatch_items
        .filter(item => {
          const itemKey = `${selectedField}:${item.original.toLowerCase()}`;
          return selectedItems.has(itemKey);
        })
        .map(item => {
          // For brush field, use the shared utility to structure data correctly
          if (selectedField === 'brush' && item.matched) {
            const { data } = structureBrushDataForAPI(item.matched, item.original);
            return {
              original: item.original,
              matched: data,
            };
          }

          // For blade field, include razor format context for correct section placement
          if (selectedField === 'blade' && item.matched) {
            // Ensure the format field is present for correct section placement in correct_matches.yaml
            // The backend expects a 'format' field to determine which section to place the entry in
            const bladeData = {
              ...item.matched,
              // Use existing format field, but warn if it's missing
              format:
                item.matched.format ||
                (() => {
                  console.warn(
                    `Blade match missing format field for "${item.original}" (incorrect). This may cause incorrect placement in correct_matches directory.`
                  );
                  // Try to infer format from other fields or use a more specific default
                  if (item.matched.brand && item.matched.model) {
                    // Check if we can infer the format from the brand/model combination
                    console.warn(
                      `Attempting to infer format from brand: ${item.matched.brand}, model: ${item.matched.model}`
                    );
                  }
                  // For now, use 'DE' as fallback, but this should be fixed in the backend
                  return 'DE';
                })(),
            };

            // Debug logging for blade format handling
            console.log('Blade match data (incorrect):', {
              original: item.original,
              originalMatched: item.matched,
              processedMatched: bladeData,
              format: bladeData.format,
              hasFormatField: 'format' in item.matched,
              formatFieldValue: item.matched.format,
            });

            return {
              original: item.original,
              matched: bladeData,
            };
          }

          // For soap field, no mapping needed - brand and scent fields are already correct
          if (selectedField === 'soap' && item.matched) {
            // Soap data already has brand and scent fields, no mapping needed
            const soapData = {
              ...item.matched,
            };

            // Debug logging for soap field mapping
            console.log('Soap match data (incorrect):', {
              original: item.original,
              originalMatched: item.matched,
              processedMatched: soapData,
              brandToMaker: item.matched.brand,
              modelToScent: item.matched.model,
            });

            return {
              original: item.original,
              matched: soapData,
            };
          }

          // For non-brush fields, return as-is
          return {
            original: item.original,
            matched: item.matched,
          };
        });

      const capturedField = selectedField;
      const capturedItemKeys = new Set(selectedItems);

      enqueueDecision('mark_incorrect', capturedField, capturedItemKeys, async () => {
        const response = await removeMatchesFromCorrect({
          field: capturedField,
          matches,
          force: true,
        });
        if (response.success) {
          await loadCorrectMatches();
        } else {
          setError(`Failed to mark items as incorrect: ${response.message}`);
        }
      });

      setError(null);
    } catch (err: unknown) {
      setError(handleApiError(err));
    }
  };

  const isItemConfirmed = useCallback((item: MismatchAnalysisResult['mismatch_items'][0]) => {
    // Use the is_confirmed field from the backend
    return item.is_confirmed || false;
  }, []);

  // Helper function to determine if a pattern matches the display mode criteria
  const isPatternMatchType = useCallback(
    (pattern: { match_type: string }, mode: string): boolean => {
      switch (mode) {
        case 'all':
          return true;
        case 'mismatches':
          // Show non-exact patterns (regex, brand, dash_split)
          return pattern.match_type !== 'exact';
        case 'unconfirmed':
          // Show non-exact patterns (regex, brand, dash_split)
          return pattern.match_type !== 'exact';
        case 'regex':
          // Show only regex patterns
          return pattern.match_type === 'regex';
        case 'matches':
          // Show only exact patterns
          return pattern.match_type === 'exact';
        case 'intentionally_unmatched':
          // Not applicable for grouped view (no mismatch_type info)
          return false;
        case 'complete_brushes':
          // Not applicable for soap field
          return false;
        case 'brand':
          // Show only brand match patterns
          return pattern.match_type === 'brand';
        case 'dash_split':
          // Show only dash_split match patterns
          return pattern.match_type === 'dash_split';
        default:
          return true;
      }
    },
    []
  );

  // Memoized Set for O(1) pattern confirmation lookups
  const confirmedPatternsSet = useMemo(() => {
    if (!correctMatches?.entries) {
      return new Set<string>();
    }
    
    // Build a Set of confirmed patterns for O(1) lookups
    // Key format: "brand|scent|normalized_original"
    const set = new Set<string>();
    for (const [brand, brandData] of Object.entries(correctMatches.entries)) {
      if (typeof brandData === 'object' && brandData !== null) {
        for (const [scent, scentData] of Object.entries(brandData)) {
          if (Array.isArray(scentData)) {
            for (const normalizedOriginal of scentData) {
              const key = `${brand}|${scent}|${normalizedOriginal.toLowerCase().trim()}`;
              set.add(key);
            }
          }
        }
      }
    }
    return set;
  }, [correctMatches]);

  // Helper function to check if a pattern is confirmed (in correct_matches)
  const isPatternConfirmed = useCallback(
    (pattern: { original: string }, brand: string, scent: string): boolean => {
      if (!correctMatches?.entries || confirmedPatternsSet.size === 0) {
        return false;
      }
      
      // Patterns in grouped data are already normalized, so we just lowercase and trim
      const normalizedOriginal = pattern.original.toLowerCase().trim();
      
      // Use O(1) Set lookup instead of O(n) Array.some()
      const key = `${brand}|${scent}|${normalizedOriginal}`;
      return confirmedPatternsSet.has(key);
    },
    [correctMatches, confirmedPatternsSet]
  );

  // Helper function to determine if a group has patterns matching the display mode
  const groupHasMatchingPatterns = useCallback(
    (group: GroupedDataItem, mode: string): boolean => {
      return group.all_patterns.some(pattern => isPatternMatchType(pattern, mode));
    },
    [isPatternMatchType]
  );

  // Memoized filtered results for performance
  const filteredResults = useMemo((): AnalyzerDataItem[] => {
    // Handle grouped data (soap field with groupByMatched enabled)
    // Only return grouped data if groupByMatched is true AND we have grouped results
    if (groupByMatched && selectedField === 'soap' && groupedResults?.groups) {
      // Filter groups first based on display mode
      let filteredGroups = groupedResults.groups;
      if (displayMode !== 'all') {
        filteredGroups = filteredGroups.filter(group =>
          groupHasMatchingPatterns(group, displayMode)
        );
      }

      // Filter patterns within groups and recalculate counts
      const result = filteredGroups
        .map(group => {
          // First filter by display mode
          let displayModeFilteredPatterns = group.all_patterns.filter(pattern =>
            isPatternMatchType(pattern, displayMode)
          );
          
          // Then filter out confirmed patterns (unless displayMode is 'matches' or 'all')
          let finalPatterns = displayModeFilteredPatterns;
          if (displayMode !== 'all' && displayMode !== 'matches' && correctMatches?.entries) {
            finalPatterns = displayModeFilteredPatterns.filter(pattern =>
              !isPatternConfirmed(pattern, group.brand, group.scent)
            );
          }
          
          // For 'matches' mode, only show confirmed patterns
          if (displayMode === 'matches' && correctMatches?.entries) {
            finalPatterns = displayModeFilteredPatterns.filter(pattern =>
              isPatternConfirmed(pattern, group.brand, group.scent)
            );
          }

          // Get top patterns from final filtered list
          const filteredTopPatterns = finalPatterns.slice(0, 3);
          const filteredAllPatterns = finalPatterns;

          // If all patterns are filtered out, exclude the group entirely
          if (filteredAllPatterns.length === 0) {
            return null;
          }

          // Recalculate remaining_count based on filtered patterns
          // remaining_count = total patterns - top 3 patterns shown
          const remainingCount = Math.max(0, filteredAllPatterns.length - 3);

          // Recalculate total_count from filtered patterns (not original total)
          const filteredTotalCount = filteredAllPatterns.reduce((sum, pattern) => sum + (pattern.count || 0), 0);

          return {
            matched_string: group.matched_string,
            brand: group.brand,
            scent: group.scent,
            countable: group.countable,
            is_mashup: group.is_mashup,
            sample_type: group.sample_type,
            total_count: filteredTotalCount, // Use recalculated total from filtered patterns
            top_patterns: filteredTopPatterns.slice(0, 3), // Show top 3 filtered patterns
            remaining_count: remainingCount,
            all_patterns: filteredAllPatterns,
            pattern_count: filteredAllPatterns.length, // Updated count
            match_type: group.match_type,
            match_type_breakdown: group.match_type_breakdown,
            is_grouped: true,
          } as GroupedDataItem;
        })
        .filter((group): group is GroupedDataItem => group !== null);
      
      // Filter out pending items from grouped results
      return result.filter(group => {
        const itemKey = `${selectedField}:${group.matched_string?.toLowerCase() || 'unknown'}`;
        return !pendingItems.has(itemKey);
      });
    }

    // Handle regular data (existing logic)
    if (!results?.mismatch_items) {
      return [];
    }

    let filtered: AnalyzerDataItem[];
    switch (displayMode) {
      case 'mismatches':
        // Show only potential mismatches (default behavior)
        filtered = results.mismatch_items.filter(
          item =>
            item.mismatch_type &&
            item.mismatch_type !== 'good_matches' &&
            item.mismatch_type !== 'exact_matches' &&
            item.mismatch_type !== 'intentionally_unmatched' &&
            !isItemConfirmed(item)
        );
        break;

      case 'all':
        // Show all matches (both good and problematic)
        filtered = results.mismatch_items;
        break;

      case 'unconfirmed':
        // Show only unconfirmed matches (not exact or previously confirmed)
        filtered = results.mismatch_items.filter(item => !isItemConfirmed(item));
        break;

      case 'regex':
        // Show only regex matches that need confirmation
        filtered = results.mismatch_items.filter(
          item => item.match_type === 'regex' && !isItemConfirmed(item)
        );
        break;

      case 'intentionally_unmatched':
        filtered = results.mismatch_items.filter(
          item => item.mismatch_type === 'intentionally_unmatched'
        );
        break;

      case 'unmatched':
        // Show only truly unmatched items (no match from catalog)
        filtered = results.mismatch_items.filter(
          item => item.mismatch_type === 'unmatched'
        );
        break;

      case 'complete_brushes':
        // Show only complete brush items (when field is brush)
        filtered = results.mismatch_items.filter(item => (item as any).is_complete_brush === true);
        break;

      case 'matches':
        // Show only confirmed matches (exact and manually confirmed)
        filtered = results.mismatch_items.filter(item => isItemConfirmed(item));
        break;

      case 'brand':
        // Show only brand matches
        filtered = results.mismatch_items.filter(item => item.match_type === 'brand');
        break;

      case 'dash_split':
        // Show only dash_split matches
        filtered = results.mismatch_items.filter(item => item.match_type === 'dash_split');
        break;

      default:
        filtered = results.mismatch_items;
    }
    
    // Filter out pending items from regular results
    return filtered.filter(item => {
      const itemKey = `${selectedField}:${item.original?.toLowerCase() || 'unknown'}`;
      return !pendingItems.has(itemKey);
    });
  }, [
    results?.mismatch_items,
    groupedResults?.groups,
    displayMode,
    isItemConfirmed,
    groupByMatched,
    selectedField,
    groupHasMatchingPatterns,
    isPatternMatchType,
    isPatternConfirmed,
    correctMatches,
    pendingItems,
  ]);

  // Keyboard navigation handlers

  // Container ref for keyboard navigation
  const containerRef = useRef<HTMLDivElement>(null);

  // Enable keyboard navigation when component mounts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle keyboard navigation if focus is on an input field
      const activeElement = document.activeElement;

      if (activeElement) {
        const tagName = activeElement.tagName.toLowerCase();
        const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';
        const isContentEditable = activeElement.getAttribute('contenteditable') === 'true';

        if (isInput || isContentEditable) {
          // If we're in an input field, let it handle all events including space bar
          return; // Let the input field handle all events
        }
      }

      // Only handle keyboard navigation if enabled
      if (!keyboardNavigationEnabled) {
        return;
      }

      switch (event.key) {
        case 'ArrowUp':
          event.preventDefault();
          if (activeRowIndex > 0) {
            setActiveRowIndex(activeRowIndex - 1);
          } else if (visibleRows.length > 0) {
            setActiveRowIndex(0);
          }
          break;
        case 'ArrowDown':
          event.preventDefault();
          if (activeRowIndex >= 0 && activeRowIndex < visibleRows.length - 1) {
            setActiveRowIndex(activeRowIndex + 1);
          } else if (visibleRows.length > 0 && activeRowIndex === -1) {
            setActiveRowIndex(0);
          }
          break;
        case ' ':
          event.preventDefault();
          if (activeRowIndex >= 0 && activeRowIndex < visibleRows.length) {
            const item = visibleRows[activeRowIndex];
            // Use the same key logic as visibleItemKeys to handle both grouped and regular data
            const itemKey = isGroupedDataItem(item)
              ? `${selectedField}:${item.matched_string?.toLowerCase() || 'unknown'}`
              : `${selectedField}:${item.original?.toLowerCase() || 'unknown'}`;
            const isCurrentlySelected = selectedItems.has(itemKey);
            handleItemSelection(itemKey, !isCurrentlySelected);
          }
          break;
        case 'Enter':
          event.preventDefault();
          if (selectedItems.size > 0 && !markingCorrect) {
            handleMarkAsCorrect();
          }
          break;
        case 'Escape':
          setActiveRowIndex(-1);
          setKeyboardNavigationEnabled(false);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    keyboardNavigationEnabled,
    activeRowIndex,
    visibleRows,
    selectedField,
    selectedItems,
    handleItemSelection,
    markingCorrect,
    handleMarkAsCorrect,
  ]);

  // Reset active row when data changes
  useEffect(() => {
    setActiveRowIndex(-1);
  }, [filteredResults]);

  // Enable keyboard navigation when results are available
  useEffect(() => {
    // Check both regular results and grouped results
    if ((results || groupedResults) && filteredResults.length > 0) {
      setKeyboardNavigationEnabled(true);
    } else {
      setKeyboardNavigationEnabled(false);
    }
  }, [results, groupedResults, filteredResults.length]);

  const getDisplayModeCounts = () => {
    // Handle grouped data (soap field with groupByMatched enabled)
    if (groupByMatched && selectedField === 'soap' && groupedResults?.groups) {
      const groups = groupedResults.groups;
      return {
        mismatches: groups.filter(g => groupHasMatchingPatterns(g, 'mismatches')).length,
        all: groups.length,
        unconfirmed: groups.filter(g => groupHasMatchingPatterns(g, 'unconfirmed')).length,
        regex: groups.filter(g => groupHasMatchingPatterns(g, 'regex')).length,
        unmatched: 0,
        intentionally_unmatched: 0,
        matches: groups.filter(g => groupHasMatchingPatterns(g, 'matches')).length,
        complete_brushes: 0,
        brand: groups.filter(g => groupHasMatchingPatterns(g, 'brand')).length,
        dash_split: groups.filter(g => groupHasMatchingPatterns(g, 'dash_split')).length,
      };
    }

    // Handle regular data
    if (!results)
      return {
        mismatches: 0,
        all: 0,
        unconfirmed: 0,
        regex: 0,
        unmatched: 0,
        intentionally_unmatched: 0,
        matches: 0,
        complete_brushes: 0,
        brand: 0,
        dash_split: 0,
      };

    // We always have the full dataset now, so calculate from the returned items
    const returnedItems = results.mismatch_items || [];

    // Debug logging to understand the data structure
    // console.log('Debug: Analyzing data for counts:', {
    //   totalItems: returnedItems.length,
    //   field: results.field,
    //   months: results.months,
    //   sampleItems: returnedItems.slice(0, 3).map(item => ({
    //     original: item.original,
    //     match_type: item.match_type,
    //     mismatch_type: item.mismatch_type,
    //     is_confirmed: item.is_confirmed,
    //     pattern: item.pattern,
    //   })),
    // });

    // Count regex matches specifically
    const regexMatches = returnedItems.filter(item => item.match_type === 'regex');
    const unconfirmedRegexMatches = returnedItems.filter(
      item => item.match_type === 'regex' && !isItemConfirmed(item)
    );

    // console.log('Debug: Regex analysis:', {
    //   totalRegexMatches: regexMatches.length,
    //   unconfirmedRegexMatches: unconfirmedRegexMatches.length,
    //   regexMatchTypes: regexMatches.map(item => ({
    //     original: item.original,
    //     match_type: item.match_type,
    //     is_confirmed: item.is_confirmed,
    //     pattern: item.pattern,
    //   })),
    // });

    // Calculate all counts with detailed logging
    const mismatchesCount = returnedItems.filter(
      item =>
        item.mismatch_type !== 'good_matches' &&
        item.mismatch_type !== 'exact_matches' &&
        item.mismatch_type !== 'intentionally_unmatched' &&
        !isItemConfirmed(item)
    ).length;

    const unconfirmedCount = returnedItems.filter(item => !isItemConfirmed(item)).length;
    const intentionallyUnmatchedCount = returnedItems.filter(
      item => item.mismatch_type === 'intentionally_unmatched'
    ).length;
    const unmatchedCount = returnedItems.filter(
      item => item.mismatch_type === 'unmatched'
    ).length;
    const matchesCount = returnedItems.filter(item => isItemConfirmed(item)).length;
    const completeBrushesCount = returnedItems.filter(
      item => (item as any).is_complete_brush === true
    ).length;
    const brandCount = returnedItems.filter(item => item.match_type === 'brand').length;
    const dashSplitCount = returnedItems.filter(item => item.match_type === 'dash_split').length;

    // Debug logging for count calculations
    // console.log('🔍 DEBUG: Display mode count calculations:', {
    //   totalItems: returnedItems.length,
    //   field: results.field,
    //   months: results.months,
    //   calculatedCounts: {
    //     mismatches: mismatchesCount,
    //     all: returnedItems.length,
    //     unconfirmed: unconfirmedCount,
    //     regex: unconfirmedRegexMatches.length,
    //     intentionally_unmatched: intentionallyUnmatchedCount,
    //     matches: matchesCount,
    //     complete_brushes: completeBrushesCount,
    //   },
    //   mismatchTypeBreakdown: returnedItems.reduce((acc, item) => {
    //     acc[item.mismatch_type || 'unknown'] = (acc[item.mismatch_type || 'unknown'] || 0) + 1;
    //     return acc;
    //   }, {} as Record<string, number>),
    //   confirmedBreakdown: {
    //     confirmed: returnedItems.filter(item => item.is_confirmed).length,
    //     unconfirmed: returnedItems.filter(item => !item.is_confirmed).length,
    //   }
    // });

    return {
      mismatches: mismatchesCount,
      all: returnedItems.length,
      unconfirmed: unconfirmedCount,
      regex: unconfirmedRegexMatches.length,
      unmatched: unmatchedCount,
      intentionally_unmatched: intentionallyUnmatchedCount,
      matches: matchesCount,
      complete_brushes: completeBrushesCount,
      brand: brandCount,
      dash_split: dashSplitCount,
    };
  };

  const getUnmatchedButtonText = useMemo(() => {
    if (visibleSelectedCount === 0) return 'Mark 0 as Unmatched';

    // Count how many visible selected items are already intentionally unmatched
    let addCount = 0;
    let removeCount = 0;

    if (visibleRows.length > 0) {
      visibleRows.forEach((item, index) => {
        const itemKey = visibleItemKeys[index];
        if (selectedItems.has(itemKey)) {
          if (item.mismatch_type === 'intentionally_unmatched') {
            removeCount++;
          } else {
            addCount++;
          }
        }
      });
    }

    if (addCount > 0 && removeCount > 0) {
      return `Add ${addCount}, Remove ${removeCount} from Unmatched`;
    } else if (removeCount > 0) {
      return `Remove ${removeCount} from Unmatched`;
    } else {
      return `Mark ${addCount} as Unmatched`;
    }
  }, [visibleSelectedCount, visibleRows, visibleItemKeys, selectedItems]);

  const shouldShowReasonInput = useMemo(() => {
    if (selectedItems.size === 0) return false;

    // Only show reason input if we're adding items (not removing)
    let hasAddItems = false;

    if (results?.mismatch_items) {
      results.mismatch_items
        .filter((item, index) => {
          const itemKey = `${selectedField}:${index}`;
          return selectedItems.has(itemKey);
        })
        .forEach(item => {
          if (item.mismatch_type !== 'intentionally_unmatched') {
            hasAddItems = true;
          }
        });
    }

    return hasAddItems;
  }, [selectedItems, results?.mismatch_items]);

  return (
      <div ref={containerRef} className='w-full p-4 max-w-full overflow-x-hidden'>
      {/* Controls and Header */}
      <div className='mb-4'>
        <h1 className='text-3xl font-bold text-gray-900 mb-2'>Match Analyzer</h1>
        <p className='text-gray-600 mb-4'>
          Analyze and manage all matches to identify potential catalog conflicts, view confirmed
          entries, and maintain data quality.
        </p>

        {/* Correct Matches Summary */}
        {correctMatches && (
          <div className='bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h3 className='text-lg font-medium text-blue-900'>Correct Matches</h3>
                <p className='text-blue-700'>
                  {correctMatches.total_entries} confirmed matches for {selectedField}
                </p>
              </div>
              <button
                onClick={handleRemoveFromCorrect}
                disabled={selectedItems.size === 0 || removingCorrect}
                className='px-3 py-1 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed'
              >
                {removingCorrect ? 'Removing...' : `Clear ${visibleSelectedCount} Entry`}
              </button>
            </div>
          </div>
        )}

        {/* Enriched Data Info Panel */}
        {useEnrichedData && (
          <div className='bg-green-50 border border-green-200 rounded-lg p-4 mb-4'>
            <div className='flex items-start'>
              <div className='flex-shrink-0'>
                <svg className='h-5 w-5 text-green-400' fill='currentColor' viewBox='0 0 20 20'>
                  <path
                    fillRule='evenodd'
                    d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z'
                    clipRule='evenodd'
                  />
                </svg>
              </div>
              <div className='ml-3'>
                <h3 className='text-sm font-medium text-green-800'>Enriched Data Mode Active</h3>
                <div className='mt-2 text-sm text-green-700'>
                  <p className='mb-2'>
                    You are viewing data from the <strong>enrich phase</strong>, which shows the
                    final results after all refinements have been applied.
                  </p>
                  <p className='mb-2'>
                    <strong>What this means:</strong> Some items that appear as "mismatches" in the
                    match phase are actually correct matches that get refined during the enrich
                    phase. Hover over the "Matched" column to see enrich-phase adjustments.
                  </p>
                  <p>
                    <strong>Tip:</strong> This mode helps distinguish between truly problematic
                    matches and expected enrich-phase corrections.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedField === 'soap' && !useEnrichedData && (
          <div className='bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4'>
            <div className='flex items-start'>
              <div className='flex-shrink-0 text-amber-500 mt-0.5' aria-hidden='true'>
                <svg className='h-5 w-5' fill='currentColor' viewBox='0 0 20 20'>
                  <path
                    fillRule='evenodd'
                    d='M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z'
                    clipRule='evenodd'
                  />
                </svg>
              </div>
              <div className='ml-3'>
                <h3 className='text-sm font-medium text-amber-800'>Matched data only</h3>
                <p className='mt-1 text-sm text-amber-700'>{SOAP_MASHUP_MATCH_ONLY_NOTE}</p>
              </div>
            </div>
          </div>
        )}

        {/* Delta Months Info Panel */}
        <DeltaMonthsInfoPanel selectedMonths={selectedMonths} deltaMonths={deltaMonths} />

        {/* Controls Section - Made responsive */}
        <div className='space-y-4 mb-4'>
          {/* First row - Basic controls */}
          <div className='flex flex-wrap gap-4 items-end'>
            {/* Mode Toggle */}
            <div className='flex items-center gap-2 mr-4'>
              <button
                className={`px-3 py-1 text-sm rounded ${reviewMode === 'live' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
                onClick={() => setReviewMode('live')}
              >
                Live
              </button>
              <button
                className={`px-3 py-1 text-sm rounded ${reviewMode === 'agent_review' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
                onClick={() => setReviewMode('agent_review')}
              >
                Agent Review
              </button>
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <label
                htmlFor='field-select'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Field
              </label>
              <select
                id='field-select'
                value={selectedField}
                onChange={e => setSelectedField(e.target.value)}
                className='w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              >
                <option value='razor'>Razor</option>
                <option value='blade'>Blade</option>
                <option value='brush'>Brush</option>
                <option value='soap'>Soap</option>
              </select>
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <label
                htmlFor='month-selector'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Month
              </label>
              <MonthSelector
                selectedMonths={selectedMonths}
                onMonthsChange={handleMonthChange}
                label='Select Month'
                multiple={true}
                enableDeltaMonths={true}
                onDeltaMonthsChange={handleDeltaMonthsChange}
              />
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <label
                htmlFor='levenshtein-threshold'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Levenshtein Threshold
              </label>
              <input
                id='levenshtein-threshold'
                type='number'
                min='0'
                max='10'
                value={threshold}
                onChange={e => setThreshold(Number(e.target.value))}
                className='w-full sm:w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <label
                htmlFor='result-limit'
                className='block text-sm font-medium text-gray-700 mb-1'
                title='Cap how many grouped rows are returned. Leave empty for no cap.'
              >
                Max rows
              </label>
              <input
                id='result-limit'
                type='number'
                min={1}
                max={100000}
                placeholder='No limit'
                value={resultLimit ?? ''}
                onChange={e => {
                  const raw = e.target.value;
                  if (raw === '') {
                    setResultLimit(null);
                    return;
                  }
                  const n = parseInt(raw, 10);
                  if (Number.isNaN(n)) return;
                  setResultLimit(Math.min(100000, Math.max(1, n)));
                }}
                className='w-full sm:w-28 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <div className='flex items-center gap-2'>
                <input
                  type='checkbox'
                  id='useEnrichedData'
                  checked={useEnrichedData}
                  onChange={e => setUseEnrichedData(e.target.checked)}
                  className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                />
                <label htmlFor='useEnrichedData' className='text-sm text-gray-700'>
                  Use Enriched Data
                </label>
                <div className='relative group'>
                  <button
                    type='button'
                    className='ml-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600'
                    title='Learn about Match vs Enrich phases'
                  >
                    <svg className='h-4 w-4' fill='currentColor' viewBox='0 0 20 20'>
                      <path
                        fillRule='evenodd'
                        d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z'
                        clipRule='evenodd'
                      />
                    </svg>
                  </button>
                  <div className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm max-w-xs'>
                    <div className='font-medium mb-1'>Match vs Enrich Phases:</div>
                    <div className='space-y-1'>
                      <div>
                        <strong>Match Phase:</strong> Initial product identification
                      </div>
                      <div>
                        <strong>Enrich Phase:</strong> Refines matches with additional data
                      </div>
                      <div className='text-gray-600'>
                        Some "mismatches" are actually correct enrich-phase adjustments
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className='min-w-0 flex-1 sm:flex-none'>
              <button
                onClick={() => handleAnalyze()}
                disabled={loading || selectedMonths.length === 0}
                className='w-full sm:w-auto bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed h-10'
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </div>

          {/* Second row - Display Mode buttons */}
          <div className='min-w-0'>
            <label className='block text-sm font-medium text-gray-700 mb-2'>Display Mode</label>
            <div className='flex flex-wrap gap-2'>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('all')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'all' ? 'bg-blue-600 text-white' : ''}`}
                title='Show all matches with mismatch indicators'
              >
                <Eye className='h-4 w-4' />
                All
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'all' ? 'bg-white text-blue-600' : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().all}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show all matches (both good and problematic)
                </span>
              </Button>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('mismatches')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'mismatches' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only potential mismatches that need review'
              >
                <EyeOff className='h-4 w-4' />
                Mismatches
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'mismatches'
                    ? 'bg-white text-blue-600'
                    : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().mismatches}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only problematic matches that need review
                </span>
              </Button>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('unconfirmed')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'unconfirmed' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only unconfirmed matches (not exact or previously confirmed)'
              >
                <Filter className='h-4 w-4' />
                Unconfirmed
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'unconfirmed'
                    ? 'bg-white text-blue-600'
                    : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().unconfirmed}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only unconfirmed matches (not exact or previously confirmed)
                </span>
              </Button>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('regex')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'regex' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only regex matches that need confirmation'
              >
                <Filter className='h-4 w-4' />
                Regex
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'regex' ? 'bg-white text-blue-600' : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().regex}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only regex matches that need confirmation
                </span>
              </Button>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('unmatched')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'unmatched' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only unmatched items (no catalog match)'
              >
                <Filter className='h-4 w-4' />
                Unmatched
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'unmatched'
                    ? 'bg-white text-blue-600'
                    : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().unmatched}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only unmatched items (no catalog match)
                </span>
              </Button>
              <Button
                variant='outline'
                onClick={() => setDisplayMode('intentionally_unmatched')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'intentionally_unmatched' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only intentionally unmatched items'
              >
                <Filter className='h-4 w-4' />
                Intentionally Unmatched
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'intentionally_unmatched'
                    ? 'bg-white text-blue-600'
                    : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().intentionally_unmatched}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only intentionally unmatched items
                </span>
              </Button>
              {/* Matches filter - show confirmed entries */}
              <Button
                variant='outline'
                onClick={() => setDisplayMode('matches')}
                className={`flex items-center gap-1 text-sm relative group ${displayMode === 'matches' ? 'bg-blue-600 text-white' : ''}`}
                title='Show only confirmed matches (exact and manually confirmed)'
              >
                <Filter className='h-4 w-4' />
                Matches
                <span
                  className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'matches'
                    ? 'bg-white text-blue-600'
                    : 'bg-gray-100 text-gray-700'
                    }`}
                >
                  {getDisplayModeCounts().matches}
                </span>
                <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                  Show only confirmed matches (exact and manually confirmed)
                </span>
              </Button>
              {/* Brand button - only show if there are brand matches */}
              {getDisplayModeCounts().brand > 0 && (
                <Button
                  variant='outline'
                  onClick={() => setDisplayMode('brand')}
                  className={`flex items-center gap-1 text-sm relative group ${displayMode === 'brand' ? 'bg-blue-600 text-white' : ''}`}
                  title='Show only brand matches'
                >
                  <Filter className='h-4 w-4' />
                  Brand
                  <span
                    className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'brand' ? 'bg-white text-blue-600' : 'bg-gray-100 text-gray-700'}`}
                  >
                    {getDisplayModeCounts().brand}
                  </span>
                  <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                    Show only brand matches
                  </span>
                </Button>
              )}
              {/* Dash Split button - only show if there are dash_split matches */}
              {getDisplayModeCounts().dash_split > 0 && (
                <Button
                  variant='outline'
                  onClick={() => setDisplayMode('dash_split')}
                  className={`flex items-center gap-1 text-sm relative group ${displayMode === 'dash_split' ? 'bg-blue-600 text-white' : ''}`}
                  title='Show only dash_split matches'
                >
                  <Filter className='h-4 w-4' />
                  Dash Split
                  <span
                    className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'dash_split' ? 'bg-white text-blue-600' : 'bg-gray-100 text-gray-700'}`}
                  >
                    {getDisplayModeCounts().dash_split}
                  </span>
                  <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                    Show only dash_split matches
                  </span>
                </Button>
              )}
              {/* Complete Brushes filter - only show when field is brush */}
              {selectedField === 'brush' && (
                <Button
                  variant='outline'
                  onClick={() => setDisplayMode('complete_brushes')}
                  className={`flex items-center gap-1 text-sm relative group ${displayMode === 'complete_brushes' ? 'bg-blue-600 text-white' : ''}`}
                  title='Show only complete brush items (single products)'
                >
                  <Filter className='h-4 w-4' />
                  Complete Brushes
                  <span
                    className={`ml-1 px-1.5 py-0.5 text-xs rounded-full ${displayMode === 'complete_brushes'
                      ? 'bg-white text-blue-600'
                      : 'bg-gray-100 text-gray-700'
                      }`}
                  >
                    {getDisplayModeCounts().complete_brushes}
                  </span>
                  <span className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm'>
                    Show only complete brush items (single products)
                  </span>
                </Button>
              )}
            </div>
          </div>

          {/* Group by Matched toggle - only show when soap field is selected */}
          {selectedField === 'soap' && (
            <div className='min-w-0'>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Grouping Options
              </label>
              <div className='flex items-center gap-2'>
                <input
                  type='checkbox'
                  id='groupByMatched'
                  checked={groupByMatched}
                  onChange={e => {
                    const newValue = e.target.checked;
                    setGroupByMatched(newValue);
                    // If enabling groupByMatched and we have months selected, automatically trigger analysis
                    // Pass the new value directly to avoid React state update timing issues
                    if (newValue && selectedMonths.length > 0 && selectedField === 'soap') {
                      // Clear existing results to avoid showing wrong data
                      setResults(null);
                      setGroupedResults(null);
                      // Trigger analysis automatically with the new value
                      setTimeout(() => {
                        handleAnalyze(newValue);
                      }, 0);
                    } else if (!newValue) {
                      // When unchecking, clear grouped results and trigger regular analysis
                      setGroupedResults(null);
                      if (selectedMonths.length > 0 && selectedField === 'soap') {
                        setTimeout(() => {
                          handleAnalyze(false);
                        }, 0);
                      }
                    }
                  }}
                  className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  aria-label='Group results by matched string (brand + scent) instead of original string'
                />
                <label htmlFor='groupByMatched' className='text-sm text-gray-700'>
                  Group by Matched
                </label>
                <div className='relative group'>
                  <button
                    type='button'
                    className='ml-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600'
                    title='Learn about Group by Matched'
                  >
                    <svg className='h-4 w-4' fill='currentColor' viewBox='0 0 20 20'>
                      <path
                        fillRule='evenodd'
                        d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z'
                        clipRule='evenodd'
                      />
                    </svg>
                  </button>
                  <div className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10 shadow-sm max-w-xs'>
                    <div className='font-medium mb-1'>Group by Matched:</div>
                    <div className='space-y-1'>
                      <div>
                        <strong>Enabled:</strong> Groups results by brand + scent combinations
                      </div>
                      <div>
                        <strong>Disabled:</strong> Groups results by original input strings
                      </div>
                      <div className='text-gray-600'>
                        Helps identify which scent-specific regexes to add to the catalog
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className='mb-4'>
          <ErrorDisplay error={error} onRetry={() => setError(null)} />
        </div>
      )}

      {/* Loading Spinner */}
      {loading && (
        <div className='mb-4'>
          <LoadingSpinner message='Analyzing mismatches...' />
        </div>
      )}

      {/* Correct matches queue errors panel */}
      {queueErrors && queueErrors.errors.length > 0 && (
        <div className='mb-4 rounded-lg border border-amber-200 bg-amber-50'>
          <details className='group' open={queueErrors.errors.length > 0}>
            <summary className='cursor-pointer list-none px-4 py-2 font-medium text-amber-900'>
              Correct matches queue errors ({queueErrors.source})
            </summary>
            <div className='border-t border-amber-200 px-4 py-3'>
              <ul className='space-y-2 text-sm'>
                {queueErrors.errors.map((e: QueueErrorEntry, i: number) => (
                  <li key={i} className='rounded bg-white/80 p-2'>
                    <span className='font-medium'>{e.field}</span>
                    {e.original && (
                      <span className='ml-1 text-gray-700'>
                        &quot;{e.original}&quot;
                      </span>
                    )}
                    {e.retry_count > 0 && (
                      <span className='ml-1 text-amber-700'>
                        (retry {e.retry_count})
                      </span>
                    )}
                    <div className='mt-1 text-red-700'>{e.error || e.message}</div>
                    {e.completed_at > 0 && (
                      <div className='mt-0.5 text-xs text-gray-500'>
                        {new Date(e.completed_at * 1000).toLocaleString()}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      )}

      {reviewMode === 'live' ? (
      <>
      {/* Results Table */}
      {(results || groupedResults) && (
        <div className='bg-white rounded-lg shadow'>
          <div className='px-6 py-4 border-b border-gray-200'>
            <div className='flex items-center justify-between'>
              <div className='min-w-0 flex-1'>
                <h3 className='text-lg font-medium text-gray-900'>Analysis Results</h3>
                <div className='mt-2 text-sm text-gray-600 flex flex-wrap gap-4'>
                  <span className='whitespace-nowrap'>
                    Field: <span className='font-medium'>{selectedField}</span>
                  </span>
                  <span className='whitespace-nowrap'>
                    Month{selectedMonths.length > 1 ? 's' : ''}:{' '}
                    <span className='font-medium'>{selectedMonths.length > 1 ? 'Multiple' : selectedMonths[0] || ''}</span>
                  </span>
                  {groupByMatched && selectedField === 'soap' && groupedResults ? (
                    <>
                      <span className='whitespace-nowrap'>
                        Total Groups:{' '}
                        <span className='font-medium'>{groupedResults.total_groups}</span>
                      </span>
                      <span className='whitespace-nowrap'>
                        Total Matches:{' '}
                        <span className='font-medium'>{groupedResults.total_matches}</span>
                      </span>
                      <span className='whitespace-nowrap'>
                        Grouping: <span className='font-medium'>By Matched String</span>
                      </span>
                    </>
                  ) : (
                    <>
                      <span className='whitespace-nowrap'>
                        Total Matches:{' '}
                        <span className='font-medium'>{results?.mismatch_items?.length || 0}</span>
                      </span>
                      <span className='whitespace-nowrap'>
                        Total Mismatches:{' '}
                        <span className='font-medium'>
                          {
                            (results?.mismatch_items || []).filter(
                              item =>
                                item.mismatch_type !== 'good_matches' &&
                                item.mismatch_type !== 'exact_matches' &&
                                item.mismatch_type !== 'intentionally_unmatched'
                            ).length
                          }
                        </span>
                      </span>
                      <span className='whitespace-nowrap'>
                        Processing Time:{' '}
                        <span className='font-medium'>{results?.processing_time?.toFixed(2)}s</span>
                      </span>
                    </>
                  )}
                  <span className='whitespace-nowrap'>
                    Displayed: <span className='font-medium'>{filteredResults.length}</span>
                  </span>
                </div>
                {/* Keyboard Navigation Indicator */}
                {keyboardNavigationEnabled && (
                  <div className='mt-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded border border-blue-200'>
                    ⌨️ Keyboard Navigation Active: Use ↑↓ to navigate, Space to select, Esc to exit
                  </div>
                )}
              </div>

              {/* Bulk Actions */}
              {filteredResults.length > 0 && (
                <div className='flex flex-wrap gap-2 min-w-0'>
                  <button
                    onClick={handleSelectAll}
                    className='px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 whitespace-nowrap'
                  >
                    Select All
                  </button>
                  <button
                    onClick={handleClearSelection}
                    className='px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 whitespace-nowrap'
                  >
                    Clear Selection
                  </button>
                  <button
                    onClick={handleMarkAsCorrect}
                    disabled={selectedItems.size === 0 || markingCorrect}
                    className='px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap'
                  >
                    {markingCorrect ? 'Marking...' : `Mark ${visibleSelectedCount} as Correct`}
                  </button>
                  <button
                    onClick={handleMarkAsIntentionallyUnmatched}
                    disabled={selectedItems.size === 0 || updatingFiltered}
                    className='px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap'
                  >
                    {updatingFiltered ? 'Updating...' : getUnmatchedButtonText}
                  </button>
                  {/* Only show Mark as Incorrect when viewing confirmed matches */}
                  {displayMode === 'matches' && (
                    <button
                      onClick={handleMarkAsIncorrect}
                      disabled={selectedItems.size === 0}
                      className='px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap'
                    >
                      Mark {visibleSelectedCount} as Incorrect
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Reason Input for Unmatched - Only show when adding items */}
          {selectedItems.size > 0 && shouldShowReasonInput && (
            <div className='px-6 py-3 bg-gray-50 border-t border-gray-200'>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Reason for marking as unmatched (optional)
              </label>
              <input
                type='text'
                value={reasonText}
                onChange={e => setReasonText(e.target.value)}
                placeholder='e.g., not a real product, joke, spam...'
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm'
              />
            </div>
          )}

          <div className='p-6'>
            {filteredResults.length > 0 ? (
              // Use GroupedDataTable for grouped view, MismatchAnalyzerDataTable for normal view
              // Only use GroupedDataTable if we actually have grouped data (groupedResults?.groups exists)
              (() => {
                // Check if we have actual grouped data before using GroupedDataTable
                const hasGroupedData = groupedResults?.groups && groupedResults.groups.length > 0;
                const shouldUseGrouped = groupByMatched && selectedField === 'soap' && hasGroupedData;
                
                return shouldUseGrouped ? (
                  <GroupedDataTable
                    key={`grouped-${displayMode}-${selectedField}`}
                    data={filteredResults as GroupedDataItem[]}
                    field={selectedField}
                    onCommentClick={handleCommentClick}
                    commentLoading={commentLoading}
                    selectedItems={selectedItems}
                    onItemSelection={handleItemSelection}
                    isItemConfirmed={isItemConfirmed}
                    onVisibleRowsChange={handleVisibleRowsChange}
                    onBrushSplitClick={handleBrushSplitClick}
                    activeRowIndex={activeRowIndex}
                    keyboardNavigationEnabled={keyboardNavigationEnabled}
                    sorting={tableSorting}
                    onSortingChange={setTableSorting}
                    globalFilter={tableSearch}
                    onGlobalFilterChange={setTableSearch}
                    useRegexMode={tableUseRegex}
                    onUseRegexModeChange={setTableUseRegex}
                    failedItemKeys={failedItemKeys}
                  />
                ) : (
                <MismatchAnalyzerDataTable
                  key={`match-${displayMode}-${selectedField}`}
                  data={filteredResults}
                  field={selectedField}
                  onCommentClick={handleCommentClick}
                  commentLoading={commentLoading}
                  selectedItems={selectedItems}
                  onItemSelection={handleItemSelection}
                  isItemConfirmed={isItemConfirmed}
                  onVisibleRowsChange={handleVisibleRowsChange}
                  matched_data_map={results?.matched_data_map}
                  onBrushSplitClick={handleBrushSplitClick}
                  activeRowIndex={activeRowIndex}
                  keyboardNavigationEnabled={keyboardNavigationEnabled}
                  sorting={tableSorting}
                  onSortingChange={setTableSorting}
                  globalFilter={tableSearch}
                  onGlobalFilterChange={setTableSearch}
                  useRegexMode={tableUseRegex}
                  onUseRegexModeChange={setTableUseRegex}
                  matchTypeFilter={matchTypeFilter}
                  onMatchTypeFilterChange={setMatchTypeFilter}
                  brushTypeFilter={brushTypeFilter}
                  onBrushTypeFilterChange={setBrushTypeFilter}
                  strategyFilter={strategyFilter}
                  onStrategyFilterChange={setStrategyFilter}
                  failedItemKeys={failedItemKeys}
                />
                );
              })()
            ) : (
              <div className='text-center py-8'>
                <div className='text-green-600 text-4xl mb-2'>✅</div>
                <h3 className='text-lg font-medium text-gray-900 mb-2'>No Items Found</h3>
                <p className='text-gray-600'>No items match the current display mode criteria.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ready State */}
      {!loading && !results && !groupedResults && !error && (
        <div className='bg-white rounded-lg shadow p-6'>
          <div className='text-center py-8'>
            <div className='text-gray-400 text-6xl mb-4'>🔍</div>
            <h3 className='text-lg font-medium text-gray-900 mb-2'>Ready to Analyze</h3>
            <p className='text-gray-600'>
              Select a month and field, then click &quot;Analyze&quot; to begin match analysis.
            </p>
          </div>
        </div>
      )}
      </>
      ) : (
        <AgentReviewPanel
          verifiedData={verifiedData}
          proposedData={proposedData}
          loading={agentLoading}
          month={selectedMonths[0] || ''}
          field={selectedField}
          onDataRefresh={() => {
            if (selectedMonths.length > 0) {
              loadAgentData(selectedMonths[0]);
            }
          }}
        />
      )}

      {/* Comment Modal */}
      {selectedComment && (
        <CommentModal
          comment={selectedComment}
          isOpen={commentModalOpen}
          onClose={handleCloseCommentModal}
          comments={allComments}
          currentIndex={currentCommentIndex}
          onNavigate={handleCommentNavigation}
          remainingCommentIds={remainingCommentIds}
        />
      )}

      {/* Brush Split Modal */}
      {selectedBrushItem && (
        <BrushSplitModal
          isOpen={brushSplitModalOpen}
          onClose={handleBrushSplitClose}
          original={selectedBrushItem.original}
          existingSplit={existingBrushSplit}
          onSave={handleBrushSplitSave}
          onDelete={
            yamlBrushSplits.some(s => s.original === selectedBrushItem.original)
              ? handleBrushSplitDelete
              : undefined
          }
        />
      )}

      {/* Undo Decision Toast Stack */}
      <DecisionToast decisions={decisionQueue} onUndo={undoDecision} />
    </div>
  );
};

export default MatchAnalyzer;

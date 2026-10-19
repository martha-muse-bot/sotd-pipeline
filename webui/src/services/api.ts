import axios from 'axios';
import { BrushSplit } from '@/types/brushSplit';
import { Product, ProductUsageAnalysis, ProductYearlySummary } from '@/types/productUsage';

// Use different base URL for tests vs development
const API_BASE_URL =
  process.env.NODE_ENV === 'test'
    ? 'http://localhost:8000/api' // Direct connection for tests
    : '/api'; // Proxy for development

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    Pragma: 'no-cache',
    Expires: '0',
  },
});

// Add cache-busting interceptor to all requests
api.interceptors.request.use(config => {
  // Add timestamp to prevent caching
  const separator = config.url?.includes('?') ? '&' : '?';
  config.url = `${config.url}${separator}_t=${Date.now()}`;
  return config;
});

// Health check
export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
};

// File system operations
export interface MonthData {
  month: string;
  total_shaves: number;
  unique_shavers: number;
  included_months: string[];
  missing_months: string[];
}

export const getAvailableMonths = async (): Promise<string[]> => {
  try {
    const response = await api.get('/files/available-months');
    return response.data.months;
  } catch (error) {
    console.error('Failed to fetch available months:', error);
    throw error;
  }
};

export const getMonthData = async (month: string): Promise<MonthData> => {
  try {
    const response = await api.get(`/files/month/${month}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch data for month ${month}:`, error);
    throw error;
  }
};

// Catalog operations
export interface CatalogInfo {
  name: string;
  path: string;
  size: number;
  last_modified: string;
}

export const getCatalogs = async (): Promise<CatalogInfo[]> => {
  try {
    const response = await api.get('/catalogs/');
    return response.data.catalogs;
  } catch (error) {
    console.error('Failed to fetch catalogs:', error);
    throw error;
  }
};

export const getCatalogContent = async (catalogName: string): Promise<Record<string, unknown>> => {
  try {
    const response = await api.get(`/catalogs/${catalogName}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch catalog ${catalogName}:`, error);
    throw error;
  }
};

// Comment operations
export interface ProductFieldData {
  original: string;
  normalized?: string | null;
  matched: Record<string, any> | null;
  enriched: Record<string, any> | null;
  match_type?: string;
  pattern?: string;
  overridden?: string | null;
  override_value?: string | null;
  override_pending?: boolean;
}

export interface CommentProductData {
  razor?: ProductFieldData;
  blade?: ProductFieldData;
  brush?: ProductFieldData;
  soap?: ProductFieldData;
}

export interface CommentDetail {
  id: string;
  author: string;
  body: string;
  created_utc: string;
  thread_id: string;
  thread_title: string;
  url: string;
  month?: string;
  product_data?: CommentProductData;
  data_source?: 'enriched' | 'matched';
}

export interface ExtractOverrideResponse {
  success: boolean;
  message: string;
  month: string;
  comment_id: string;
  fields: Record<string, string>;
}

export const getCommentDetail = async (
  commentId: string,
  months: string[]
): Promise<CommentDetail> => {
  try {
    const monthsParam = months.join(',');
    const response = await api.get(`/analysis/comment/${commentId}?months=${monthsParam}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch comment ${commentId}:`, error);
    throw error;
  }
};

export const saveExtractOverrides = async (
  month: string,
  commentId: string,
  fields: {
    razor?: string | null;
    blade?: string | null;
    brush?: string | null;
    soap?: string | null;
  }
): Promise<ExtractOverrideResponse> => {
  const response = await api.put(`/extract-overrides/${month}/${commentId}`, fields);
  return response.data;
};

// Mismatch analyzer types and functions (includes unmatched via display_mode: 'unmatched')
export interface MismatchAnalysisRequest {
  field: string;
  months: string[];
  threshold?: number;
  use_enriched_data?: boolean;
  display_mode?:
    | 'mismatches'
    | 'all'
    | 'unconfirmed'
    | 'regex'
    | 'intentionally_unmatched'
    | 'complete_brushes'
    | 'matches'
    | 'unmatched';
  /** Omit for no cap (server returns every grouped row). */
  limit?: number;
}

export interface MismatchItem {
  original: string;
  normalized?: string; // Add normalized field for search functionality
  matched: MatchedData; // Use specific union type instead of Record<string, unknown>
  enriched?: Record<string, unknown>;
  pattern: string;
  match_type: string;
  confidence?: number;
  mismatch_type?: string;
  reason?: string;
  count: number;
  examples: string[];
  comment_ids: string[];
  comment_sources?: Record<string, string>; // comment_id -> source_file
  is_confirmed?: boolean;
  // Split brush fields added by backend API
  is_split_brush?: boolean;
  handle_component?: string;
  knot_component?: string;
  // Strategy field for brush matching
  matched_by_strategy?: string;
  /** First markdown link on the SOTD header line, if any */
  sotd_photo_url?: string;
}

// More specific interface for brush matched data
export interface BrushMatchedData {
  type: 'brush'; // Explicit type for discrimination
  brand?: string;
  model?: string;
  fiber?: string;
  knot_size_mm?: number;
  handle_maker?: string;
  knot_maker?: string;
  fiber_strategy?: string;
  fiber_conflict?: string;
  matched_by_strategy?: string;
  _pattern_used?: string;
  _matched_from?: string;
  _original_knot_text?: string;
  _original_handle_text?: string;
  [key: string]: unknown; // Allow additional fields
}

// Union type for all matched data types
export type MatchedData = BrushMatchedData | Record<string, unknown>;

// Type guard to check if matched data is brush data
export function isBrushMatchedData(matched: MatchedData): matched is BrushMatchedData {
  return (
    typeof matched === 'object' && matched !== null && 'type' in matched && matched.type === 'brush'
  );
}

export interface MismatchAnalysisResult {
  field: string;
  months: string[]; // Changed from month: string to months: string[]
  total_matches: number;
  total_mismatches: number;
  mismatch_items: MismatchItem[];
  processing_time: number;
  partial_results?: boolean;
  error?: string;
  matched_data_map?: Record<string, Record<string, any>>;
}

// Format compatibility analysis
export interface FormatCompatibilityResult {
  razor_original: string;
  razor_matched: Record<string, any>;
  razor_enriched?: Record<string, any>;
  blade_original: string;
  blade_matched: Record<string, any>;
  severity: 'error' | 'warning';
  issue_type: string;
  comment_ids: string[];
  count: number;
}

export interface FormatCompatibilityResponse {
  months: string[];
  severity_filter: string;
  total_issues: number;
  errors: number;
  warnings: number;
  results: FormatCompatibilityResult[];
  processing_time: number;
}

export const analyzeFormatCompatibility = async (params: {
  months: string[];
  severity?: 'error' | 'warning' | 'all';
}): Promise<FormatCompatibilityResponse> => {
  try {
    const queryParams = new URLSearchParams();
    queryParams.append('months', params.months.join(','));
    if (params.severity) {
      queryParams.append('severity', params.severity);
    }

    const response = await api.get(`/format-compatibility?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error analyzing format compatibility:', error);
    throw error;
  }
};

export const analyzeMismatch = async (
  request: MismatchAnalysisRequest
): Promise<MismatchAnalysisResult> => {
  try {
    const response = await api.post('/analysis/mismatch', request);
    return response.data;
  } catch (error) {
    console.error('Failed to analyze mismatches:', error);
    throw error;
  }
};

// Group by matched API for soap analyzer
export interface GroupByMatchedRequest {
  months: string;
  group_by_matched: boolean;
  limit?: number;
}

export interface GroupByMatchedResult {
  groups: Array<{
    matched_string: string;
    total_count: number;
    top_patterns: Array<{
      original: string;
      count: number;
    }>;
    remaining_count: number;
    all_patterns: Array<{
      original: string;
      count: number;
    }>;
    pattern_count: number;
  }>;
  total_groups: number;
  total_matches: number;
  months_processed: string[];
  group_by_matched: boolean;
}

// Individual grouped data item for display in data table
export interface GroupedDataItem {
  matched_string: string;
  brand: string;
  scent: string;
  countable?: boolean;  // Optional: true by default, false for mashup scents
  is_mashup?: boolean;  // From enrich phase when mashup detected
  sample_type?: string | null;  // From enrich phase when sample usage detected
  total_count: number;
  top_patterns: Array<{
    original: string;
    count: number;
    match_type: string;
  }>;
  remaining_count: number;
  all_patterns: Array<{
    original: string;
    count: number;
    match_type: string;
  }>;
  pattern_count: number;
  match_type: string;
  match_type_breakdown: {
    exact: number;
    [key: string]: number; // regex, brand, or dash_split
  };
  // Add a flag to indicate this is grouped data
  is_grouped: true;
}

// Union type for data that can be either regular mismatch items or grouped data
export type AnalyzerDataItem = MismatchItem | GroupedDataItem;

// Type guard to check if data is grouped
export const isGroupedDataItem = (item: AnalyzerDataItem): item is GroupedDataItem => {
  return 'is_grouped' in item && item.is_grouped === true;
};

export const getSoapGroupByMatched = async (
  request: GroupByMatchedRequest
): Promise<GroupByMatchedResult> => {
  try {
    const response = await api.get('/soaps/group-by-matched', {
      params: request,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to get soap group by matched:', error);
    throw error;
  }
};

// Match phase operations
export interface MatchPhaseRequest {
  months: string[];
  force: boolean;
}

export interface MatchPhaseResult {
  months: string[];
  force: boolean;
  success: boolean;
  message: string;
  error_details?: string;
  processing_time: number;
}

export const runMatchPhase = async (request: MatchPhaseRequest): Promise<MatchPhaseResult> => {
  try {
    const response = await api.post('/analysis/match-phase', request);
    return response.data;
  } catch (error) {
    console.error('Failed to run match phase:', error);
    throw error;
  }
};

// Brush split operations
export interface LoadBrushSplitsResponse {
  brush_splits: BrushSplit[];
  statistics: Record<string, unknown>;
  processing_info?: Record<string, unknown>;
  errors?: Array<Record<string, unknown>>;
}

export interface SaveBrushSplitRequest {
  original: string;
  handle: string | null;
  knot: string;
  validated_at?: string;
  should_not_split?: boolean;
  occurrences?: Array<{ file: string; comment_ids: string[] }>;
}

export interface SaveBrushSplitResponse {
  success: boolean;
  message: string;
  corrected?: boolean;
  system_handle?: string | null;
  system_knot?: string | null;
  system_confidence?: string | null;
  system_reasoning?: string | null;
}

export interface SaveBrushSplitsRequest {
  brush_splits: BrushSplit[];
}

export interface SaveBrushSplitsResponse {
  success: boolean;
  message: string;
  saved_count: number;
}

export const loadBrushSplits = async (
  months: string[],
  unmatchedOnly: boolean = true
): Promise<LoadBrushSplitsResponse> => {
  try {
    const response = await api.get('/brushes/splits/load', {
      params: {
        months: months.join(','),
        unmatched_only: unmatchedOnly,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to load brush splits:', error);
    throw error;
  }
};

export const loadYamlBrushSplits = async (): Promise<LoadBrushSplitsResponse> => {
  try {
    const response = await api.get('/brushes/splits/yaml');
    return response.data;
  } catch (error) {
    console.error('Failed to load YAML brush splits:', error);
    throw error;
  }
};

export const saveBrushSplit = async (
  brushSplit: SaveBrushSplitRequest
): Promise<SaveBrushSplitResponse> => {
  try {
    const response = await api.post('/brushes/splits/save-split', {
      ...brushSplit,
      validated_at: brushSplit.validated_at || new Date().toISOString(),
    });
    return response.data;
  } catch (error) {
    console.error('Failed to save brush split:', error);
    throw error;
  }
};

export interface DeleteBrushSplitResponse {
  success: boolean;
  message: string;
  deleted: boolean;
}

export const deleteBrushSplit = async (original: string): Promise<DeleteBrushSplitResponse> => {
  try {
    const response = await api.delete('/brushes/splits/split', {
      params: { original },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to delete brush split:', error);
    throw error;
  }
};

export const saveBrushSplits = async (
  brushSplits: BrushSplit[]
): Promise<SaveBrushSplitsResponse> => {
  try {
    // Convert BrushSplit objects to the format expected by the API
    const formattedSplits = brushSplits.map(split => ({
      original: split.original,
      handle: split.handle,
      knot: split.knot,
      validated_at: split.validated_at,
      corrected: split.corrected,
      system_handle: split.system_handle,
      system_knot: split.system_knot,
      system_confidence: split.system_confidence,
      system_reasoning: split.system_reasoning,
      should_not_split: split.should_not_split,
      occurrences:
        split.occurrences?.map(occ => ({
          file: occ.file,
          comment_ids: occ.comment_ids,
        })) || [],
    }));

    const response = await api.post('/brushes/splits/save', {
      brush_splits: formattedSplits,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to save brush splits:', error);
    throw error;
  }
};

// Error handling utility
export const handleApiError = (error: unknown): string => {
  if (error && typeof error === 'object' && 'response' in error) {
    const apiError = error as { response: { data?: { message?: string }; status?: number } };
    if (apiError.response?.data?.message) {
      return apiError.response.data.message;
    }
    if (apiError.response?.status) {
      return `HTTP ${apiError.response.status} error`;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

// Filtered entries operations
export interface FilteredEntry {
  name: string;
  action: 'add' | 'remove';
  comment_id?: string;
  source?: string;
  month: string; // Add month to each entry
}

export interface FilteredEntryRequest {
  category: string;
  entries: FilteredEntry[];
  reason?: string;
}

export interface FilteredEntryResponse {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
  added_count: number;
  removed_count: number;
  errors: string[];
}

export interface FilteredStatusRequest {
  entries: Array<{
    category: string;
    name: string;
  }>;
}

export interface FilteredStatusResponse {
  success: boolean;
  message: string;
  data: Record<string, boolean>;
}

export const getFilteredEntries = async (): Promise<FilteredEntryResponse> => {
  try {
    const response = await api.get('/filtered/');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch filtered entries:', error);
    throw error;
  }
};

export const getFilteredEntriesByCategory = async (
  category: string
): Promise<FilteredEntryResponse> => {
  try {
    const response = await api.get(`/filtered/${category}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch filtered entries for ${category}:`, error);
    throw error;
  }
};

export const updateFilteredEntries = async (
  request: FilteredEntryRequest
): Promise<FilteredEntryResponse> => {
  try {
    const response = await api.post('/filtered/', request);
    return response.data;
  } catch (error) {
    console.error('Failed to update filtered entries:', error);
    throw error;
  }
};

export const checkFilteredStatus = async (
  request: FilteredStatusRequest
): Promise<FilteredStatusResponse> => {
  try {
    const response = await api.post('/filtered/check', request);
    return response.data;
  } catch (error) {
    console.error('Failed to check filtered status:', error);
    throw error;
  }
};

export interface MarkCorrectRequest {
  field: string;
  matches: Array<{
    original: string;
    matched: any;
  }>;
  force?: boolean;
}

export interface MarkCorrectResponse {
  success: boolean;
  message: string;
  marked_count: number;
  errors: string[];
  operation_id?: string;
  status_url?: string;
}

export interface CorrectMatchesResponse {
  field: string;
  total_entries: number;
  entries: Record<string, any>;
}

export interface QueueErrorEntry {
  field: string;
  original: string;
  matched?: Record<string, unknown> | null;
  message: string;
  error: string;
  retry_count: number;
  completed_at: number;
  operation_type: string;
}

export interface QueueErrorsResponse {
  source: string;
  errors: QueueErrorEntry[];
}

export const getQueueErrors = async (): Promise<QueueErrorsResponse> => {
  try {
    const response = await api.get('/analysis/queue-errors');
    return response.data;
  } catch (error) {
    console.error('Failed to get queue errors:', error);
    throw error;
  }
};

export const getCorrectMatches = async (field: string): Promise<CorrectMatchesResponse> => {
  try {
    const response = await api.get(`/analysis/correct-matches/${field}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get correct matches:', error);
    throw error;
  }
};

export const markMatchesAsCorrect = async (
  request: MarkCorrectRequest
): Promise<MarkCorrectResponse> => {
  try {
    const response = await api.post('/analysis/mark-correct', request);
    return response.data;
  } catch (error) {
    console.error('Failed to mark matches as correct:', error);
    throw error;
  }
};

export const clearCorrectMatchesByField = async (
  field: string
): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.delete(`/analysis/correct-matches/${field}`);
    return response.data;
  } catch (error) {
    console.error('Failed to clear correct matches:', error);
    throw error;
  }
};

export interface RemoveCorrectRequest {
  field: string;
  matches: Array<{
    original: string;
    matched: any;
  }>;
  force?: boolean;
}

export interface RemoveCorrectResponse {
  success: boolean;
  message: string;
  removed_count: number;
  errors: string[];
  operation_id?: string;
  status_url?: string;
}

export const removeMatchesFromCorrect = async (
  request: RemoveCorrectRequest
): Promise<RemoveCorrectResponse> => {
  try {
    const response = await api.post('/analysis/remove-correct', request);
    return response.data;
  } catch (error) {
    console.error('Failed to remove matches from correct matches:', error);
    throw error;
  }
};

export const clearAllCorrectMatches = async (): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.delete('/analysis/correct-matches');
    return response.data;
  } catch (error) {
    console.error('Failed to clear all correct matches:', error);
    throw error;
  }
};

// Operation status for async queue operations
export interface OperationStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  started_at?: number;
  updated_at: number;
  completed_at?: number;
  result?: {
    marked_count?: number;
    removed_count?: number;
    errors: string[];
    error?: string;
  };
}

export const getOperationStatus = async (operationId: string): Promise<OperationStatus> => {
  try {
    const response = await api.get(`/analysis/operation-status/${operationId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to get operation status for ${operationId}:`, error);
    throw error;
  }
};

export const clearValidatorCache = async (): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.post('/analysis/clear-validator-cache');
    return response.data;
  } catch (error) {
    console.error('Failed to clear validator cache:', error);
    throw error;
  }
};

// Catalog validation operations
export interface CatalogValidationRequest {
  field: string;
}

export interface CatalogValidationIssue {
  issue_type: 'catalog_pattern_mismatch' | 'catalog_pattern_no_match' | 'format_mismatch' | 'structural_change' | 'duplicate_string' | 'cross_section_conflict' | 'data_mismatch' | 'no_match';
  field: string;
  correct_match: string;
  expected_brand: string;
  expected_model: string;
  actual_brand: string;
  actual_model: string;
  severity: string;
  suggested_action: string;
  details: string;
  format?: string;
  catalog_format?: string;
  matched_pattern?: string;
  // Additional fields for brush validation
  version?: string; // For brush version (e.g., v26, v27)
  // Structural change fields
  expected_section?: string; // Where it currently is (correct_matches directory)
  actual_section?: string; // Where it should be (current matching system)
  // Brush-specific match details
  current_match_details?: {
    brand?: string;
    model?: string;
    fiber?: string;
    knot_size_mm?: number;
  };
  current_handle_match?: {
    brand?: string;
    model?: string;
  };
  current_knot_match?: {
    brand?: string;
    model?: string;
    fiber?: string;
    knot_size_mm?: number;
  };
  expected_handle_match?: {
    brand?: string;
    model?: string;
  };
  expected_knot_match?: {
    brand?: string;
    model?: string;
    fiber?: string;
    knot_size_mm?: number;
  };
  // Line numbers for duplicate/conflict issues
  line_numbers?: Record<string, number[]>; // Maps section/file name to list of line numbers
  // Source files where the issue originates
  source_files?: string[]; // List of file names (e.g., ["handle.yaml", "knot.yaml"])
}

export interface CatalogValidationResult {
  field: string;
  total_entries: number;
  issues: CatalogValidationIssue[];
  processing_time: number;
}

export const validateCatalogAgainstCorrectMatches = async (
  request: CatalogValidationRequest
): Promise<CatalogValidationResult> => {
  try {
    const response = await api.post('/analysis/validate-catalog', request);
    return response.data;
  } catch (error) {
    console.error('Failed to validate catalog against correct matches:', error);
    throw error;
  }
};

export const removeCatalogValidationEntries = async (request: {
  field: string;
  entries: Array<{
    correct_match: string;
    expected_brand: string;
    expected_model: string;
    issue_type?: string;
    format?: string; // Format section for blades (AC, DE, Half DE, etc.)
  }>;
}): Promise<{
  success: boolean;
  message: string;
  removed_count: number;
  errors: string[];
}> => {
  try {
    const response = await api.post('/analysis/remove-catalog-entries', {
      field: request.field,
      matches: request.entries,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to remove catalog validation entries:', error);
    throw error;
  }
};

export const moveCatalogValidationEntries = async (request: {
  field: string;
  entries: Array<{
    correct_match: string;
    expected_brand: string;
    expected_model: string;
    actual_brand: string;
    actual_model: string;
    issue_type: string;
    actual_section?: string;
    expected_section?: string;
    format?: string;
    expected_handle_match?: { brand?: string; model?: string };
    expected_knot_match?: {
      brand?: string;
      model?: string;
      fiber?: string;
      knot_size_mm?: number;
    };
  }>;
}): Promise<{
  success: boolean;
  message: string;
  moved_count: number;
  removed_count: number;
  added_count: number;
  errors: string[];
}> => {
  try {
    const response = await api.post('/analysis/move-catalog-entries', {
      field: request.field,
      matches: request.entries,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to move catalog validation entries:', error);
    throw error;
  }
};

// Brush validation interfaces
export interface BrushValidationEntry {
  input_text: string;
  normalized_text?: string; // Normalized text for matching operations
  system_used: 'scoring';
  matched?: {
    brand: string;
    model: string;
    strategy?: string;
    score?: number;
    handle?: {
      brand: string;
      model: string;
    };
    knot?: {
      brand: string;
      model: string;
      fiber?: string;
    };
  };
  all_strategies: Array<{
    strategy: string;
    score: number;
    result: Record<string, any>;
  }>;
  comment_ids?: string[]; // Comment IDs where this input text was found
}

export interface BrushValidationResponse {
  entries: BrushValidationEntry[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

export interface BrushValidationStatistics {
  total_entries: number;
  correct_entries: number;
  user_processed: number;
  overridden_count: number;
  total_processed: number;
  unprocessed_count: number;
  processing_rate: number;
  // Legacy fields for backward compatibility
  validated_count: number;
  user_validations: number;
  unvalidated_count: number;
  validation_rate: number;
  total_actions: number;
}

export interface StrategyDistributionStatistics {
  total_brush_records: number;
  correct_matches_count: number;
  remaining_entries: number;
  strategy_counts: Record<string, number>;
  all_strategies_lengths: Record<string, number>;
}

export interface BrushValidationActionRequest {
  input_text: string;
  month: string;
  system_used: 'scoring';
  action: 'validate' | 'override';
  // For override actions, specify which strategy index to use
  strategy_index?: number;
}

export interface BrushValidationActionResponse {
  success: boolean;
  message: string;
}

// Brush validation API functions
export const getBrushValidationData = async (
  month: string,
  system: 'scoring',
  options: {
    sortBy?: 'unvalidated' | 'validated' | 'ambiguity';
    page?: number;
    pageSize?: number;
    // New filter parameters for backend filtering
    strategyCount?: number;
    showValidated?: boolean;
    showSingleStrategy?: boolean;
    showMultipleStrategy?: boolean;
  } = {}
): Promise<BrushValidationResponse> => {
  try {
    const params = new URLSearchParams();
    if (options.sortBy) params.append('sort_by', options.sortBy);
    if (options.page) params.append('page', options.page.toString());
    if (options.pageSize) params.append('page_size', options.pageSize.toString());

    // Add new filter parameters
    if (options.strategyCount !== undefined)
      params.append('strategy_count', options.strategyCount.toString());
    if (options.showValidated !== undefined)
      params.append('show_validated', options.showValidated.toString());
    if (options.showSingleStrategy !== undefined)
      params.append('show_single_strategy', options.showSingleStrategy.toString());
    if (options.showMultipleStrategy !== undefined)
      params.append('show_multiple_strategy', options.showMultipleStrategy.toString());

    const response = await api.get(`/brushes/validation/data/${month}/${system}?${params}`);
    return response.data;
  } catch (error) {
    console.error('Error loading brush validation data:', error);
    throw error;
  }
};

export const getBrushValidationStatistics = async (
  month: string
): Promise<BrushValidationStatistics> => {
  try {
    const response = await api.get(`/brushes/validation/statistics/${month}`);
    return response.data;
  } catch (error) {
    console.error('Error loading brush validation statistics:', error);
    throw error;
  }
};

export const getStrategyDistributionStatistics = async (
  month: string
): Promise<StrategyDistributionStatistics> => {
  try {
    const response = await api.get(`/brushes/validation/statistics/${month}/strategy-distribution`);
    return response.data;
  } catch (error) {
    console.error('Error loading strategy distribution statistics:', error);
    throw error;
  }
};

export const recordBrushValidationAction = async (
  actionData: BrushValidationActionRequest
): Promise<BrushValidationActionResponse> => {
  try {
    const response = await api.post('/brushes/validation/action', actionData);
    return response.data;
  } catch (error) {
    console.error('Error recording brush validation action:', error);
    throw error;
  }
};

export const undoLastValidationAction = async (
  month: string
): Promise<BrushValidationActionResponse> => {
  try {
    const response = await api.post(`/brushes/validation/undo?month=${month}`);
    return response.data;
  } catch (error) {
    console.error('Error undoing last validation action:', error);
    throw error;
  }
};

// Product usage operations
export const getProductsForMonth = async (
  month: string,
  productType: string,
  search?: string
): Promise<Product[]> => {
  try {
    const params = new URLSearchParams();
    if (search) {
      params.append('search', search);
    }
    const response = await api.get(
      `/product-usage/products/${month}/${productType}?${params.toString()}`
    );
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch products for month ${month} and type ${productType}:`, error);
    throw error;
  }
};

export const getProductUsageAnalysis = async (
  month: string,
  productType: string,
  brand: string,
  model: string
): Promise<ProductUsageAnalysis> => {
  try {
    // URL encode brand and model to handle special characters
    const encodedBrand = encodeURIComponent(brand);
    const encodedModel = encodeURIComponent(model);
    const response = await api.get(
      `/product-usage/analysis/${month}/${productType}/${encodedBrand}/${encodedModel}`
    );
    return response.data;
  } catch (error) {
    console.error(
      `Failed to fetch product usage analysis for ${productType} '${brand} ${model}' in month ${month}:`,
      error
    );
    throw error;
  }
};

export const getProductYearlySummary = async (
  month: string,
  productType: string,
  brand: string,
  model: string
): Promise<ProductYearlySummary> => {
  try {
    // URL encode brand and model to handle special characters
    const encodedBrand = encodeURIComponent(brand);
    const encodedModel = encodeURIComponent(model);
    const response = await api.get(
      `/product-usage/yearly-summary/${month}/${productType}/${encodedBrand}/${encodedModel}`
    );
    return response.data;
  } catch (error) {
    console.error(
      `Failed to fetch product yearly summary for ${productType} '${brand} ${model}' starting from ${month}:`,
      error
    );
    throw error;
  }
};

// Report rankings (placement over time)
export interface ReportRankingsTable {
  id: string;
  label: string;
}

export interface ReportRankingsSeriesPoint {
  month: string;
  rank: number | null;
  shaves: number | null;
  unique_users: number | null;
}

export interface ReportRankingsSeriesEntry {
  item: string;
  data: ReportRankingsSeriesPoint[];
}

export interface ReportRankingsSeriesResponse {
  months: string[];
  series: ReportRankingsSeriesEntry[];
}

export interface ReportRankingsPivotedPoint {
  month: string;
  item: string | null;
  shaves: number | null;
  unique_users: number | null;
  prev_rank: number | null;
}

export interface ReportRankingsPivotedLane {
  rank: number;
  points: ReportRankingsPivotedPoint[];
}

export interface ReportRankingsPivotedResponse {
  months: string[];
  lanes: ReportRankingsPivotedLane[];
}

export const getReportRankingsPivoted = async (
  tableId: string
): Promise<ReportRankingsPivotedResponse> => {
  const response = await api.get<ReportRankingsPivotedResponse>('/report-rankings/pivoted', {
    params: { table: tableId },
  });
  return response.data;
};

export const getReportRankingsMonths = async (): Promise<string[]> => {
  const response = await api.get<{ months: string[] }>('/report-rankings/months');
  return response.data.months;
};

export const getReportRankingsTables = async (): Promise<ReportRankingsTable[]> => {
  const response = await api.get<{ tables: ReportRankingsTable[] }>('/report-rankings/tables');
  return response.data.tables;
};

export const getReportRankingsItems = async (
  table: string,
  month?: string
): Promise<string[]> => {
  const params = month ? { table, month } : { table };
  const response = await api.get<{ items: string[] }>('/report-rankings/items', { params });
  return response.data.items;
};

export const getReportRankingsSeries = async (
  table: string,
  items: string[]
): Promise<ReportRankingsSeriesResponse> => {
  const params = { table, items: items.join(',') };
  const response = await api.get<ReportRankingsSeriesResponse>('/report-rankings/series', {
    params,
  });
  return response.data;
};

// --- Agent Validation Types ---

export interface VerificationItem {
  comment_id: string;
  field: string;
  original: string;
  matched: Record<string, unknown>;
  match_type: string;
  verdict: 'verified' | 'needs_review' | 'incorrect';
  confidence: number;
  reasoning: string;
  source_url?: string;
  research?: string;
}

export interface VerifiedData {
  metadata: {
    month: string;
    processed_at: string;
    stats: {
      total_non_exact: number;
      verified_correct: number;
      needs_review: number;
      incorrect: number;
      proposals_generated: number;
    };
  };
  verifications: VerificationItem[];
}

export interface ProposalItem {
  type: 'new_scent' | 'new_pattern' | 'new_product';
  field: string;
  brand: string;
  model: string;
  suggested_pattern: string;
  suggested_entry?: Record<string, unknown>;
  evidence: string[];
  source_url?: string;
  research?: string;
  confidence: number;
  comment_id: string;
  _status?: 'accepted' | 'rejected';
  _accepted_at?: number;
  _rejected_at?: number;
}

export interface ProposedData {
  metadata: {
    month: string;
    processed_at: string;
    proposal_count: number;
  };
  proposals: ProposalItem[];
}

export interface ValidatedMonths {
  months: string[];
}

// --- Agent Validation API Functions ---

export const getVerifiedData = async (month: string): Promise<VerifiedData> => {
  try {
    const response = await api.get(`/validation/verified/${month}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch verified data for ${month}:`, error);
    throw error;
  }
};

export const getProposedData = async (month: string): Promise<ProposedData> => {
  try {
    const response = await api.get(`/validation/proposed/${month}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch proposed data for ${month}:`, error);
    throw error;
  }
};

export const getValidatedMonths = async (): Promise<ValidatedMonths> => {
  try {
    const response = await api.get('/validation/months');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch validated months:', error);
    throw error;
  }
};

export const acceptProposal = async (
  month: string,
  proposalIndex: number,
  editedProposal?: Record<string, unknown>
): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.post('/validation/accept-proposal', {
      month,
      proposal_index: proposalIndex,
      edited_proposal: editedProposal || null,
    });
    return response.data;
  } catch (error) {
    console.error(`Failed to accept proposal ${proposalIndex} for ${month}:`, error);
    throw error;
  }
};

export const rejectProposal = async (
  month: string,
  proposalIndex: number,
  reason?: string
): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.post('/validation/reject-proposal', {
      month,
      proposal_index: proposalIndex,
      reason: reason || null,
    });
    return response.data;
  } catch (error) {
    console.error(`Failed to reject proposal ${proposalIndex} for ${month}:`, error);
    throw error;
  }
};

export const bulkApproveVerified = async (
  field: string,
  matches: Array<{ original: string; matched: Record<string, unknown> }>
): Promise<{ success: boolean; operation_id: string; message: string }> => {
  try {
    const response = await api.post('/validation/bulk-approve', {
      field,
      matches,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to bulk approve verified matches:', error);
    throw error;
  }
};

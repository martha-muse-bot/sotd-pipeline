import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar as CalendarIcon, List as ListIcon, Table as TableIcon, BarChart3 as SummaryIcon, Loader2, Copy, Check } from 'lucide-react';
import { CommentDisplay } from '@/components/domain/CommentDisplay';
import CommentModal from '@/components/domain/CommentModal';
import { getCommentDetail, CommentDetail } from '@/services/api';
import { getProductsForMonth, getProductUsageAnalysis, getProductYearlySummary } from '@/services/api';
import { Product, ProductUsageAnalysis, ProductYearlySummary } from '@/types/productUsage';
import MonthSelector from '@/components/forms/MonthSelector';
import { isPublicBuild } from '@/lib/buildMode';
import axios from 'axios';

const ProductUsage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedMonths, setSelectedMonths] = useState<string[]>([]);
  const [selectedProductType, setSelectedProductType] = useState<'razor' | 'blade' | 'brush' | 'soap' | ''>('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [productSearch, setProductSearch] = useState<string>('');
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [productAnalyses, setProductAnalyses] = useState<Array<{ month: string; analysis: ProductUsageAnalysis }>>([]);
  const [aggregatedAnalysis, setAggregatedAnalysis] = useState<ProductUsageAnalysis | null>(null);
  const [yearlySummary, setYearlySummary] = useState<ProductYearlySummary | null>(null);
  const [yearlySummaryLoading, setYearlySummaryLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [viewMode, setViewMode] = useState<'table' | 'calendar' | 'list' | 'summary'>('calendar');

  // Comment modal state
  const [selectedComment, setSelectedComment] = useState<CommentDetail | null>(null);
  const [commentModalOpen, setCommentModalOpen] = useState(false);
  const [commentLoading, setCommentLoading] = useState(false);
  const [allComments, setAllComments] = useState<CommentDetail[]>([]);
  const [currentCommentIndex, setCurrentCommentIndex] = useState<number>(0);
  const [remainingCommentIds, setRemainingCommentIds] = useState<string[]>([]);

  // Track expanded state for each user to synchronize comment IDs and usage dates
  const [expandedUsers, setExpandedUsers] = useState<Record<string, boolean>>({});

  // Copy to markdown state
  const [copyLoading, setCopyLoading] = useState<Record<string, boolean>>({});
  const [copySuccess, setCopySuccess] = useState<Record<string, boolean>>({});
  const [commentUrls, setCommentUrls] = useState<Record<string, string>>({});

  // Read URL parameters on mount and initialize state
  useEffect(() => {
    const monthsParam = searchParams.get('months');
    const productTypeParam = searchParams.get('productType');
    const brandParam = searchParams.get('brand');
    const modelParam = searchParams.get('model');

    if (monthsParam) {
      // Parse comma-separated months
      const months = monthsParam.split(',').map(m => m.trim()).filter(m => m.length > 0);
      if (months.length > 0) {
        setSelectedMonths(months);
      }
    }

    if (productTypeParam && ['razor', 'blade', 'brush', 'soap'].includes(productTypeParam)) {
      setSelectedProductType(productTypeParam as 'razor' | 'blade' | 'brush' | 'soap');
    }
  }, [searchParams]);

  // Auto-select product when URL params are provided and products are loaded
  useEffect(() => {
    const brandParam = searchParams.get('brand');
    const modelParam = searchParams.get('model');
    const monthsParam = searchParams.get('months');
    const productTypeParam = searchParams.get('productType');

    // Only auto-select if all URL params exist, products are loaded, and we haven't already selected this product
    if (
      brandParam &&
      modelParam &&
      monthsParam &&
      productTypeParam &&
      products.length > 0 &&
      selectedMonths.length > 0 &&
      selectedProductType
    ) {
      // Check if we've already selected the matching product
      const isAlreadySelected =
        selectedProduct &&
        selectedProduct.brand === brandParam &&
        selectedProduct.model === modelParam;

      if (!isAlreadySelected) {
        // Find matching product by brand and model
        const matchingProduct = products.find(
          p => p.brand === brandParam && p.model === modelParam
        );

        if (matchingProduct) {
          setSelectedProduct(matchingProduct);
          // Trigger product analysis
          fetchProductAnalyses(selectedMonths, selectedProductType, matchingProduct);
          // For yearly summary, use the first selected month
          if (selectedMonths.length > 0) {
            fetchYearlySummary(selectedMonths[0], selectedProductType, matchingProduct);
          }
        } else {
          // Product not found - might not exist in those months
          setError(`Product ${brandParam} ${modelParam} not found in selected months`);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [products, searchParams, selectedMonths, selectedProductType, selectedProduct]);

  // Fetch products when months and product type change
  useEffect(() => {
    if (selectedMonths.length > 0 && selectedProductType) {
      fetchProductsForMonths(selectedMonths, selectedProductType);
    } else {
      setProducts([]);
      setFilteredProducts([]);
      setSelectedProduct(null);
      setAggregatedAnalysis(null);
      setProductAnalyses([]);
      setYearlySummary(null);
      setCommentUrls({});
    }
  }, [selectedMonths, selectedProductType]);

  // Filter products when search changes
  useEffect(() => {
    if (productSearch.trim() === '') {
      setFilteredProducts(products);
    } else {
      const searchLower = productSearch.toLowerCase();
      const filtered = products.filter(
        p =>
          p.brand.toLowerCase().includes(searchLower) ||
          p.model.toLowerCase().includes(searchLower)
      );
      setFilteredProducts(filtered);
    }
  }, [productSearch, products]);

  // Aggregate razor products by manufacturer (brand) for "how did Karve/Blackland do" view
  const razorManufacturers = useMemo(() => {
    if (selectedProductType !== 'razor' || products.length === 0) return [];
    const byBrand = new Map<
      string,
      { usage_count: number; model_count: number; unique_users_sum: number }
    >();
    products.forEach(p => {
      const existing = byBrand.get(p.brand);
      if (existing) {
        existing.usage_count += p.usage_count;
        existing.model_count += 1;
        existing.unique_users_sum += p.unique_users;
      } else {
        byBrand.set(p.brand, {
          usage_count: p.usage_count,
          model_count: 1,
          unique_users_sum: p.unique_users,
        });
      }
    });
    return Array.from(byBrand.entries())
      .map(([brand, stats]) => ({ brand, ...stats }))
      .sort((a, b) => b.usage_count - a.usage_count);
  }, [selectedProductType, products]);

  const fetchProductsForMonths = async (months: string[], productType: string) => {
    try {
      setLoading(true);
      setError('');
      const responses = await Promise.all(
        months.map(month => getProductsForMonth(month, productType))
      );

      // Merge products across all months
      const productMap = new Map<string, Product>();
      responses.forEach(productsData => {
        productsData.forEach(product => {
          const existing = productMap.get(product.key);
          if (existing) {
            existing.usage_count += product.usage_count;
            // For unique_users, we need to track unique users across months
            // Since we can't merge user sets from the API, we'll use the max value
            existing.unique_users = Math.max(existing.unique_users, product.unique_users);
          } else {
            productMap.set(product.key, { ...product });
          }
        });
      });

      const mergedProducts = Array.from(productMap.values()).sort((a, b) => b.usage_count - a.usage_count);
      setProducts(mergedProducts);
      setFilteredProducts(mergedProducts);
      setSelectedProduct(null);
      setAggregatedAnalysis(null);
      setProductAnalyses([]);
    } catch (err) {
      setError('Failed to fetch products for months');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to batch API calls to avoid overwhelming the server
  const batchProcess = async <T, R>(
    items: T[],
    batchSize: number,
    processor: (item: T) => Promise<R>
  ): Promise<R[]> => {
    const results: R[] = [];
    for (let i = 0; i < items.length; i += batchSize) {
      const batch = items.slice(i, i + batchSize);
      const batchResults = await Promise.all(batch.map(processor));
      results.push(...batchResults);
    }
    return results;
  };

  const aggregateProductAnalyses = (analyses: ProductUsageAnalysis[]): ProductUsageAnalysis => {
    if (analyses.length === 0) {
      throw new Error('Cannot aggregate empty analyses array');
    }

    // Merge users across months
    const userMap = new Map<string, any>();
    analyses.forEach(analysis => {
      analysis.users.forEach(user => {
        const existing = userMap.get(user.username);
        if (existing) {
          existing.usage_count += user.usage_count;
          // Merge usage_dates (unique)
          const dateSet = new Set([...existing.usage_dates, ...user.usage_dates]);
          existing.usage_dates = Array.from(dateSet).sort();
          // Merge comment_ids (unique)
          const commentIdSet = new Set([...existing.comment_ids, ...user.comment_ids]);
          existing.comment_ids = Array.from(commentIdSet);
        } else {
          userMap.set(user.username, {
            username: user.username,
            usage_count: user.usage_count,
            usage_dates: [...user.usage_dates].sort(),
            comment_ids: [...user.comment_ids],
          });
        }
      });
    });

    // Convert to array and sort by usage count
    const mergedUsers = Array.from(userMap.values()).sort((a, b) => b.usage_count - a.usage_count);

    // Merge comments_by_date across months
    const mergedCommentsByDate: Record<string, string[]> = {};
    analyses.forEach(analysis => {
      Object.entries(analysis.comments_by_date).forEach(([date, ids]) => {
        if (!mergedCommentsByDate[date]) {
          mergedCommentsByDate[date] = [];
        }
        mergedCommentsByDate[date].push(...ids);
        // Remove duplicates
        mergedCommentsByDate[date] = [...new Set(mergedCommentsByDate[date])];
      });
    });

    // Merge comment_urls from all analyses
    const mergedCommentUrls: Record<string, string> = {};
    analyses.forEach(analysis => {
      if (analysis.comment_urls) {
        Object.entries(analysis.comment_urls).forEach(([commentId, url]) => {
          if (url) {
            mergedCommentUrls[commentId] = url;
          }
        });
      }
    });

    // Sum total_usage and calculate unique_users
    const totalUsage = analyses.reduce((sum, a) => sum + a.total_usage, 0);
    const uniqueUsers = mergedUsers.length;

    return {
      product: analyses[0].product, // Keep product info from first analysis
      total_usage: totalUsage,
      unique_users: uniqueUsers,
      users: mergedUsers,
      usage_by_date: { ...mergedCommentsByDate },
      comments_by_date: mergedCommentsByDate,
      comment_urls: Object.keys(mergedCommentUrls).length > 0 ? mergedCommentUrls : undefined,
    };
  };

  const fetchProductAnalyses = async (months: string[], productType: string, product: Product) => {
    try {
      setLoading(true);
      setError('');

      // Process months in batches of 6 to avoid overwhelming the server
      const batchSize = 6;
      const responses = await batchProcess(months, batchSize, async month => {
        try {
          const analysis = await getProductUsageAnalysis(month, productType, product.brand, product.model);
          return { month, analysis, error: null };
        } catch (err: any) {
          // Handle case where product doesn't exist in a month
          if (err.response?.status === 404) {
            return { month, analysis: null, error: null };
          }
          // For other errors, return error info but don't throw
          return { month, analysis: null, error: err };
        }
      });

      // Check if any requests failed with non-404 errors
      const errors = responses.filter(r => r.error !== null);
      if (errors.length > 0) {
        const firstError = errors[0].error;
        const errorMessage =
          firstError instanceof Error && 'response' in firstError && (firstError as any).response?.status === 500
            ? 'Server error: Failed to fetch product analysis. Please try again later.'
            : firstError instanceof Error
            ? `Failed to fetch product analysis: ${firstError.message}`
            : 'Failed to fetch product analysis';
        setError(errorMessage);
        setAggregatedAnalysis(null);
        setProductAnalyses([]);
        return;
      }

      const validAnalysesWithMonths = responses
        .filter(r => r.analysis !== null)
        .map(r => ({
          month: r.month,
          analysis: r.analysis!,
        }));

      if (validAnalysesWithMonths.length === 0) {
        setError(`Product ${product.brand} ${product.model} not found in any selected month`);
        setAggregatedAnalysis(null);
        setProductAnalyses([]);
        return;
      }

      // Aggregate analyses
      const validAnalyses = validAnalysesWithMonths.map(item => item.analysis);
      const aggregated = aggregateProductAnalyses(validAnalyses);
      setAggregatedAnalysis(aggregated);
      setProductAnalyses(validAnalysesWithMonths);

      // Use pre-computed URLs if available, otherwise fetch them
      if (aggregated.comment_urls && Object.keys(aggregated.comment_urls).length > 0) {
        // Use pre-computed URLs from aggregation
        setCommentUrls(aggregated.comment_urls);
      } else {
        // Fallback: Fetch URLs for all comment IDs in the background
        // Extract unique comment IDs from aggregated comments_by_date (much more efficient)
        const allCommentIds = new Set<string>();
        Object.values(aggregated.comments_by_date).forEach(ids => {
          ids.forEach(id => allCommentIds.add(id));
        });

        if (allCommentIds.size > 0) {
          // Fetch URLs in batches to avoid overwhelming the server
          const urlMap: Record<string, string> = {};
          await batchProcess(Array.from(allCommentIds), 10, async commentId => {
            try {
              const comment = await getCommentDetail(commentId, months);
              return { commentId, url: comment.url };
            } catch (err) {
              console.warn(`Failed to fetch URL for comment ${commentId}:`, err);
              return { commentId, url: '' };
            }
          }).then(results => {
            results.forEach(({ commentId, url }) => {
              urlMap[commentId] = url;
            });
            setCommentUrls(urlMap);
          });
        } else {
          setCommentUrls({});
        }
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error && 'response' in err && (err as any).response?.status === 500
          ? 'Server error: Failed to fetch product analysis. Please try again later.'
          : err instanceof Error
          ? `Failed to fetch product analysis: ${err.message}`
          : 'Failed to fetch product analysis';
      setError(errorMessage);
      setAggregatedAnalysis(null);
      setProductAnalyses([]);
      setCommentUrls({});
      console.error('[ProductUsage] Error fetching product analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchYearlySummary = async (month: string, productType: string, product: Product) => {
    try {
      setYearlySummaryLoading(true);
      setError('');
      const summary = await getProductYearlySummary(month, productType, product.brand, product.model);
      setYearlySummary(summary);
    } catch (err) {
      setError('Failed to fetch yearly summary');
      console.error(err);
    } finally {
      setYearlySummaryLoading(false);
    }
  };

  // Helper function to get comment URLs from pre-computed or cache
  const getCommentUrls = (commentIds: string[]): Record<string, string> => {
    const urlMap: Record<string, string> = {};
    commentIds.forEach(commentId => {
      // First try pre-computed URLs from aggregated analysis
      if (aggregatedAnalysis?.comment_urls?.[commentId]) {
        urlMap[commentId] = aggregatedAnalysis.comment_urls[commentId];
      } else if (commentUrls[commentId]) {
        // Fallback to cached URLs
        urlMap[commentId] = commentUrls[commentId];
      }
    });
    return urlMap;
  };

  // Public build: open the Reddit URL of the first comment that has one.
  const openFirstCommentUrl = (commentIds: string[]) => {
    if (!isPublicBuild()) return;
    for (const id of commentIds) {
      const url = commentUrls[id];
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        return;
      }
    }
  };

  // Helper function to copy text to clipboard
  const copyToClipboard = async (text: string): Promise<boolean> => {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      return false;
    }
  };

  // Comment modal handlers
  const handleCommentClick = async (commentId: string, allCommentIds?: string[]) => {
    // Public build: the comment-detail API is admin-only, so link straight to
    // Reddit when the URL is known and do nothing when it isn't.
    if (isPublicBuild()) {
      const url = commentUrls[commentId];
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
      return;
    }

    try {
      setCommentLoading(true);

      // Always load just the clicked comment initially for fast response
      const comment = await getCommentDetail(commentId, selectedMonths);
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
      console.error('Error loading comment detail:', err);
      setError('Failed to load comment details');
    } finally {
      setCommentLoading(false);
    }
  };

  const handleCommentNavigation = async (direction: 'prev' | 'next') => {
    if (direction === 'prev' && currentCommentIndex > 0) {
      setCurrentCommentIndex(currentCommentIndex - 1);
      setSelectedComment(allComments[currentCommentIndex - 1]);
    } else if (direction === 'next') {
      if (currentCommentIndex < allComments.length - 1) {
        setCurrentCommentIndex(currentCommentIndex + 1);
        setSelectedComment(allComments[currentCommentIndex + 1]);
      } else if (remainingCommentIds.length > 0) {
        // Load next comment from remaining IDs
        const nextCommentId = remainingCommentIds[0];
        try {
          setCommentLoading(true);
          const nextComment = await getCommentDetail(nextCommentId, selectedMonths);
          setAllComments([...allComments, nextComment]);
          setRemainingCommentIds(remainingCommentIds.slice(1));
          setCurrentCommentIndex(allComments.length);
          setSelectedComment(nextComment);
        } catch (err: unknown) {
          console.error('Error loading next comment:', err);
          setError('Failed to load next comment');
        } finally {
          setCommentLoading(false);
        }
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

  // Helper function to update URL parameters
  // Only updates if the values actually changed to prevent infinite loops
  const updateUrlParams = (updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams);
    let hasChanges = false;

    Object.entries(updates).forEach(([key, value]) => {
      const currentValue = searchParams.get(key);
      if (value === null || value === '') {
        if (currentValue !== null) {
          newParams.delete(key);
          hasChanges = true;
        }
      } else {
        if (currentValue !== value) {
          newParams.set(key, value);
          hasChanges = true;
        }
      }
    });

    // Only update if there are actual changes
    if (hasChanges) {
      setSearchParams(newParams, { replace: true });
    }
  };

  const handleMonthChange = (months: string[]) => {
    setSelectedMonths(months);
    setSelectedProduct(null);
    setAggregatedAnalysis(null);
    setProductAnalyses([]);
    setYearlySummary(null);
    setProductSearch('');
    setCommentUrls({});

    // Update URL parameters
    if (months.length > 0) {
      updateUrlParams({ months: months.join(',') });
    } else {
      // Clear all related parameters when months are cleared
      updateUrlParams({ months: null, productType: null, brand: null, model: null });
    }
  };

  const handleProductTypeChange = (productType: string) => {
    setSelectedProductType(productType as 'razor' | 'blade' | 'brush' | 'soap' | '');
    setSelectedProduct(null);
    setAggregatedAnalysis(null);
    setProductAnalyses([]);
    setYearlySummary(null);
    setProductSearch('');
    setCommentUrls({});

    // Update URL parameters
    if (productType) {
      updateUrlParams({ productType, brand: null, model: null });
    } else {
      // Clear product-related parameters when product type is cleared
      updateUrlParams({ productType: null, brand: null, model: null });
    }
  };

  const handleProductSelect = (product: Product) => {
    setSelectedProduct(product);
    if (selectedMonths.length > 0 && selectedProductType) {
      fetchProductAnalyses(selectedMonths, selectedProductType, product);
      // For yearly summary, use the first selected month
      if (selectedMonths.length > 0) {
        fetchYearlySummary(selectedMonths[0], selectedProductType, product);
      }
    }

    // Update URL parameters with product brand and model
    if (product) {
      updateUrlParams({ brand: product.brand, model: product.model });
    }
  };

  const handleUserExpandChange = (username: string, expanded: boolean) => {
    setExpandedUsers(prev => ({
      ...prev,
      [username]: expanded,
    }));
  };

  // Navigate to MonthlyUserPosts with username and months
  const handleUsernameClick = (username: string) => {
    if (selectedMonths.length > 0) {
      const monthsParam = selectedMonths.join(',');
      navigate(`/monthly-user-posts?user=${encodeURIComponent(username)}&months=${encodeURIComponent(monthsParam)}`);
    }
  };

  // Build (date, commentId) pairs from comments_by_date so date labels match the comment opened (fixes wrong-date link bug).
  const getOrderedDateCommentPairs = (
    commentIds: string[],
    commentsByDate: Record<string, string[]>
  ): { dates: string[]; commentIds: string[] } => {
    const pairs: { date: string; commentId: string }[] = [];
    const commentIdToDate: Record<string, string> = {};
    Object.entries(commentsByDate).forEach(([date, ids]) => {
      ids.forEach(id => {
        commentIdToDate[id] = date;
      });
    });
    commentIds.forEach(commentId => {
      const date = commentIdToDate[commentId];
      if (date) pairs.push({ date, commentId });
    });
    pairs.sort((a, b) => b.date.localeCompare(a.date)); // latest first
    return {
      dates: pairs.map(p => p.date),
      commentIds: pairs.map(p => p.commentId),
    };
  };

  // Helper function to get dates with URLs for a user (uses cached URLs)
  const getUserUsageDatesWithUrls = (
    commentIds: string[],
    aggregatedAnalysis: ProductUsageAnalysis,
    includeUrls: boolean = true
  ): Array<{ date: string; url: string }> => {
    if (!aggregatedAnalysis || !commentIds || commentIds.length === 0) {
      return [];
    }

    // Map comment IDs to dates
    const commentIdToDate: Record<string, string> = {};
    const commentsByDate = aggregatedAnalysis.comments_by_date;

    commentIds.forEach(commentId => {
      for (const [date, dateCommentIds] of Object.entries(commentsByDate)) {
        if (dateCommentIds.includes(commentId)) {
          commentIdToDate[commentId] = date;
          break;
        }
      }
    });

    // Get URLs from cache if including URLs
    const commentUrlsMap = includeUrls ? getCommentUrls(commentIds) : {};

    // Group by date and get first URL for each date
    const dateToUrl: Record<string, string> = {};
    commentIds.forEach(commentId => {
      const date = commentIdToDate[commentId];
      if (date && !dateToUrl[date]) {
        dateToUrl[date] = includeUrls ? (commentUrlsMap[commentId] || '') : '';
      }
    });

    // Create array of date-url pairs, sorted by date
    const datesWithUrls = Object.keys(dateToUrl)
      .sort()
      .map(date => ({
        date,
        url: dateToUrl[date],
      }));

    return datesWithUrls;
  };

  // Generate markdown for calendar view
  const generateCalendarMarkdown = (
    month: string,
    monthAnalysis: ProductUsageAnalysis,
    year: number,
    monthNum: number,
    includeUrls: boolean = true
  ): string => {
    const startDate = new Date(year, monthNum - 1, 1);
    const endDate = new Date(year, monthNum, 0);
    const daysInMonth = endDate.getDate();
    const firstDayOfWeek = startDate.getDay();

    // Collect all unique comment IDs for this month
    const allCommentIds = new Set<string>();
    Object.values(monthAnalysis.comments_by_date).forEach(ids => {
      ids.forEach(id => allCommentIds.add(id));
    });

    // Get URLs from cache if including URLs
    const commentUrlsMap = includeUrls ? getCommentUrls(Array.from(allCommentIds)) : {};

    // Build calendar grid
    const monthName = new Date(year, monthNum - 1).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
    });

    let markdown = `## ${monthName}\n\n`;
    markdown += '| Sun | Mon | Tue | Wed | Thu | Fri | Sat |\n';
    markdown += '|-----|-----|-----|-----|-----|-----|-----|\n';

    // Empty cells for days before month starts
    const emptyCells = Array(firstDayOfWeek).fill('|     ');
    let currentRow = emptyCells.join('');

    // Generate calendar days
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const dayCommentIds = monthAnalysis.comments_by_date[dateStr] || [];
      const isUsed = dayCommentIds.length > 0;

      if (isUsed && dayCommentIds.length > 0 && includeUrls) {
        // Use the first comment URL for the day link
        const firstCommentId = dayCommentIds[0];
        const url = commentUrlsMap[firstCommentId] || '';
        if (url) {
          currentRow += `| [${day}](${url}) `;
        } else {
          currentRow += `| ${day} `;
        }
      } else {
        currentRow += `| ${day} `;
      }

      // Start new row on Saturday
      if ((firstDayOfWeek + day) % 7 === 0) {
        markdown += currentRow + '|\n';
        currentRow = '';
      }
    }

    // Add remaining cells for the last row
    if (currentRow) {
      const remainingCells = 7 - (currentRow.match(/\|/g) || []).length;
      for (let i = 0; i < remainingCells; i++) {
        currentRow += '|     ';
      }
      markdown += currentRow + '|\n';
    }

    return markdown;
  };

  // Generate markdown for list view
  const generateListViewMarkdown = (
    selectedMonths: string[],
    productAnalyses: Array<{ month: string; analysis: ProductUsageAnalysis }>,
    aggregatedAnalysis: ProductUsageAnalysis,
    singleMonth?: string
  ): string => {
    let markdown = '';

    // If singleMonth is specified, only generate for that month
    const monthsToProcess = singleMonth ? [singleMonth] : selectedMonths;

    if (selectedMonths.length > 1 && aggregatedAnalysis && !singleMonth) {
      markdown += `## ${selectedMonths.length} months selected\n\n`;
      markdown += `Total Usage: ${aggregatedAnalysis.total_usage} times by ${aggregatedAnalysis.unique_users} users\n\n`;
    }

    // Generate table for each month
    monthsToProcess.forEach(month => {
      const monthData = productAnalyses.find(a => a.month === month);
      const monthAnalysis = monthData?.analysis;

      if (!monthAnalysis) return;

      const [year, monthNum] = month.split('-').map(Number);
      const monthName = new Date(year, monthNum - 1).toLocaleDateString('en-US', {
        month: 'long',
        year: 'numeric',
      });

      markdown += `## ${monthName} - Daily Usage\n\n`;
      markdown += '| Date | Status | Uses | Users |\n';
      markdown += '|------|--------|------|-------|\n';

      const endDate = new Date(year, monthNum, 0);
      const daysInMonth = endDate.getDate();

      // Get users who used the product on each date
      const dateUserMap: Record<string, string[]> = {};
      monthAnalysis.users.forEach(user => {
        user.usage_dates.forEach(date => {
          if (!dateUserMap[date]) {
            dateUserMap[date] = [];
          }
          if (!dateUserMap[date].includes(user.username)) {
            dateUserMap[date].push(user.username);
          }
        });
      });

      for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isUsed = monthAnalysis.comments_by_date[dateStr]?.length > 0;
        const status = isUsed ? 'Used' : 'Not Used';
        const uses = monthAnalysis.comments_by_date[dateStr]?.length || 0;
        const users = dateUserMap[dateStr]?.length || 0;

        markdown += `| ${dateStr} | ${status} | ${uses} | ${users} |\n`;
      }

      markdown += '\n';
    });

    return markdown;
  };

  // Generate markdown for user table
  const generateUserTableMarkdown = (
    aggregatedAnalysis: ProductUsageAnalysis,
    includeUrls: boolean = true
  ): string => {
    let markdown = '## Users\n\n';
    markdown += '| # | Username | Usage Count | Dates |\n';
    markdown += '|---|----------|-------------|-------|\n';

    for (const [index, user] of aggregatedAnalysis.users.entries()) {
      const datesWithUrls = getUserUsageDatesWithUrls(
        user.comment_ids,
        aggregatedAnalysis,
        includeUrls
      );
      const datesStr =
        datesWithUrls.length > 0
          ? datesWithUrls
              .map(({ date, url }) => (includeUrls && url ? `[${date}](${url})` : date))
              .join(', ')
          : '-';

      markdown += `| ${index + 1} | ${user.username} | ${user.usage_count} | ${datesStr} |\n`;
    }

    return markdown;
  };

  // Handler for copying calendar markdown
  const handleCopyCalendarMarkdown = async (month: string, includeUrls: boolean = true) => {
    const monthData = productAnalyses.find(a => a.month === month);
    const monthAnalysis = monthData?.analysis;

    if (!monthAnalysis) return;

    const [year, monthNum] = month.split('-').map(Number);
    const key = `calendar-${month}-${includeUrls ? 'with-urls' : 'no-urls'}`;

    setCopyLoading(prev => ({ ...prev, [key]: true }));
    setCopySuccess(prev => ({ ...prev, [key]: false }));

    try {
      const markdown = generateCalendarMarkdown(month, monthAnalysis, year, monthNum, includeUrls);
      const success = await copyToClipboard(markdown);

      if (success) {
        setCopySuccess(prev => ({ ...prev, [key]: true }));
        setTimeout(() => {
          setCopySuccess(prev => ({ ...prev, [key]: false }));
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to generate calendar markdown:', err);
    } finally {
      setCopyLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  // Handler for copying list view markdown
  const handleCopyListViewMarkdown = async (singleMonth?: string, includeUrls: boolean = true) => {
    if (!aggregatedAnalysis) return;

    const key = singleMonth
      ? `list-view-${singleMonth}-${includeUrls ? 'with-urls' : 'no-urls'}`
      : `list-view-${includeUrls ? 'with-urls' : 'no-urls'}`;
    setCopyLoading(prev => ({ ...prev, [key]: true }));
    setCopySuccess(prev => ({ ...prev, [key]: false }));

    try {
      const markdown = generateListViewMarkdown(
        selectedMonths,
        productAnalyses,
        aggregatedAnalysis,
        singleMonth
      );
      const success = await copyToClipboard(markdown);

      if (success) {
        setCopySuccess(prev => ({ ...prev, [key]: true }));
        setTimeout(() => {
          setCopySuccess(prev => ({ ...prev, [key]: false }));
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to generate list view markdown:', err);
    } finally {
      setCopyLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  // Handler for copying user table markdown
  const handleCopyUserTableMarkdown = async (includeUrls: boolean = true) => {
    if (!aggregatedAnalysis) return;

    const key = `user-table-${includeUrls ? 'with-urls' : 'no-urls'}`;
    setCopyLoading(prev => ({ ...prev, [key]: true }));
    setCopySuccess(prev => ({ ...prev, [key]: false }));

    try {
      const markdown = generateUserTableMarkdown(aggregatedAnalysis, includeUrls);
      const success = await copyToClipboard(markdown);

      if (success) {
        setCopySuccess(prev => ({ ...prev, [key]: true }));
        setTimeout(() => {
          setCopySuccess(prev => ({ ...prev, [key]: false }));
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to generate user table markdown:', err);
    } finally {
      setCopyLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const renderTableView = () => {
    if (!aggregatedAnalysis) {
      return (
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Select a product to see usage analysis
        </div>
      );
    }

    return (
      <div className='space-y-4'>
        <div className='flex justify-end gap-2'>
          <Button
            variant='outline'
            size='sm'
            onClick={() => handleCopyUserTableMarkdown(true)}
            disabled={copyLoading['user-table-with-urls']}
            className='flex items-center gap-2'
          >
            {copyLoading['user-table-with-urls'] ? (
              <Loader2 className='h-4 w-4 animate-spin' />
            ) : copySuccess['user-table-with-urls'] ? (
              <Check className='h-4 w-4' />
            ) : (
              <Copy className='h-4 w-4' />
            )}
            {copySuccess['user-table-with-urls'] ? 'Copied!' : 'Copy (with URLs)'}
          </Button>
          <Button
            variant='outline'
            size='sm'
            onClick={() => handleCopyUserTableMarkdown(false)}
            disabled={copyLoading['user-table-no-urls']}
            className='flex items-center gap-2'
          >
            {copyLoading['user-table-no-urls'] ? (
              <Loader2 className='h-4 w-4 animate-spin' />
            ) : copySuccess['user-table-no-urls'] ? (
              <Check className='h-4 w-4' />
            ) : (
              <Copy className='h-4 w-4' />
            )}
            {copySuccess['user-table-no-urls'] ? 'Copied!' : 'Copy (no URLs)'}
          </Button>
        </div>
        <div className='overflow-x-auto'>
          <table className='w-full min-w-[768px] border-collapse border border-border'>
            <thead>
              <tr className='bg-muted'>
                <th className='border border-border p-2 text-center'>#</th>
                <th className='border border-border p-2 text-left'>Username</th>
                <th className='border border-border p-2 text-center'>Usage Count</th>
                <th className='border border-border p-2 text-left'>Usage Dates</th>
                <th className='hidden md:table-cell border border-border p-2 text-left'>Comment IDs</th>
              </tr>
            </thead>
            <tbody>
              {aggregatedAnalysis.users.map((user, index) => {
                const ordered = getOrderedDateCommentPairs(
                  user.comment_ids,
                  aggregatedAnalysis.comments_by_date
                );
                return (
                  <tr key={user.username} className='hover:bg-muted/50'>
                    <td className='border border-border p-2 text-center font-medium'>{index + 1}</td>
                    <td className='border border-border p-2'>{user.username}</td>
                    <td className='border border-border p-2 text-center'>{user.usage_count}</td>
                    <td className='border border-border p-2'>
                      <CommentDisplay
                        commentIds={ordered.commentIds}
                        onCommentClick={commentId => handleCommentClick(commentId, user.comment_ids)}
                        displayMode='dates'
                        dates={ordered.dates}
                        expanded={expandedUsers[user.username]}
                        onExpandChange={expanded => handleUserExpandChange(user.username, expanded)}
                      />
                    </td>
                    <td className='hidden md:table-cell border border-border p-2'>
                      <CommentDisplay
                        commentIds={ordered.commentIds}
                        onCommentClick={commentId => handleCommentClick(commentId, user.comment_ids)}
                        expanded={expandedUsers[user.username]}
                        onExpandChange={expanded => handleUserExpandChange(user.username, expanded)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderCalendarView = () => {
    if (!aggregatedAnalysis || selectedMonths.length === 0) {
      return (
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Select a product to see usage analysis
        </div>
      );
    }

    return (
      <div className='space-y-8'>
        {/* Aggregated summary when multiple months */}
        {selectedMonths.length > 1 && aggregatedAnalysis && (
          <div className='text-center mb-4'>
            <h3 className='text-lg font-semibold'>{selectedMonths.length} months selected</h3>
            <p className='text-sm text-muted-foreground'>
              Total Usage: {aggregatedAnalysis.total_usage} times by {aggregatedAnalysis.unique_users} users
            </p>
          </div>
        )}

        {/* Separate calendar section for each month */}
        {[...selectedMonths].sort().map(month => {
          const monthData = productAnalyses.find(a => a.month === month);
          const monthAnalysis = monthData?.analysis || null;

          if (!monthAnalysis) return null;

          // Parse the month to get year and month number
          const [year, monthNum] = month.split('-').map(Number);
          const startDate = new Date(year, monthNum - 1, 1);
          const endDate = new Date(year, monthNum, 0);
          const daysInMonth = endDate.getDate();

          // Create array of dates for the month
          const dates = Array.from({ length: daysInMonth }, (_, i) => i + 1);

          // Convert usage dates to day numbers for easy lookup
          const usageDays = new Set(
            Object.keys(monthAnalysis.comments_by_date).map(dateStr => {
              const date = new Date(dateStr + 'T00:00:00'); // Add time to avoid timezone issues
              return date.getDate();
            })
          );

          // Get users who used the product on each date for distinct user count
          const dateUserMap: Record<string, string[]> = {};
          monthAnalysis.users.forEach(user => {
            user.usage_dates.forEach(date => {
              if (!dateUserMap[date]) {
                dateUserMap[date] = [];
              }
              if (!dateUserMap[date].includes(user.username)) {
                dateUserMap[date].push(user.username);
              }
            });
          });

          return (
            <div key={month} className='space-y-4'>
              <div className='text-center relative'>
                <div className='flex items-center justify-center gap-2 mt-2 sm:mt-0 sm:absolute sm:top-0 sm:right-0'>
                  <Button
                    variant='outline'
                    size='sm'
                    onClick={() => handleCopyCalendarMarkdown(month, true)}
                    disabled={copyLoading[`calendar-${month}-with-urls`]}
                    className='flex items-center gap-2'
                  >
                    {copyLoading[`calendar-${month}-with-urls`] ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : copySuccess[`calendar-${month}-with-urls`] ? (
                      <Check className='h-4 w-4' />
                    ) : (
                      <Copy className='h-4 w-4' />
                    )}
                    {copySuccess[`calendar-${month}-with-urls`] ? 'Copied!' : 'Copy (with URLs)'}
                  </Button>
                  <Button
                    variant='outline'
                    size='sm'
                    onClick={() => handleCopyCalendarMarkdown(month, false)}
                    disabled={copyLoading[`calendar-${month}-no-urls`]}
                    className='flex items-center gap-2'
                  >
                    {copyLoading[`calendar-${month}-no-urls`] ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : copySuccess[`calendar-${month}-no-urls`] ? (
                      <Check className='h-4 w-4' />
                    ) : (
                      <Copy className='h-4 w-4' />
                    )}
                    {copySuccess[`calendar-${month}-no-urls`] ? 'Copied!' : 'Copy (no URLs)'}
                  </Button>
                </div>
                <h3 className='text-lg font-semibold'>
                  {new Date(year, monthNum - 1).toLocaleDateString('en-US', {
                    month: 'long',
                    year: 'numeric',
                  })}
                </h3>
                <p className='text-sm text-muted-foreground'>
                  Total Usage: {monthAnalysis.total_usage} times by {monthAnalysis.unique_users} users
                </p>
              </div>

              <div className='grid grid-cols-7 gap-1'>
                {/* Day headers */}
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className='p-2 text-center text-sm font-medium text-muted-foreground'>
                    {day}
                  </div>
                ))}

                {/* Empty cells for days before month starts */}
                {Array.from({ length: startDate.getDay() }, (_, i) => (
                  <div key={`empty-${i}`} className='p-2' />
                ))}

                {/* Month days */}
                {dates.map(day => {
                  const isUsed = usageDays.has(day);
                  const dateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                  const dayCommentIds = monthAnalysis.comments_by_date[dateStr] || [];
                  const dayUsers = dateUserMap[dateStr] || [];
                  const dailyUses = dayCommentIds.length;
                  const distinctUsers = dayUsers.length;

                  return (
                    <div
                      key={day}
                      onClick={
                        isPublicBuild() && isUsed && dayCommentIds.length > 0
                          ? () => openFirstCommentUrl(dayCommentIds)
                          : undefined
                      }
                      className={`p-2 text-center border rounded-md min-h-[56px] sm:min-h-[80px] flex flex-col items-center justify-center ${
                        isUsed
                          ? 'bg-green-100 border-green-300 text-green-800'
                          : 'bg-gray-100 border-gray-300 text-gray-400'
                      } ${isPublicBuild() && isUsed && dayCommentIds.length > 0 ? 'cursor-pointer' : ''}`}
                    >
                      <span className='text-sm font-medium'>{day}</span>
                      {isUsed && dailyUses > 0 && (
                        <div className='mt-1 space-y-0.5'>
                          <div className='text-xs'>
                            {dailyUses} {dailyUses === 1 ? 'use' : 'uses'}
                          </div>
                          <div className='text-xs'>
                            {distinctUsers} {distinctUsers === 1 ? 'user' : 'users'}
                          </div>
                          {!isPublicBuild() && (
                            <div className='mt-1'>
                              <CommentDisplay
                                commentIds={dayCommentIds}
                                onCommentClick={commentId => handleCommentClick(commentId, dayCommentIds)}
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderListView = () => {
    if (!aggregatedAnalysis || selectedMonths.length === 0) {
      return (
        <div className='flex items-center justify-center h-64 text-muted-foreground'>
          Select a product to see usage analysis
        </div>
      );
    }

    return (
      <div className='space-y-8'>
        {/* Aggregated summary when multiple months */}
        {selectedMonths.length > 1 && aggregatedAnalysis && (
          <div className='text-center mb-4 relative'>
            <div className='flex items-center justify-center gap-2 mt-2 sm:mt-0 sm:absolute sm:top-0 sm:right-0'>
              <Button
                variant='outline'
                size='sm'
                onClick={() => handleCopyListViewMarkdown(undefined, true)}
                disabled={copyLoading['list-view-with-urls']}
                className='flex items-center gap-2'
              >
                {copyLoading['list-view-with-urls'] ? (
                  <Loader2 className='h-4 w-4 animate-spin' />
                ) : copySuccess['list-view-with-urls'] ? (
                  <Check className='h-4 w-4' />
                ) : (
                  <Copy className='h-4 w-4' />
                )}
                {copySuccess['list-view-with-urls'] ? 'Copied!' : 'Copy (with URLs)'}
              </Button>
              <Button
                variant='outline'
                size='sm'
                onClick={() => handleCopyListViewMarkdown(undefined, false)}
                disabled={copyLoading['list-view-no-urls']}
                className='flex items-center gap-2'
              >
                {copyLoading['list-view-no-urls'] ? (
                  <Loader2 className='h-4 w-4 animate-spin' />
                ) : copySuccess['list-view-no-urls'] ? (
                  <Check className='h-4 w-4' />
                ) : (
                  <Copy className='h-4 w-4' />
                )}
                {copySuccess['list-view-no-urls'] ? 'Copied!' : 'Copy (no URLs)'}
              </Button>
            </div>
            <h3 className='text-lg font-semibold'>{selectedMonths.length} months selected</h3>
            <p className='text-sm text-muted-foreground'>
              Total Usage: {aggregatedAnalysis.total_usage} times by {aggregatedAnalysis.unique_users} users
            </p>
          </div>
        )}

        {/* Copy button for single month list view */}
        {selectedMonths.length === 1 && (
          <div className='flex justify-end mb-4 gap-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => handleCopyListViewMarkdown(undefined, true)}
              disabled={copyLoading['list-view-with-urls']}
              className='flex items-center gap-2'
            >
              {copyLoading['list-view-with-urls'] ? (
                <Loader2 className='h-4 w-4 animate-spin' />
              ) : copySuccess['list-view-with-urls'] ? (
                <Check className='h-4 w-4' />
              ) : (
                <Copy className='h-4 w-4' />
              )}
              {copySuccess['list-view-with-urls'] ? 'Copied!' : 'Copy (with URLs)'}
            </Button>
            <Button
              variant='outline'
              size='sm'
              onClick={() => handleCopyListViewMarkdown(undefined, false)}
              disabled={copyLoading['list-view-no-urls']}
              className='flex items-center gap-2'
            >
              {copyLoading['list-view-no-urls'] ? (
                <Loader2 className='h-4 w-4 animate-spin' />
              ) : copySuccess['list-view-no-urls'] ? (
                <Check className='h-4 w-4' />
              ) : (
                <Copy className='h-4 w-4' />
              )}
              {copySuccess['list-view-no-urls'] ? 'Copied!' : 'Copy (no URLs)'}
            </Button>
          </div>
        )}

        {/* Separate section for each month */}
        {[...selectedMonths].sort().map(month => {
          const monthData = productAnalyses.find(a => a.month === month);
          const monthAnalysis = monthData?.analysis || null;

          if (!monthAnalysis) return null;

          const [year, monthNum] = month.split('-').map(Number);
          const daysInMonth = new Date(year, monthNum, 0).getDate();
          const usageDays = new Set(
            Object.keys(monthAnalysis.comments_by_date).map(dateStr => {
              const date = new Date(dateStr + 'T00:00:00'); // Add time to avoid timezone issues
              return date.getDate();
            })
          );

          // Get users who used the product on each date
          const dateUserMap: Record<string, string[]> = {};
          monthAnalysis.users.forEach(user => {
            user.usage_dates.forEach(date => {
              if (!dateUserMap[date]) {
                dateUserMap[date] = [];
              }
              if (!dateUserMap[date].includes(user.username)) {
                dateUserMap[date].push(user.username);
              }
            });
          });

          return (
            <div key={month} className='space-y-4'>
              <div className='text-center mb-4 relative'>
                <div className='flex items-center justify-center gap-2 mt-2 sm:mt-0 sm:absolute sm:top-0 sm:right-0'>
                  <Button
                    variant='outline'
                    size='sm'
                    onClick={() => handleCopyListViewMarkdown(month, true)}
                    disabled={copyLoading[`list-view-${month}-with-urls`]}
                    className='flex items-center gap-2'
                  >
                    {copyLoading[`list-view-${month}-with-urls`] ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : copySuccess[`list-view-${month}-with-urls`] ? (
                      <Check className='h-4 w-4' />
                    ) : (
                      <Copy className='h-4 w-4' />
                    )}
                    {copySuccess[`list-view-${month}-with-urls`] ? 'Copied!' : 'Copy (with URLs)'}
                  </Button>
                  <Button
                    variant='outline'
                    size='sm'
                    onClick={() => handleCopyListViewMarkdown(month, false)}
                    disabled={copyLoading[`list-view-${month}-no-urls`]}
                    className='flex items-center gap-2'
                  >
                    {copyLoading[`list-view-${month}-no-urls`] ? (
                      <Loader2 className='h-4 w-4 animate-spin' />
                    ) : copySuccess[`list-view-${month}-no-urls`] ? (
                      <Check className='h-4 w-4' />
                    ) : (
                      <Copy className='h-4 w-4' />
                    )}
                    {copySuccess[`list-view-${month}-no-urls`] ? 'Copied!' : 'Copy (no URLs)'}
                  </Button>
                </div>
                <h3 className='text-lg font-semibold'>
                  {new Date(year, monthNum - 1).toLocaleDateString('en-US', {
                    month: 'long',
                    year: 'numeric',
                  })}
                </h3>
                <p className='text-sm text-muted-foreground'>
                  Total Usage: {monthAnalysis.total_usage} times by {monthAnalysis.unique_users} users
                </p>
              </div>

              <div className='space-y-2'>
                {Array.from({ length: daysInMonth }, (_, i) => {
                  const day = i + 1;
                  const isUsed = usageDays.has(day);
                  const dateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                  const dayCommentIds = monthAnalysis.comments_by_date[dateStr] || [];
                  const dayUsers = dateUserMap[dateStr] || [];

                  const dailyUses = dayCommentIds.length;
                  const distinctUsers = dayUsers.length;

                  return (
                    <div
                      key={day}
                      className={`flex items-center justify-between p-3 border rounded-lg ${
                        isUsed ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className='flex items-center space-x-3'>
                        <span className='font-medium'>Day {day}</span>
                        <Badge variant={isUsed ? 'default' : 'outline'} className={isUsed ? 'bg-green-600' : ''}>
                          {isUsed ? 'Used' : 'Not Used'}
                        </Badge>
                        {isUsed && (
                          <div className='flex items-center space-x-2 text-sm'>
                            <Badge variant='outline' className='bg-blue-50'>
                              {dailyUses} {dailyUses === 1 ? 'use' : 'uses'}
                            </Badge>
                            <Badge variant='outline' className='bg-purple-50'>
                              {distinctUsers} {distinctUsers === 1 ? 'user' : 'users'}
                            </Badge>
                            {dayUsers.length > 0 && (
                              <span className='text-muted-foreground'>
                                ({dayUsers.join(', ')})
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      {isUsed && dayCommentIds.length > 0 && (
                        <div className='text-sm text-muted-foreground'>
                          <CommentDisplay
                            commentIds={dayCommentIds}
                            onCommentClick={commentId => handleCommentClick(commentId, dayCommentIds)}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderSummaryView = () => {
    if (!yearlySummary) {
      return (
        <div className='text-center p-8 text-muted-foreground'>
          {yearlySummaryLoading ? (
            <div className='flex items-center justify-center'>
              <Loader2 className='h-8 w-8 animate-spin mr-2' />
              <span>Loading yearly summary...</span>
            </div>
          ) : (
            <span>No yearly summary data available</span>
          )}
        </div>
      );
    }

    return (
      <div className='space-y-4'>
        <div className='text-center mb-4'>
          <h3 className='text-lg font-semibold'>
            Yearly Summary: {yearlySummary.product.brand} {yearlySummary.product.model}
          </h3>
          {selectedProductType === 'razor' && (
            <p className='text-sm text-muted-foreground'>Manufacturer: {yearlySummary.product.brand}</p>
          )}
          <p className='text-sm text-muted-foreground'>Past 12 Months</p>
        </div>

        <div className='overflow-x-auto'>
          <table className='w-full min-w-[768px] border-collapse border border-border'>
            <thead>
              <tr className='bg-muted'>
                <th className='border border-border p-2 text-left'>Month</th>
                <th className='border border-border p-2 text-center'>Shaves</th>
                <th className='border border-border p-2 text-center'>Unique Users</th>
                <th className='border border-border p-2 text-center'>Rank</th>
              </tr>
            </thead>
            <tbody>
              {yearlySummary.months.map(monthData => {
                // Format month for display (e.g., "Nov 2025")
                const [year, month] = monthData.month.split('-');
                const monthDate = new Date(parseInt(year), parseInt(month) - 1, 1);
                const monthDisplay = monthDate.toLocaleDateString('en-US', {
                  month: 'short',
                  year: 'numeric',
                });

                return (
                  <tr
                    key={monthData.month}
                    className={`hover:bg-muted/50 ${
                      selectedMonths.includes(monthData.month) ? 'bg-blue-50' : ''
                    }`}
                  >
                    <td className='border border-border p-2 font-medium'>{monthDisplay}</td>
                    <td className='border border-border p-2 text-center'>
                      {monthData.has_data ? monthData.shaves.toLocaleString() : '-'}
                    </td>
                    <td className='border border-border p-2 text-center'>
                      {monthData.has_data ? monthData.unique_users.toLocaleString() : '-'}
                    </td>
                    <td className='border border-border p-2 text-center'>
                      {monthData.has_data && monthData.rank !== null
                        ? monthData.rank.toLocaleString()
                        : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className='container mx-auto p-4 sm:p-6 space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <div>
          <h1 className='text-2xl sm:text-3xl font-bold'>Product Usage</h1>
          <p className='text-muted-foreground'>Analyze which users used a specific product in any month</p>
        </div>
      </div>

      {/* Month, Product Type, and Product Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Month, Product Type, and Product</CardTitle>
        </CardHeader>
        <CardContent className='space-y-4'>
          {/* Month Selection */}
          <div className='space-y-2'>
            <Label htmlFor='month'>Month</Label>
            <MonthSelector
              selectedMonths={selectedMonths}
              onMonthsChange={handleMonthChange}
              multiple={true}
              label=''
            />
          </div>

          {/* Product Type Selection */}
          {selectedMonths.length > 0 && (
            <div className='space-y-2'>
              <Label htmlFor='product-type'>Product Type</Label>
              <Select value={selectedProductType} onValueChange={handleProductTypeChange}>
                <SelectTrigger id='product-type'>
                  <SelectValue placeholder='Select product type' />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value='razor'>Razor</SelectItem>
                  <SelectItem value='blade'>Blade</SelectItem>
                  <SelectItem value='brush'>Brush</SelectItem>
                  <SelectItem value='soap'>Soap</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Razor manufacturers: how did each brand do (Karve, Blackland, etc.) */}
          {selectedProductType === 'razor' && razorManufacturers.length > 0 && (
            <div className='space-y-2'>
              <Label>Razor manufacturers</Label>
              <p className='text-sm text-muted-foreground'>
                Total usage by brand for selected months. Users is the sum of unique users per model
                (may overcount if a user used multiple models from the same brand). Click a row to
                filter products below.
              </p>
              <div className='overflow-x-auto border rounded-md max-h-60 overflow-y-auto'>
                <table className='w-full border-collapse'>
                  <thead>
                    <tr className='bg-muted'>
                      <th className='border border-border p-2 text-left'>Manufacturer</th>
                      <th className='border border-border p-2 text-center'>Total uses</th>
                      <th className='border border-border p-2 text-center'>Users</th>
                      <th className='border border-border p-2 text-center'>Models</th>
                    </tr>
                  </thead>
                  <tbody>
                    {razorManufacturers.map(
                      ({ brand, usage_count, model_count, unique_users_sum }) => (
                        <tr
                          key={brand}
                          className='hover:bg-muted/70 cursor-pointer'
                          onClick={() => setProductSearch(brand)}
                        >
                          <td className='border border-border p-2 font-medium'>{brand}</td>
                          <td className='border border-border p-2 text-center'>
                            {usage_count.toLocaleString()}
                          </td>
                          <td className='border border-border p-2 text-center'>
                            {unique_users_sum.toLocaleString()}
                          </td>
                          <td className='border border-border p-2 text-center'>{model_count}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Product Selection */}
          {selectedMonths.length > 0 && selectedProductType && (
            <div className='space-y-2'>
              <Label htmlFor='product'>Product</Label>
              <div className='flex space-x-2'>
                <Input
                  id='product'
                  placeholder='Search for a product...'
                  value={productSearch}
                  onChange={e => setProductSearch(e.target.value)}
                  className='flex-1'
                />
              </div>

              {/* Product Suggestions */}
              {loading ? (
                <div className='flex items-center justify-center p-4'>
                  <Loader2 className='h-4 w-4 animate-spin' />
                </div>
              ) : filteredProducts.length > 0 ? (
                <div className='mt-2 space-y-1 max-h-60 overflow-y-auto'>
                  {filteredProducts.slice(0, 20).map(product => (
                    <div
                      key={product.key}
                      className='flex items-center justify-between p-2 hover:bg-muted rounded cursor-pointer'
                      onClick={() => handleProductSelect(product)}
                    >
                      <div className='flex flex-col'>
                        <span>
                          {product.brand} {product.model}
                        </span>
                        {selectedProductType === 'razor' && (
                          <span className='text-xs text-muted-foreground'>
                            Manufacturer: {product.brand}
                          </span>
                        )}
                      </div>
                      <div className='flex items-center space-x-2'>
                        <Badge variant='outline'>{product.usage_count} uses</Badge>
                        <Badge variant='outline'>{product.unique_users} users</Badge>
                      </div>
                    </div>
                  ))}
                  {filteredProducts.length > 20 && (
                    <div className='text-sm text-muted-foreground text-center'>
                      +{filteredProducts.length - 20} more products
                    </div>
                  )}
                </div>
              ) : (
                <div className='text-sm text-muted-foreground text-center p-4'>
                  No products found
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className='border-destructive'>
          <CardContent className='pt-6'>
            <div className='text-destructive text-center'>{error}</div>
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      {aggregatedAnalysis && (
        <Card>
          <CardHeader>
            <div className='flex flex-wrap items-center justify-between gap-2'>
              <div>
                <CardTitle>
                  Usage Analysis for {aggregatedAnalysis.product.brand} {aggregatedAnalysis.product.model} -{' '}
                  {selectedMonths.length === 1
                    ? selectedMonths[0]
                    : `${selectedMonths.length} months`}
                </CardTitle>
                {selectedProductType === 'razor' && (
                  <p className='text-sm text-muted-foreground mt-1'>
                    Manufacturer: {aggregatedAnalysis.product.brand}
                  </p>
                )}
              </div>

              {/* View Toggle */}
              <div className='flex flex-wrap items-center gap-2'>
                <Button
                  variant={viewMode === 'calendar' ? 'default' : 'outline'}
                  size='sm'
                  onClick={() => setViewMode('calendar')}
                >
                  <CalendarIcon className='h-4 w-4 mr-2' />
                  Calendar
                </Button>
                <Button
                  variant={viewMode === 'table' ? 'default' : 'outline'}
                  size='sm'
                  onClick={() => setViewMode('table')}
                >
                  <TableIcon className='h-4 w-4 mr-2' />
                  Table
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'outline'}
                  size='sm'
                  onClick={() => setViewMode('list')}
                >
                  <ListIcon className='h-4 w-4 mr-2' />
                  List
                </Button>
                <Button
                  variant={viewMode === 'summary' ? 'default' : 'outline'}
                  size='sm'
                  onClick={() => setViewMode('summary')}
                >
                  <SummaryIcon className='h-4 w-4 mr-2' />
                  Summary
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex items-center justify-center h-64'>
                <Loader2 className='h-8 w-8 animate-spin' />
              </div>
            ) : (
              <div>
                {viewMode === 'table' && renderTableView()}
                {viewMode === 'calendar' && renderCalendarView()}
                {viewMode === 'list' && renderListView()}
                {viewMode === 'summary' && (
                  yearlySummaryLoading ? (
                    <div className='flex items-center justify-center h-64'>
                      <Loader2 className='h-8 w-8 animate-spin' />
                    </div>
                  ) : (
                    renderSummaryView()
                  )
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Users Table - Always Visible */}
      {aggregatedAnalysis && aggregatedAnalysis.users.length > 0 && (
        <Card>
          <CardHeader>
            <div className='flex flex-wrap items-center justify-between gap-2'>
              <CardTitle>Users Who Used This Product</CardTitle>
              <div className='flex items-center gap-2'>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleCopyUserTableMarkdown(true)}
                  disabled={copyLoading['user-table-with-urls']}
                  className='flex items-center gap-2'
                >
                  {copyLoading['user-table-with-urls'] ? (
                    <Loader2 className='h-4 w-4 animate-spin' />
                  ) : copySuccess['user-table-with-urls'] ? (
                    <Check className='h-4 w-4' />
                  ) : (
                    <Copy className='h-4 w-4' />
                  )}
                  {copySuccess['user-table-with-urls'] ? 'Copied!' : 'Copy (with URLs)'}
                </Button>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => handleCopyUserTableMarkdown(false)}
                  disabled={copyLoading['user-table-no-urls']}
                  className='flex items-center gap-2'
                >
                  {copyLoading['user-table-no-urls'] ? (
                    <Loader2 className='h-4 w-4 animate-spin' />
                  ) : copySuccess['user-table-no-urls'] ? (
                    <Check className='h-4 w-4' />
                  ) : (
                    <Copy className='h-4 w-4' />
                  )}
                  {copySuccess['user-table-no-urls'] ? 'Copied!' : 'Copy (no URLs)'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className='overflow-x-auto'>
              <table className='w-full min-w-[768px] border-collapse border border-border'>
                <thead>
                  <tr className='bg-muted'>
                    <th className='border border-border p-2 text-center'>#</th>
                    <th className='border border-border p-2 text-left'>Username</th>
                    <th className='border border-border p-2 text-center'>Usage Count</th>
                    <th className='border border-border p-2 text-left'>Usage Dates</th>
                    <th className='hidden md:table-cell border border-border p-2 text-left'>Comment IDs</th>
                  </tr>
                </thead>
                <tbody>
                  {aggregatedAnalysis.users.map((user, userIndex) => {
                    const ordered = getOrderedDateCommentPairs(
                      user.comment_ids,
                      aggregatedAnalysis.comments_by_date
                    );
                    return (
                      <tr key={user.username} className='hover:bg-muted/50'>
                        <td className='border border-border p-2 text-center font-medium'>
                          {userIndex + 1}
                        </td>
                        <td className='border border-border p-2'>
                          <button
                            onClick={() => handleUsernameClick(user.username)}
                            className='text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium'
                            type='button'
                          >
                            {user.username}
                          </button>
                        </td>
                        <td className='border border-border p-2 text-center'>{user.usage_count}</td>
                        <td className='border border-border p-2'>
                          <CommentDisplay
                            commentIds={ordered.commentIds}
                            onCommentClick={commentId =>
                              handleCommentClick(commentId, user.comment_ids)
                            }
                            displayMode='dates'
                            dates={ordered.dates}
                            expanded={expandedUsers[user.username]}
                            onExpandChange={expanded =>
                              handleUserExpandChange(user.username, expanded)
                            }
                          />
                        </td>
                        <td className='hidden md:table-cell border border-border p-2'>
                          <CommentDisplay
                            commentIds={ordered.commentIds}
                            onCommentClick={commentId =>
                              handleCommentClick(commentId, user.comment_ids)
                            }
                            expanded={expandedUsers[user.username]}
                            onExpandChange={expanded =>
                              handleUserExpandChange(user.username, expanded)
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comment Modal */}
      <CommentModal
        comment={selectedComment}
        isOpen={commentModalOpen}
        onClose={handleCloseCommentModal}
        comments={allComments}
        currentIndex={currentCommentIndex}
        onNavigate={handleCommentNavigation}
        remainingCommentIds={remainingCommentIds}
      />
    </div>
  );
};

export default ProductUsage;


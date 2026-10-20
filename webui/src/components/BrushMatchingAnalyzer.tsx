import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Loader2, Search, Trophy, Target, Hash, Info, Split, Component } from 'lucide-react';

export interface BrushMatchingAnalyzerProps {
  /** Prefill / analyze this string (takes precedence over ?brush=). */
  initialBrushString?: string;
  /** When true (or when a brush source is present and unset), auto-run analysis once. */
  autoAnalyze?: boolean;
}

interface BrushMatchResult {
  strategy: string;
  score: number;
  matchType: string;
  pattern: string;
  scoreBreakdown: {
    baseScore: number;
    modifiers: number;
    modifierDetails: { name: string; weight: number; description: string }[];
    total?: number;
  };
  matchedData: {
    brand?: string;
    model?: string;
    fiber?: string;
    size?: string;
    handle?: {
      brand?: string;
      model?: string;
      source_text?: string;
    };
    knot?: {
      brand?: string;
      model?: string;
      fiber?: string;
      knot_size_mm?: number;
      source_text?: string;
    };
  };
  // Enhanced fields for detailed analysis
  componentDetails?: {
    handle?: {
      score: number;
      breakdown: Record<string, number>;
      metadata: Record<string, any>;
      patterns?: {
        brand_pattern?: string;
        model_pattern?: string;
        handle_pattern?: string;
        source?: string;
      };
    };
    knot?: {
      score: number;
      breakdown: Record<string, number>;
      metadata: Record<string, any>;
      patterns?: {
        brand_pattern?: string;
        model_pattern?: string;
        fiber_pattern?: string;
        size_pattern?: string;
        source?: string;
      };
    };
  };
  splitInformation?: {
    handleText: string;
    knotText: string;
    splitPriority?: string;
  };
}

interface InputParsing {
  fiber?: string | null;
  knot_size_mm?: number | null;
}

interface BrushAnalysisResponse {
  results: BrushMatchResult[];
  winner: BrushMatchResult;
  enrichedData?: any;
  inputParsing?: InputParsing;
}

function matchedFiberFromWinner(winner: BrushMatchResult): string | null {
  const data = winner.matchedData;
  if (!data) return null;
  if (data.fiber) return data.fiber;
  if (data.knot?.fiber) return data.knot.fiber;
  return null;
}

// Reusable component for displaying score breakdowns
function ScoreBreakdownDisplay({
  baseScore,
  modifiers,
  modifierDetails,
  total,
}: {
  baseScore: number;
  modifiers: number;
  modifierDetails: { name: string; weight: number; description: string }[];
  total?: number;
}) {
  const finalTotal = total ?? baseScore + modifiers;

  return (
    <div className='mb-4'>
      <h4 className='font-medium mb-2'>Score Breakdown</h4>
      <div className='grid grid-cols-3 gap-4 text-sm'>
        <div>
          <p className='text-gray-600'>Base Score</p>
          <p className='font-semibold'>{baseScore.toFixed(2)}</p>
          <p className='text-xs text-gray-500'>Strategy match</p>
        </div>
        <div>
          <p className='text-gray-600'>Modifiers</p>
          <p className='font-semibold'>
            {modifiers > 0 ? '+' : ''}
            {modifiers.toFixed(2)}
          </p>
          <p className='text-xs text-gray-500'>{modifiers > 0 ? 'Bonus points' : 'No bonuses'}</p>
        </div>
        <div>
          <p className='text-gray-600'>Total</p>
          <p className='font-semibold'>{finalTotal.toFixed(2)}</p>
          <p className='text-xs text-gray-500'>Final score</p>
        </div>
      </div>
    </div>
  );
}

// Reusable component for displaying modifier details
function ModifierDetailsDisplay({
  modifierDetails,
  modifiers,
}: {
  modifierDetails: { name: string; weight: number; description: string }[];
  modifiers: number;
}) {
  return (
    <div className='mb-4'>
      <h4 className='font-medium mb-2'>Modifier Details</h4>
      <div className='text-xs text-gray-600 mb-2 bg-gray-50 p-2 rounded'>
        <p className='font-medium'>About Modifiers:</p>
        <p>Modifiers can be bonuses (positive) or penalties (negative):</p>
        <ul className='list-disc list-inside ml-2 mt-1 space-y-1'>
          <li>Fiber type matches (badger, boar, synthetic)</li>
          <li>Size specifications (knot diameter)</li>
          <li>Handle material matches</li>
          <li>Brand/model confidence</li>
          <li>Pattern specificity</li>
          <li>Component matching success</li>
          <li>Brand balance (same brand penalty, multiple brands bonus)</li>
        </ul>
      </div>
      {modifierDetails.length > 0 ? (
        <div className='space-y-1'>
          {modifierDetails.map((detail, idx) => {
            const isPenalty = detail.weight < 0;
            const displayValue = detail.weight.toFixed(2);
            return (
              <div key={idx} className='text-sm text-gray-700 bg-gray-50 p-2 rounded'>
                <div className='flex justify-between items-center'>
                  <span className='font-medium'>{detail.name}</span>
                  <span
                    className={`font-semibold ${
                      isPenalty ? 'text-red-600' : 'text-green-600'
                    }`}
                  >
                    {displayValue}
                  </span>
                </div>
                <p className='text-xs text-gray-500 mt-1'>{detail.description}</p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className='text-sm text-gray-500 italic'>
          {modifiers > 0 ? (
            <>
              <p>Modifiers applied: +{modifiers.toFixed(2)}</p>
              <p className='text-xs mt-1'>(Detailed breakdown not available from backend)</p>
            </>
          ) : (
            <p>No modifiers applied</p>
          )}
        </div>
      )}
    </div>
  );
}

// Reusable component for displaying component details
function ComponentDetailsDisplay({
  componentDetails,
  splitInformation,
}: {
  componentDetails?: {
    handle?: {
      score: number;
      breakdown: Record<string, number>;
      metadata: Record<string, any>;
      patterns?: {
        brand_pattern?: string;
        model_pattern?: string;
        handle_pattern?: string;
        source?: string;
      };
    };
    knot?: {
      score: number;
      breakdown: Record<string, number>;
      metadata: Record<string, any>;
      patterns?: {
        brand_pattern?: string;
        model_pattern?: string;
        fiber_pattern?: string;
        size_pattern?: string;
        source?: string;
      };
    };
  };
  splitInformation?: { handleText: string; knotText: string; splitPriority?: string };
}) {
  if (!componentDetails && !splitInformation) return null;

  return (
    <div className='mb-4'>
      <h4 className='font-medium mb-2 flex items-center gap-2'>
        <Component className='w-4 h-4' />
        Component Analysis
      </h4>

      {/* Split Information */}
      {splitInformation && (
        <div className='mb-3 p-3 bg-blue-50 border border-blue-200 rounded'>
          <h5 className='font-medium text-sm text-blue-800 mb-2 flex items-center gap-2'>
            <Split className='w-4 h-4' />
            Split Information
          </h5>
          <div className='grid grid-cols-2 gap-4 text-sm'>
            <div>
              <p className='text-blue-600 font-medium'>Handle Text:</p>
              <p className='font-mono text-xs bg-white p-2 rounded border'>
                {splitInformation.handleText}
              </p>
            </div>
            <div>
              <p className='text-blue-600 font-medium'>Knot Text:</p>
              <p className='font-mono text-xs bg-white p-2 rounded border'>
                {splitInformation.knotText}
              </p>
            </div>
          </div>
          {splitInformation.splitPriority && (
            <div className='mt-2'>
              <p className='text-blue-600 font-medium'>Split Priority:</p>
              <Badge variant='outline' className='text-xs'>
                {splitInformation.splitPriority}
              </Badge>
            </div>
          )}
        </div>
      )}

      {/* Component Details */}
      {componentDetails && (
        <div className='space-y-3'>
          {/* Handle Component */}
          {componentDetails.handle && (
            <div className='p-3 bg-green-50 border border-green-200 rounded'>
              <h5 className='font-medium text-sm text-green-800 mb-2'>🖐️ Handle Component</h5>
              <div className='grid grid-cols-2 gap-4 text-sm'>
                <div>
                  <p className='text-green-600 font-medium'>Score:</p>
                  <p className='font-semibold'>{componentDetails.handle.score.toFixed(2)}</p>
                </div>
                <div>
                  <p className='text-green-600 font-medium'>Breakdown:</p>
                  <div className='space-y-1'>
                    {Object.entries(componentDetails.handle.breakdown).map(([key, value]) => (
                      <div key={key} className='flex justify-between text-xs'>
                        <span className='text-gray-600'>{key}:</span>
                        <span className='font-medium'>+{value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              {Object.keys(componentDetails.handle.metadata).length > 0 && (
                <div className='mt-2'>
                  <p className='text-green-600 font-medium text-xs'>Metadata:</p>
                  <div className='text-xs text-gray-700 bg-white p-2 rounded border mt-1'>
                    {Object.entries(componentDetails.handle.metadata).map(([key, value]) => (
                      <div key={key} className='flex justify-between'>
                        <span className='text-gray-600'>{key}:</span>
                        <span>{value || 'Not specified'}</span>
                      </div>
                    ))}
                    {/* Show pattern information inline */}
                    {componentDetails.handle.patterns?.brand_pattern && (
                      <div className='flex justify-between'>
                        <span className='text-gray-600'>pattern:</span>
                        <span className='font-mono'>
                          {componentDetails.handle.patterns.brand_pattern}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Knot Component */}
          {componentDetails.knot && (
            <div className='p-3 bg-purple-50 border border-purple-200 rounded'>
              <h5 className='font-medium text-sm text-purple-800 mb-2'>🧶 Knot Component</h5>
              <div className='grid grid-cols-2 gap-4 text-sm'>
                <div>
                  <p className='text-purple-600 font-medium'>Score:</p>
                  <p className='font-semibold'>{componentDetails.knot.score.toFixed(2)}</p>
                </div>
                <div>
                  <p className='text-purple-600 font-medium'>Breakdown:</p>
                  <div className='space-y-1'>
                    {Object.entries(componentDetails.knot.breakdown).map(([key, value]) => (
                      <div key={key} className='flex justify-between text-xs'>
                        <span className='text-gray-600'>{key}:</span>
                        <span className='font-medium'>+{value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              {Object.keys(componentDetails.knot.metadata).length > 0 && (
                <div className='mt-2'>
                  <p className='text-purple-600 font-medium text-xs'>Metadata:</p>
                  <div className='text-xs text-gray-700 bg-white p-2 rounded border mt-1'>
                    {Object.entries(componentDetails.knot.metadata).map(([key, value]) => (
                      <div key={key} className='flex justify-between'>
                        <span className='text-gray-600'>{key}:</span>
                        <span>{value || 'Not specified'}</span>
                      </div>
                    ))}
                    {/* Show pattern information inline */}
                    {componentDetails.knot.patterns?.brand_pattern && (
                      <div className='flex justify-between'>
                        <span className='text-gray-600'>pattern:</span>
                        <span className='font-mono'>
                          {componentDetails.knot.patterns.brand_pattern}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function BrushMatchingAnalyzer({
  initialBrushString,
  autoAnalyze,
}: BrushMatchingAnalyzerProps = {}) {
  const [searchParams] = useSearchParams();
  const brushFromQuery = searchParams.get('brush')?.trim() ?? '';
  const sourceBrush = useMemo(
    () => (initialBrushString?.trim() || brushFromQuery || '').trim(),
    [initialBrushString, brushFromQuery]
  );
  const shouldAutoAnalyze = autoAnalyze ?? Boolean(sourceBrush);

  const [brushString, setBrushString] = useState(sourceBrush);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<BrushAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bypassCorrectMatches, setBypassCorrectMatches] = useState(false);
  const autoRanForRef = useRef<string | null>(null);

  useEffect(() => {
    if (sourceBrush) {
      setBrushString(sourceBrush);
    }
  }, [sourceBrush]);

  const analyzeBrush = useCallback(
    async (value?: string) => {
      const target = (value ?? brushString).trim();
      if (!target) return;

      setIsAnalyzing(true);
      setError(null);
      setResults(null);

      try {
        // Use the API service for cache-busting and consistent error handling
        const response = await fetch(`/api/brushes/matching/analyze?_t=${Date.now()}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            Pragma: 'no-cache',
            Expires: '0',
          },
          body: JSON.stringify({
            brushString: target,
            bypass_correct_matches: bypassCorrectMatches,
          }),
        });

        if (!response.ok) {
          throw new Error(`Analysis failed: ${response.statusText}`);
        }

        const data = await response.json();
        setResults(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis failed');
      } finally {
        setIsAnalyzing(false);
      }
    },
    [brushString, bypassCorrectMatches]
  );

  useEffect(() => {
    if (!shouldAutoAnalyze || !sourceBrush) {
      return;
    }
    if (autoRanForRef.current === sourceBrush) {
      return;
    }
    autoRanForRef.current = sourceBrush;
    void analyzeBrush(sourceBrush);
  }, [shouldAutoAnalyze, sourceBrush, analyzeBrush]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      void analyzeBrush();
    }
  };

  const getStrategyIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className='w-4 h-4 text-yellow-500' />;
      case 2:
        return <Target className='w-4 h-4 text-gray-400' />;
      case 3:
        return <Hash className='w-4 h-4 text-orange-500' />;
      default:
        return <Hash className='w-4 h-4 text-gray-400' />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className='container mx-auto p-6 max-w-6xl'>
      <Card>
        <CardHeader>
          <CardTitle className='flex items-center gap-2'>
            <Search className='w-5 h-5' />
            Brush Matching Analyzer
          </CardTitle>
        </CardHeader>
        <CardContent className='space-y-6'>
          {/* Input Section */}
          <div className='mb-6'>
            <div className='flex items-center gap-4 mb-4'>
              <input
                type='text'
                value={brushString}
                onChange={e => setBrushString(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder='Enter brush string to analyze...'
                className='flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
              <button
                onClick={() => void analyzeBrush()}
                disabled={isAnalyzing || !brushString.trim()}
                className='px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>

            <div className='flex items-center gap-2'>
              <input
                type='checkbox'
                id='bypass-correct-matches'
                checked={bypassCorrectMatches}
                onChange={e => setBypassCorrectMatches(e.target.checked)}
                className='w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
              />
              <label htmlFor='bypass-correct-matches' className='text-sm text-gray-600'>
                Bypass correct_matches directory to see all strategies
              </label>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <Card className='border-red-200 bg-red-50'>
              <CardContent className='pt-6'>
                <p className='text-red-600'>{error}</p>
              </CardContent>
            </Card>
          )}

          {/* Results Display */}
          {results && (
            <div className='space-y-6'>
              {/* Parsed from input (fiber / knot size from text parsers) */}
              {results.inputParsing && (
                <Card className='border-blue-200 bg-blue-50'>
                  <CardHeader className='pb-2'>
                    <CardTitle className='flex items-center gap-2 text-blue-800 text-base'>
                      <Info className='w-4 h-4' />
                      Parsed from input
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className='grid grid-cols-2 gap-4 text-sm'>
                      <div>
                        <p className='text-gray-600'>Fiber</p>
                        <p className='font-semibold' data-testid='input-parsing-fiber'>
                          {results.inputParsing.fiber ?? 'none'}
                        </p>
                      </div>
                      <div>
                        <p className='text-gray-600'>Knot size</p>
                        <p className='font-semibold' data-testid='input-parsing-knot-size'>
                          {results.inputParsing.knot_size_mm != null
                            ? `${results.inputParsing.knot_size_mm}mm`
                            : 'none'}
                        </p>
                      </div>
                    </div>
                    {(() => {
                      const parsed = results.inputParsing.fiber ?? null;
                      const matched = matchedFiberFromWinner(results.winner);
                      if (parsed && matched && parsed !== matched) {
                        return (
                          <p
                            className='mt-3 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2'
                            data-testid='input-parsing-fiber-mismatch'
                          >
                            Parsed fiber ({parsed}) differs from matched fiber ({matched}). Catalog
                            or strategy default may be overriding the input text.
                          </p>
                        );
                      }
                      return null;
                    })()}
                  </CardContent>
                </Card>
              )}

              {/* Winner Section */}
              <Card className='border-green-200 bg-green-50'>
                <CardHeader>
                  <CardTitle className='flex items-center gap-2 text-green-800'>
                    <Trophy className='w-5 h-5' />
                    Winner: {results.winner.strategy.toUpperCase()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='grid grid-cols-2 gap-4'>
                    <div>
                      <p className='text-sm text-gray-600'>Strategy</p>
                      <p className='font-semibold'>{results.winner.strategy}</p>
                    </div>
                    <div>
                      <p className='text-sm text-gray-600'>Score</p>
                      <div className='flex items-baseline gap-2'>
                        <span
                          className={`font-bold text-2xl ${getScoreColor(results.winner.score)}`}
                        >
                          {results.winner.score.toFixed(2)}
                        </span>
                        {results.winner.scoreBreakdown.modifiers > 0 && (
                          <span className='text-sm text-green-600 font-medium'>
                            (+{results.winner.scoreBreakdown.modifiers.toFixed(2)})
                          </span>
                        )}
                      </div>
                      <div className='text-xs text-gray-500 mt-1'>
                        {results.winner.scoreBreakdown.baseScore.toFixed(2)} base +{' '}
                        {results.winner.scoreBreakdown.modifiers.toFixed(2)} modifiers
                      </div>
                    </div>
                    <div>
                      <p className='text-sm text-gray-600'>Match Type</p>
                      <p className='font-semibold'>{results.winner.matchType || 'None'}</p>
                    </div>
                    <div>
                      <p className='text-sm text-gray-600'>Pattern</p>
                      <p className='font-mono text-sm'>{results.winner.pattern}</p>
                    </div>
                  </div>

                  {/* Winner Matched Brush Details */}
                  {results.winner.matchedData && (
                    <div className='mt-4 p-3 bg-white border border-green-200 rounded'>
                      <h4 className='font-medium mb-2 flex items-center gap-2 text-green-800'>
                        <Target className='w-4 h-4' />
                        Matched Brush
                      </h4>
                      <div className='grid grid-cols-2 gap-4 text-sm'>
                        {/* Top-level brush info */}
                        {(results.winner.matchedData.brand || results.winner.matchedData.model) && (
                          <div>
                            <p className='text-gray-600 font-medium'>Brush:</p>
                            <p className='font-semibold text-green-800'>
                              {results.winner.matchedData.brand || 'Unknown Brand'}{' '}
                              {results.winner.matchedData.model || ''}
                            </p>
                            {results.winner.matchedData.fiber && (
                              <p className='text-xs text-gray-500'>
                                Fiber: {results.winner.matchedData.fiber}
                              </p>
                            )}
                            {results.winner.matchedData.size && (
                              <p className='text-xs text-gray-500'>
                                Size: {results.winner.matchedData.size}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Handle component */}
                        {results.winner.matchedData.handle && (
                          <div>
                            <p className='text-gray-600 font-medium'>Handle:</p>
                            <p className='font-semibold text-green-800'>
                              {results.winner.matchedData.handle.brand || 'Unknown Brand'}{' '}
                              {results.winner.matchedData.handle.model || ''}
                            </p>
                            {results.winner.matchedData.handle.source_text && (
                              <p className='text-xs text-gray-500'>
                                Source: {results.winner.matchedData.handle.source_text}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Knot component */}
                        {results.winner.matchedData.knot && (
                          <div>
                            <p className='text-gray-600 font-medium'>Knot:</p>
                            <p className='font-semibold text-green-800'>
                              {results.winner.matchedData.knot.brand || 'Unknown Brand'}{' '}
                              {results.winner.matchedData.knot.model || ''}
                            </p>
                            {results.winner.matchedData.knot.fiber && (
                              <p className='text-xs text-gray-500'>
                                Fiber: {results.winner.matchedData.knot.fiber}
                              </p>
                            )}
                            {results.winner.matchedData.knot.knot_size_mm && (
                              <p className='text-xs text-gray-500'>
                                Size: {results.winner.matchedData.knot.knot_size_mm}mm
                              </p>
                            )}
                            {results.winner.matchedData.knot.source_text && (
                              <p className='text-xs text-gray-500'>
                                Source: {results.winner.matchedData.knot.source_text}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* All Results */}
              <Card>
                <CardHeader>
                  <CardTitle>All Strategy Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    {results.results
                      .filter(result => {
                        // Filter out strategies with no valid matches
                        // Only check the strategy's own matchedData, not enrichedData
                        const hasValidData =
                          result.matchedData &&
                          (result.matchedData.brand ||
                            (result.matchedData.handle &&
                              (result.matchedData.handle.brand ||
                                result.matchedData.handle.model)) ||
                            (result.matchedData.knot &&
                              (result.matchedData.knot.brand ||
                                result.matchedData.knot.model ||
                                result.matchedData.knot.fiber)));

                        return hasValidData;
                      })
                      .map((result, index) => {
                        const isWinner = result.strategy === results.winner.strategy;
                        return (
                          <Card
                            key={result.strategy}
                            className={
                              isWinner ? 'border-green-200 bg-green-50' : 'border-gray-200'
                            }
                          >
                            <CardContent className='pt-6'>
                              <div className='flex items-center justify-between mb-4'>
                                <div className='flex items-center gap-2'>
                                  {isWinner ? (
                                    <Trophy className='w-4 h-4 text-yellow-500' />
                                  ) : (
                                    getStrategyIcon(index + 1)
                                  )}
                                  <Badge variant='outline' className='font-mono'>
                                    {isWinner ? 'WINNER' : `#${index + 1}`}
                                  </Badge>
                                  <h3 className='font-semibold text-lg'>
                                    {result.strategy.toUpperCase()}
                                  </h3>
                                  <Badge
                                    variant={isWinner ? 'default' : 'secondary'}
                                    className={
                                      isWinner
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-blue-100 text-blue-800'
                                    }
                                  >
                                    {isWinner ? '✓ Winner' : '✓ Matched'}
                                  </Badge>
                                </div>
                                <div className='text-right'>
                                  <div className='flex items-baseline gap-2 justify-end'>
                                    <span
                                      className={`text-2xl font-bold ${getScoreColor(result.score)}`}
                                    >
                                      {result.score.toFixed(2)}
                                    </span>
                                    {result.scoreBreakdown.modifiers > 0 && (
                                      <span className='text-sm text-green-600 font-medium'>
                                        (+{result.scoreBreakdown.modifiers.toFixed(2)})
                                      </span>
                                    )}
                                  </div>
                                  <p className='text-sm text-gray-600'>
                                    {result.matchType || 'None'}
                                  </p>
                                  <p className='text-xs text-gray-500'>
                                    {result.scoreBreakdown.baseScore.toFixed(2)} +{' '}
                                    {result.scoreBreakdown.modifiers.toFixed(2)}
                                  </p>
                                </div>
                              </div>

                              {/* Matched Brush Details */}
                              {result.matchedData && (
                                <div className='mb-4 p-3 bg-gray-50 border border-gray-200 rounded'>
                                  <h4 className='font-medium mb-2 flex items-center gap-2'>
                                    <Target className='w-4 h-4' />
                                    Matched Brush
                                  </h4>
                                  <div className='grid grid-cols-2 gap-4 text-sm'>
                                    {/* Top-level brush info */}
                                    {(result.matchedData.brand || result.matchedData.model) && (
                                      <div>
                                        <p className='text-gray-600 font-medium'>Brush:</p>
                                        <p className='font-semibold'>
                                          {result.matchedData.brand || 'Unknown Brand'}{' '}
                                          {result.matchedData.model || ''}
                                        </p>
                                        {result.matchedData.fiber && (
                                          <p className='text-xs text-gray-500'>
                                            Fiber: {result.matchedData.fiber}
                                          </p>
                                        )}
                                        {result.matchedData.size && (
                                          <p className='text-xs text-gray-500'>
                                            Size: {result.matchedData.size}
                                          </p>
                                        )}
                                      </div>
                                    )}

                                    {/* Handle component */}
                                    {result.matchedData.handle && (
                                      <div>
                                        <p className='text-gray-600 font-medium'>Handle:</p>
                                        <p className='font-semibold'>
                                          {result.matchedData.handle.brand || 'Unknown Brand'}{' '}
                                          {result.matchedData.handle.model || ''}
                                        </p>
                                        {result.matchedData.handle.source_text && (
                                          <p className='text-xs text-gray-500'>
                                            Source: {result.matchedData.handle.source_text}
                                          </p>
                                        )}
                                      </div>
                                    )}

                                    {/* Knot component */}
                                    {result.matchedData.knot && (
                                      <div>
                                        <p className='text-gray-600 font-medium'>Knot:</p>
                                        <p className='font-semibold'>
                                          {result.matchedData.knot.brand || 'Unknown Brand'}{' '}
                                          {result.matchedData.knot.model || ''}
                                        </p>
                                        {result.matchedData.knot.fiber && (
                                          <p className='text-xs text-gray-500'>
                                            Fiber: {result.matchedData.knot.fiber}
                                          </p>
                                        )}
                                        {result.matchedData.knot.knot_size_mm && (
                                          <p className='text-xs text-gray-500'>
                                            Size: {result.matchedData.knot.knot_size_mm}mm
                                          </p>
                                        )}
                                        {result.matchedData.knot.source_text && (
                                          <p className='text-xs text-gray-500'>
                                            Source: {result.matchedData.knot.source_text}
                                          </p>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Score Breakdown - Reusable Component */}
                              <ScoreBreakdownDisplay
                                baseScore={result.scoreBreakdown.baseScore}
                                modifiers={result.scoreBreakdown.modifiers}
                                modifierDetails={result.scoreBreakdown.modifierDetails}
                                total={result.scoreBreakdown.total}
                              />

                              {/* Modifier Details - Reusable Component */}
                              <ModifierDetailsDisplay
                                modifierDetails={result.scoreBreakdown.modifierDetails}
                                modifiers={result.scoreBreakdown.modifiers}
                              />

                              {/* Component Details - Reusable Component */}
                              <ComponentDetailsDisplay
                                componentDetails={result.componentDetails}
                                splitInformation={result.splitInformation}
                              />
                            </CardContent>
                          </Card>
                        );
                      })}

                    {/* Non-Matching Strategies */}
                    {results.results
                      .filter(result => {
                        // Filter for strategies with no valid matches
                        // Only check the strategy's own matchedData, not enrichedData
                        const hasValidData =
                          result.matchedData &&
                          (result.matchedData.brand ||
                            (result.matchedData.handle &&
                              (result.matchedData.handle.brand ||
                                result.matchedData.handle.model)) ||
                            (result.matchedData.knot &&
                              (result.matchedData.knot.brand ||
                                result.matchedData.knot.model ||
                                result.matchedData.knot.fiber)));

                        return !hasValidData;
                      })
                      .map((result, index) => {
                        const matchingCount = results.results.filter(r => {
                          const hasValidData =
                            r.matchedData &&
                            (r.matchedData.brand ||
                              (r.matchedData.handle &&
                                (r.matchedData.handle.brand || r.matchedData.handle.model)) ||
                              (r.matchedData.knot &&
                                (r.matchedData.knot.brand ||
                                  r.matchedData.knot.model ||
                                  r.matchedData.knot.fiber)));
                          return hasValidData;
                        }).length;

                        return (
                          <Card key={result.strategy} className='border-gray-200 bg-gray-50'>
                            <CardContent className='pt-6'>
                              <div className='flex items-center justify-between mb-4'>
                                <div className='flex items-center gap-2'>
                                  <Hash className='w-4 h-4 text-gray-400' />
                                  <Badge variant='outline' className='font-mono text-gray-500'>
                                    #{matchingCount + index + 1}
                                  </Badge>
                                  <h3 className='font-semibold text-lg text-gray-600'>
                                    {result.strategy.toUpperCase()}
                                  </h3>
                                  <Badge variant='secondary' className='bg-red-100 text-red-800'>
                                    ✗ No Match
                                  </Badge>
                                </div>
                                <div className='text-right'>
                                  <div className='flex items-baseline gap-2 justify-end'>
                                    <span className='text-2xl font-bold text-gray-400'>
                                      {result.score.toFixed(2)}
                                    </span>
                                    {result.scoreBreakdown.modifiers > 0 && (
                                      <span className='text-sm text-gray-500 font-medium'>
                                        (+{result.scoreBreakdown.modifiers.toFixed(2)})
                                      </span>
                                    )}
                                  </div>
                                  <p className='text-sm text-gray-500'>
                                    {result.matchType || 'None'}
                                  </p>
                                  <p className='text-xs text-gray-400'>
                                    {result.scoreBreakdown.baseScore.toFixed(2)} +{' '}
                                    {result.scoreBreakdown.modifiers.toFixed(2)}
                                  </p>
                                </div>
                              </div>

                              {/* Score Breakdown for Non-Matching Strategies */}
                              <ScoreBreakdownDisplay
                                baseScore={result.scoreBreakdown.baseScore}
                                modifiers={result.scoreBreakdown.modifiers}
                                modifierDetails={result.scoreBreakdown.modifierDetails}
                                total={result.scoreBreakdown.total}
                              />

                              {/* Modifier Details for Non-Matching Strategies */}
                              <ModifierDetailsDisplay
                                modifierDetails={result.scoreBreakdown.modifierDetails}
                                modifiers={result.scoreBreakdown.modifiers}
                              />

                              {/* Component Details for Non-Matching Strategies */}
                              <ComponentDetailsDisplay
                                componentDetails={result.componentDetails}
                                splitInformation={result.splitInformation}
                              />

                              {/* No Match Explanation */}
                              <div className='mt-4 p-3 bg-red-50 border border-red-200 rounded'>
                                <h4 className='font-medium text-sm text-red-800 mb-2'>
                                  Why No Match?
                                </h4>
                                <div className='text-sm text-red-700 space-y-1'>
                                  <p>This strategy failed to produce a valid match because:</p>
                                  <ul className='list-disc list-inside ml-4 space-y-1'>
                                    <li>No matching patterns found in the catalog</li>
                                    <li>Pattern matching failed for the input text</li>
                                    <li>
                                      Required fields (brand, model, etc.) could not be extracted
                                    </li>
                                    <li>Strategy-specific logic rejected the input</li>
                                  </ul>
                                  <p className='text-xs text-red-600 mt-2'>
                                    Score: {result.score.toFixed(2)} (below threshold or invalid result)
                                  </p>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                  </div>
                </CardContent>
              </Card>

              {/* Enriched Data */}
              {results.enrichedData && (
                <Card>
                  <CardHeader>
                    <CardTitle>Enriched Data</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className='bg-gray-100 p-4 rounded text-sm overflow-x-auto'>
                      {JSON.stringify(results.enrichedData, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

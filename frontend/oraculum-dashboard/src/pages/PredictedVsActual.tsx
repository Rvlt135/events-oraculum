import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { UpgradeModal } from '../components/UpgradeModal';
import historyData from '../mocks/history.json';
import { ArrowLeft, CheckCircle, XCircle, TrendingUp, Target, Lock } from 'lucide-react';

export function PredictedVsActual() {
  const [selectedPeriod, setSelectedPeriod] = useState<7 | 30 | 90>(7);
  const [showUpgrade, setShowUpgrade] = useState(false);

  const { plan, canAccessHistoryDays } = usePlanStore();

  const filteredHistory = useMemo(() => {
    const now = new Date();
    const cutoffDate = new Date(now.getTime() - selectedPeriod * 24 * 60 * 60 * 1000);

    let filtered = historyData.filter((item) => {
      const itemDate = new Date(item.date);
      return itemDate >= cutoffDate;
    });

    if (!canAccessHistoryDays(selectedPeriod)) {
      const threeDaysCutoff = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
      filtered = historyData.filter((item) => {
        const itemDate = new Date(item.date);
        return itemDate >= threeDaysCutoff;
      });
    }

    return filtered;
  }, [selectedPeriod, canAccessHistoryDays]);

  const stats = useMemo(() => {
    const total = filteredHistory.length;
    const hits = filteredHistory.filter((item) => item.hit).length;
    const accuracy = total > 0 ? (hits / total) * 100 : 0;

    const avgEdge = filteredHistory.reduce((sum, item) => sum + item.edgeAtPrediction, 0) / total || 0;

    const highEdgeItems = filteredHistory.filter((item) => item.edgeAtPrediction >= 7.5);
    const highEdgeHits = highEdgeItems.filter((item) => item.hit).length;
    const highEdgeAccuracy = highEdgeItems.length > 0 ? (highEdgeHits / highEdgeItems.length) * 100 : 0;

    return {
      total,
      hits,
      accuracy,
      avgEdge,
      highEdgeAccuracy,
    };
  }, [filteredHistory]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handlePeriodChange = (period: 7 | 30 | 90) => {
    if (!canAccessHistoryDays(period)) {
      setShowUpgrade(true);
      return;
    }
    setSelectedPeriod(period);
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <div>
        <h1 className="text-3xl font-bold mb-2">Predicted vs Actual</h1>
        <p className="text-muted-foreground">
          Track prediction accuracy and performance over time
        </p>
      </div>

      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Time Period</h3>
          {plan === 'free' && (
            <span className="text-xs text-muted-foreground">Free: Last 3 days only</span>
          )}
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((days) => {
            const isLocked = !canAccessHistoryDays(days);
            return (
              <button
                key={days}
                onClick={() => handlePeriodChange(days as 7 | 30 | 90)}
                className={`px-4 py-2 rounded-md border transition-colors ${
                  selectedPeriod === days && !isLocked
                    ? 'bg-primary text-white border-primary'
                    : isLocked
                    ? 'bg-muted text-muted-foreground border-muted cursor-not-allowed'
                    : 'bg-white hover:bg-secondary border-border'
                }`}
              >
                <span className="flex items-center gap-1">
                  {days} days
                  {isLocked && <Lock className="h-3 w-3" />}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2 text-muted-foreground">
            <Target className="h-5 w-5" />
            <span className="text-sm font-medium">Total Predictions</span>
          </div>
          <div className="text-3xl font-bold">{stats.total}</div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2 text-muted-foreground">
            <CheckCircle className="h-5 w-5" />
            <span className="text-sm font-medium">Accuracy</span>
          </div>
          <div className="text-3xl font-bold text-green-600">{stats.accuracy.toFixed(1)}%</div>
          <div className="text-xs text-muted-foreground mt-1">
            {stats.hits} / {stats.total} correct
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2 text-muted-foreground">
            <TrendingUp className="h-5 w-5" />
            <span className="text-sm font-medium">Avg Edge Score</span>
          </div>
          <div className="text-3xl font-bold">{stats.avgEdge.toFixed(1)}</div>
        </div>

        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2 text-muted-foreground">
            <TrendingUp className="h-5 w-5" />
            <span className="text-sm font-medium">High Edge Accuracy</span>
          </div>
          <div className="text-3xl font-bold text-blue-600">{stats.highEdgeAccuracy.toFixed(1)}%</div>
          <div className="text-xs text-muted-foreground mt-1">Edge ≥ 7.5</div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold mb-4">Prediction History</h3>
        <div className="space-y-3">
          {filteredHistory.map((item) => (
            <div
              key={item.id}
              className={`border rounded-lg p-4 ${
                item.hit ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {item.hit ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    <span className="text-xs font-medium text-muted-foreground bg-white px-2 py-1 rounded">
                      {item.league}
                    </span>
                    <span className="text-xs font-medium text-muted-foreground">
                      Edge: {item.edgeAtPrediction.toFixed(1)}
                    </span>
                  </div>
                  <div className="font-semibold">{item.teams}</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {formatDate(item.date)} • Final: {item.finalScore}
                  </div>
                </div>

                <div className="flex flex-col md:flex-row gap-4 md:items-center">
                  <div className="text-sm">
                    <div className="text-muted-foreground mb-1">Predicted</div>
                    <div className={`font-medium px-2 py-1 rounded ${
                      item.predicted === 'home' ? 'bg-blue-100 text-blue-800' :
                      item.predicted === 'draw' ? 'bg-slate-100 text-slate-800' :
                      'bg-amber-100 text-amber-800'
                    }`}>
                      {item.predicted.toUpperCase()}
                    </div>
                  </div>

                  <div className="text-sm">
                    <div className="text-muted-foreground mb-1">Actual</div>
                    <div className={`font-medium px-2 py-1 rounded ${
                      item.actual === 'home' ? 'bg-blue-100 text-blue-800' :
                      item.actual === 'draw' ? 'bg-slate-100 text-slate-800' :
                      'bg-amber-100 text-amber-800'
                    }`}>
                      {item.actual.toUpperCase()}
                    </div>
                  </div>

                  <div className="text-sm font-bold">
                    {item.hit ? (
                      <span className="text-green-600">✓ HIT</span>
                    ) : (
                      <span className="text-red-600">✗ MISS</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {filteredHistory.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No prediction history available for this period
            </div>
          )}
        </div>
      </div>

      <UpgradeModal
        isOpen={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        feature="unlimited historical data"
      />
    </div>
  );
}

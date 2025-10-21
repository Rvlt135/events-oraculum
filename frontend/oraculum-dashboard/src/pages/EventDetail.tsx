import { useState, useMemo } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { EdgeBadge } from '../components/EdgeBadge';
import { UpgradeModal } from '../components/UpgradeModal';
import { usePlanStore } from '../store/planStore';
import eventDetailsData from '../mocks/event_detail.json';
import historyDetailsData from '../mocks/history_details.json';
import { Calendar, ArrowLeft, Lock, TrendingUp, CloudRain, Users, CheckCircle2, XCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

type EventDetails = {
  id: string;
  league: string;
  sport: string;
  home: string;
  away: string;
  kickoff: string;
  edgeScore: number;
  reasoningSummary: string;
  reasoningFull: string;
  verdict: string;
  oddsSeries: Array<{ timestamp: string; home: number; draw?: number; away: number }>;
  context: {
    weather: string;
    injuries: { home: string[]; away: string[] };
    recentForm: { home: string; away: string };
    headToHead: string;
  };
  aiConsensus: {
    homePercent: number;
    drawPercent: number;
    awayPercent: number;
    models: Array<{ name: string; pick: string; confidence: number; note: string }>;
  };
};

export function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<'odds' | 'reasoning' | 'context' | 'voting'>('odds');
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgradeFeature, setUpgradeFeature] = useState('');

  const { canAccessFullReasoning, canAccessFullVoting } = usePlanStore();

  const isHistoryPage = location.pathname.startsWith('/history/');

  const event: EventDetails | undefined = useMemo(() => {
    if (isHistoryPage) {
      return (historyDetailsData as any[]).find((e: any) => e.id === id) as EventDetails | undefined;
    }
    return (eventDetailsData as Record<string, EventDetails>)[id || ''];
  }, [id, isHistoryPage]);

  if (!event) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Event not found</p>
          <Link to={isHistoryPage ? '/history' : '/'} className="text-primary hover:underline mt-4 inline-block">
            Back to {isHistoryPage ? 'History' : 'Dashboard'}
          </Link>
        </div>
      </div>
    );
  }

  const isHistoricalEvent = (event as any).status === 'finished';
  const homeTeam = event.home || (event as any).teams?.home || '';
  const awayTeam = event.away || (event as any).teams?.away || '';

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const oddsChartData = event.oddsSeries.map((item) => ({
    date: new Date(item.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Home: item.home,
    Draw: item.draw,
    Away: item.away,
  }));

  const pieData = [
    { name: 'Home', value: event.aiConsensus.homePercent, color: '#0ea5e9' },
    { name: 'Draw', value: event.aiConsensus.drawPercent, color: '#94a3b8' },
    { name: 'Away', value: event.aiConsensus.awayPercent, color: '#f59e0b' },
  ];

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'win': return 'bg-green-100 text-green-800 border-green-300';
      case 'lose': return 'bg-red-100 text-red-800 border-red-300';
      case 'draw': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'risky': return 'bg-amber-100 text-amber-800 border-amber-300';
      default: return 'bg-secondary text-secondary-foreground';
    }
  };

  const handleReasoningTabClick = () => {
    if (!canAccessFullReasoning()) {
      setUpgradeFeature('full reasoning and analysis');
      setShowUpgrade(true);
    } else {
      setActiveTab('reasoning');
    }
  };

  const handleVotingTabClick = () => {
    if (!canAccessFullVoting()) {
      setUpgradeFeature('AI model voting breakdown');
      setShowUpgrade(true);
    } else {
      setActiveTab('voting');
    }
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <Link to={isHistoryPage ? '/history' : '/'} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Back to {isHistoryPage ? 'History' : 'Dashboard'}
      </Link>

      {isHistoricalEvent && (
        <div className={`bg-white border rounded-lg p-4 ${(event as any).hit ? 'border-green-300' : 'border-red-300'}`}>
          <div className="flex items-center gap-3">
            {(event as any).hit ? (
              <CheckCircle2 className="h-6 w-6 text-green-600" />
            ) : (
              <XCircle className="h-6 w-6 text-red-600" />
            )}
            <div className="flex-1">
              <div className="font-semibold">
                {(event as any).hit ? 'Prediction Hit ✓' : 'Prediction Miss ✗'}
              </div>
              <div className="text-sm text-muted-foreground mt-1">
                Predicted: <span className="font-medium">{(event as any).predicted}</span> |
                Actual: <span className="font-medium">{(event as any).actual}</span> |
                Final Score: <span className="font-medium">{(event as any).finalScore}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-muted-foreground bg-secondary px-2 py-1 rounded">
                {event.league}
              </span>
              <EdgeBadge score={event.edgeScore} />
            </div>
            <h1 className="text-3xl font-bold">
              {homeTeam} vs {awayTeam}
            </h1>
            <div className="flex items-center gap-2 mt-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>{formatDate(event.kickoff)}</span>
            </div>
          </div>

          <div className={`px-4 py-2 rounded-lg border font-medium ${getVerdictColor(event.verdict)}`}>
            Verdict: {event.verdict.toUpperCase()}
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-lg">
        <div className="border-b">
          <div className="flex overflow-x-auto">
            <button
              onClick={() => setActiveTab('odds')}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activeTab === 'odds'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              Odds Dynamics
            </button>
            <button
              onClick={handleReasoningTabClick}
              className={`px-6 py-3 font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'reasoning'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              Reasoning
              {!canAccessFullReasoning() && <Lock className="h-3 w-3" />}
            </button>
            <button
              onClick={() => setActiveTab('context')}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activeTab === 'context'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              Context
            </button>
            <button
              onClick={handleVotingTabClick}
              className={`px-6 py-3 font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'voting'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              AI Voting
              {!canAccessFullVoting() && <Lock className="h-3 w-3" />}
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === 'odds' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-4">Odds Movement</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={oddsChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="Home" stroke="#0ea5e9" strokeWidth={2} />
                    {event.oddsSeries[0].draw && (
                      <Line type="monotone" dataKey="Draw" stroke="#94a3b8" strokeWidth={2} />
                    )}
                    <Line type="monotone" dataKey="Away" stroke="#f59e0b" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4">
                  <div className="text-sm text-muted-foreground mb-1">Home Win</div>
                  <div className="text-2xl font-bold">
                    {event.oddsSeries[event.oddsSeries.length - 1].home}
                  </div>
                </div>
                {event.oddsSeries[0].draw && (
                  <div className="border rounded-lg p-4">
                    <div className="text-sm text-muted-foreground mb-1">Draw</div>
                    <div className="text-2xl font-bold">
                      {event.oddsSeries[event.oddsSeries.length - 1].draw}
                    </div>
                  </div>
                )}
                <div className="border rounded-lg p-4">
                  <div className="text-sm text-muted-foreground mb-1">Away Win</div>
                  <div className="text-2xl font-bold">
                    {event.oddsSeries[event.oddsSeries.length - 1].away}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'reasoning' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Summary
                </h4>
                <p className="text-sm">{event.reasoningSummary}</p>
              </div>

              {canAccessFullReasoning() ? (
                <div>
                  <h4 className="font-semibold mb-2">Full Analysis</h4>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {event.reasoningFull}
                  </p>
                </div>
              ) : (
                <div className="border-2 border-dashed rounded-lg p-8 text-center">
                  <Lock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <h4 className="font-semibold mb-2">Full Analysis Locked</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Upgrade to Pro to access detailed reasoning and analysis
                  </p>
                  <button
                    onClick={() => {
                      setUpgradeFeature('full reasoning and analysis');
                      setShowUpgrade(true);
                    }}
                    className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
                  >
                    Upgrade to Pro
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'context' && (
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <CloudRain className="h-5 w-5" />
                  Weather Conditions
                </h4>
                <p className="text-sm text-muted-foreground">{event.context.weather}</p>
              </div>

              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Injuries & Availability
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <div className="font-medium mb-2">{event.home}</div>
                    {event.context.injuries.home.length > 0 ? (
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {event.context.injuries.home.map((injury, i) => (
                          <li key={i}>• {injury}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No injuries reported</p>
                    )}
                  </div>
                  <div className="border rounded-lg p-4">
                    <div className="font-medium mb-2">{event.away}</div>
                    {event.context.injuries.away.length > 0 ? (
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {event.context.injuries.away.map((injury, i) => (
                          <li key={i}>• {injury}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No injuries reported</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4">
                  <h5 className="font-medium mb-2">Recent Form</h5>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">{event.home}:</span>
                      <span className="ml-2 font-mono">{event.context.recentForm.home}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{event.away}:</span>
                      <span className="ml-2 font-mono">{event.context.recentForm.away}</span>
                    </div>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <h5 className="font-medium mb-2">Head to Head</h5>
                  <p className="text-sm text-muted-foreground">{event.context.headToHead}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'voting' && (
            <div className="space-y-6">
              {canAccessFullVoting() ? (
                <>
                  <div>
                    <h4 className="font-semibold mb-4">AI Consensus Distribution</h4>
                    <div className="flex flex-col md:flex-row items-center gap-8">
                      <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, value }) => `${name}: ${value}%`}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>

                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Home Win</span>
                          <span className="font-bold">{event.aiConsensus.homePercent}%</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${event.aiConsensus.homePercent}%` }}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-sm">Draw</span>
                          <span className="font-bold">{event.aiConsensus.drawPercent}%</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div
                            className="bg-slate-400 h-2 rounded-full"
                            style={{ width: `${event.aiConsensus.drawPercent}%` }}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-sm">Away Win</span>
                          <span className="font-bold">{event.aiConsensus.awayPercent}%</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div
                            className="bg-amber-500 h-2 rounded-full"
                            style={{ width: `${event.aiConsensus.awayPercent}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold mb-3">Model Predictions</h4>
                    <div className="space-y-3">
                      {event.aiConsensus.models.map((model, i) => (
                        <div key={i} className="border rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium">{model.name}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-muted-foreground">
                                Confidence: {(model.confidence * 100).toFixed(0)}%
                              </span>
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                model.pick === 'home' ? 'bg-blue-100 text-blue-800' :
                                model.pick === 'draw' ? 'bg-slate-100 text-slate-800' :
                                'bg-amber-100 text-amber-800'
                              }`}>
                                {model.pick.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <p className="text-sm text-muted-foreground">{model.note}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="border-2 border-dashed rounded-lg p-8 text-center">
                  <Lock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <h4 className="font-semibold mb-2">AI Voting Details Locked</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    Basic consensus: {event.aiConsensus.homePercent}% Home / {event.aiConsensus.drawPercent}% Draw / {event.aiConsensus.awayPercent}% Away
                  </p>
                  <p className="text-sm text-muted-foreground mb-4">
                    Upgrade to Pro to see individual model predictions and confidence scores
                  </p>
                  <button
                    onClick={() => {
                      setUpgradeFeature('AI model voting breakdown');
                      setShowUpgrade(true);
                    }}
                    className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
                  >
                    Upgrade to Pro
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <UpgradeModal
        isOpen={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        feature={upgradeFeature}
      />
    </div>
  );
}

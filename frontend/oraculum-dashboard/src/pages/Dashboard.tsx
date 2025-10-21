import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FiltersBar } from '../components/FiltersBar';
import { EdgeBadge } from '../components/EdgeBadge';
import eventsData from '../mocks/events.json';
import { Calendar, TrendingUp, Lock } from 'lucide-react';
import { usePlanStore } from '../store/planStore';
import { UpgradeModal } from '../components/UpgradeModal';

export function Dashboard() {
  const [selectedSport, setSelectedSport] = useState('all');
  const [selectedLeague, setSelectedLeague] = useState('All Leagues');
  const [minEdge, setMinEdge] = useState(0);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgradeFeature, setUpgradeFeature] = useState('');

  const { user, canAccessSport } = usePlanStore();
  const planType = user?.plan_type || 'free';

  const filteredEvents = useMemo(() => {
    return eventsData
      .filter((event) => {
        if (selectedSport !== 'all' && event.sport !== selectedSport) return false;
        if (selectedLeague !== 'All Leagues' && event.league !== selectedLeague) return false;
        if (event.edgeScore < minEdge) return false;
        return canAccessSport(event.sport);
      })
      .slice(0, planType === 'free' ? 20 : 100);
  }, [selectedSport, selectedLeague, minEdge, planType, canAccessSport]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleConsensusClick = (e: React.MouseEvent) => {
    if (planType === 'free') {
      e.preventDefault();
      setUpgradeFeature('full AI consensus voting breakdown');
      setShowUpgrade(true);
    }
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Events Dashboard</h1>
        <p className="text-muted-foreground">
          AI-powered betting insights across {planType === 'pro' || planType === 'partner' ? 'multiple sports' : 'soccer'}
        </p>
      </div>

      <FiltersBar
        selectedSport={selectedSport}
        onSportChange={setSelectedSport}
        selectedLeague={selectedLeague}
        onLeagueChange={setSelectedLeague}
        minEdge={minEdge}
        onMinEdgeChange={setMinEdge}
      />

      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            Upcoming Events ({filteredEvents.length})
          </h2>
          {planType === 'free' && (
            <span className="text-xs text-muted-foreground">
              Showing max 20 events (Free plan)
            </span>
          )}
        </div>

        <div className="space-y-3">
          {filteredEvents.map((event) => (
            <Link
              key={event.id}
              to={`/event/${event.id}`}
              className="block border rounded-lg p-4 hover:shadow-md transition-all hover:border-primary/50"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-muted-foreground bg-secondary px-2 py-1 rounded">
                      {event.league}
                    </span>
                    <EdgeBadge score={event.edgeScore} />
                  </div>
                  <div className="font-semibold text-lg">
                    {event.home} vs {event.away}
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {formatDate(event.kickoff)}
                    </span>
                  </div>
                </div>

                <div className="flex flex-col md:flex-row gap-4 md:items-center">
                  <div className="text-sm">
                    <div className="text-muted-foreground mb-1">Best Odds</div>
                    <div className="flex gap-3 font-mono font-medium">
                      <span>H: {event.bestOdds.home}</span>
                      {event.bestOdds.draw && <span>D: {event.bestOdds.draw}</span>}
                      <span>A: {event.bestOdds.away}</span>
                    </div>
                  </div>

                  <div className="text-sm min-w-[120px]">
                    <div
                      className="text-muted-foreground mb-1 flex items-center gap-1 cursor-pointer"
                      onClick={planType === 'free' ? handleConsensusClick : undefined}
                    >
                      <TrendingUp className="h-4 w-4" />
                      AI Consensus
                      {planType === 'free' && <Lock className="h-3 w-3" />}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {(planType === 'pro' || planType === 'partner') ? 'Click for details' : 'Upgrade for details'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t text-sm text-muted-foreground">
                {event.reasoningSummary}
              </div>
            </Link>
          ))}

          {filteredEvents.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No events match your filters
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

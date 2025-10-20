import { usePlanStore } from '../store/planStore';
import { Lock } from 'lucide-react';

interface FiltersBarProps {
  selectedSport: string;
  onSportChange: (sport: string) => void;
  selectedLeague: string;
  onLeagueChange: (league: string) => void;
  minEdge: number;
  onMinEdgeChange: (edge: number) => void;
}

const SPORTS = [
  { id: 'all', label: 'All Sports', restricted: false },
  { id: 'soccer', label: 'Soccer', restricted: false },
  { id: 'basketball', label: 'Basketball', restricted: true },
  { id: 'tennis', label: 'Tennis', restricted: true },
  { id: 'hockey', label: 'Hockey', restricted: true },
];

const LEAGUES = [
  'All Leagues',
  'Premier League',
  'La Liga',
  'Bundesliga',
  'Serie A',
  'Ligue 1',
];

export function FiltersBar({
  selectedSport,
  onSportChange,
  selectedLeague,
  onLeagueChange,
  minEdge,
  onMinEdgeChange,
}: FiltersBarProps) {
  const { canAccessSport } = usePlanStore();

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Sport</label>
          <div className="flex flex-wrap gap-2">
            {SPORTS.map((sport) => {
              const isLocked = sport.restricted && !canAccessSport(sport.id);
              return (
                <button
                  key={sport.id}
                  onClick={() => !isLocked && onSportChange(sport.id)}
                  disabled={isLocked}
                  className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                    selectedSport === sport.id
                      ? 'bg-primary text-white border-primary'
                      : isLocked
                      ? 'bg-muted text-muted-foreground border-muted cursor-not-allowed'
                      : 'bg-white hover:bg-secondary border-border'
                  }`}
                >
                  <span className="flex items-center gap-1">
                    {sport.label}
                    {isLocked && <Lock className="h-3 w-3" />}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">League</label>
          <select
            value={selectedLeague}
            onChange={(e) => onLeagueChange(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border rounded-md bg-white"
          >
            {LEAGUES.map((league) => (
              <option key={league} value={league}>
                {league}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Min Edge Score: {minEdge.toFixed(1)}
          </label>
          <input
            type="range"
            min="0"
            max="10"
            step="0.5"
            value={minEdge}
            onChange={(e) => onMinEdgeChange(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>0</span>
            <span>10</span>
          </div>
        </div>
      </div>
    </div>
  );
}

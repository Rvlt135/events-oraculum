import { cn } from '../lib/utils';

interface EdgeBadgeProps {
  score: number;
  className?: string;
}

export function EdgeBadge({ score, className }: EdgeBadgeProps) {
  const getColor = (score: number) => {
    if (score >= 8) return 'bg-green-100 text-green-800 border-green-300';
    if (score >= 6.5) return 'bg-blue-100 text-blue-800 border-blue-300';
    return 'bg-amber-100 text-amber-800 border-amber-300';
  };

  const getLabel = (score: number) => {
    if (score >= 8) return 'High Edge';
    if (score >= 6.5) return 'Medium Edge';
    return 'Low Edge';
  };

  return (
    <div className={cn('inline-flex items-center gap-1 px-2 py-1 rounded-md border text-xs font-medium', getColor(score), className)}>
      <span>{getLabel(score)}</span>
      <span className="font-bold">{score.toFixed(1)}</span>
    </div>
  );
}

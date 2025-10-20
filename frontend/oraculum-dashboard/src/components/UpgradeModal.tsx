import { X, Crown, Check } from 'lucide-react';
import { usePlanStore } from '../store/planStore';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: string;
}

export function UpgradeModal({ isOpen, onClose, feature }: UpgradeModalProps) {
  const { setPlan } = usePlanStore();

  if (!isOpen) return null;

  const handleUpgrade = () => {
    setPlan('pro');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2 mb-4">
          <Crown className="h-6 w-6 text-amber-600" />
          <h2 className="text-2xl font-bold">Upgrade to Pro</h2>
        </div>

        <p className="text-muted-foreground mb-6">
          Unlock {feature} and get full access to all Oraculum AI features
        </p>

        <div className="space-y-3 mb-6">
          <div className="flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">Full reasoning and analysis for all predictions</span>
          </div>
          <div className="flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">AI model voting breakdown with confidence scores</span>
          </div>
          <div className="flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">Access to all sports: Basketball, Tennis, Hockey</span>
          </div>
          <div className="flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">Unlimited historical data and analytics</span>
          </div>
          <div className="flex items-start gap-2">
            <Check className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <span className="text-sm">100 events per day vs 20 on free plan</span>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border rounded-md hover:bg-secondary transition-colors"
          >
            Maybe Later
          </button>
          <button
            onClick={handleUpgrade}
            className="flex-1 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors font-medium"
          >
            Upgrade Now
          </button>
        </div>
      </div>
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { Check, Zap, Crown, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Pricing() {
  const navigate = useNavigate();
  const { isAuthenticated, setPlan } = usePlanStore();

  const handleSelectPlan = (plan: 'free' | 'pro') => {
    setPlan(plan);
    if (!isAuthenticated) {
      navigate('/auth');
    } else {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4">
      <div className="container mx-auto max-w-5xl">
        <div className="mb-8">
          <Link
            to={isAuthenticated ? '/' : '/auth'}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            {isAuthenticated ? 'Назад к Dashboard' : 'Назад к авторизации'}
          </Link>
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-3">Выберите план</h1>
            <p className="text-lg text-muted-foreground">
              Получите доступ к AI-анализу спортивных событий
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <div className="bg-white border rounded-lg p-8 shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="h-6 w-6 text-slate-600" />
              <h3 className="text-2xl font-bold">Free / Trial</h3>
            </div>

            <div className="mb-6">
              <div className="text-3xl font-bold mb-2">Бесплатно</div>
              <p className="text-sm text-muted-foreground">7 дней пробного периода</p>
            </div>

            <div className="mb-6">
              <p className="text-sm font-medium mb-4">
                Базовый доступ к odds и reasoning 1 агента, без истории
              </p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  <span>До 20 событий в день</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  <span>Только ⚽ Футбол</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  <span>Reasoning: краткая сводка</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  <span>История: последние 3 дня</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  <span>Trial — 7 дней, затем Free</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleSelectPlan('free')}
              className="w-full py-3 bg-slate-600 text-white rounded-md font-medium hover:bg-slate-700 transition-colors"
            >
              Начать бесплатно
            </button>
          </div>

          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-400 rounded-lg p-8 shadow-lg hover:shadow-xl transition-shadow relative">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-amber-500 text-white px-4 py-1 rounded-full text-sm font-medium">
              Рекомендуем
            </div>

            <div className="flex items-center gap-2 mb-4">
              <Crown className="h-6 w-6 text-amber-600" />
              <h3 className="text-2xl font-bold">Pro</h3>
            </div>

            <div className="mb-6">
              <div className="text-3xl font-bold mb-2">€15–25 <span className="text-lg font-normal text-muted-foreground">/ мес</span></div>
              <p className="text-sm text-muted-foreground">Полный доступ ко всем функциям</p>
            </div>

            <div className="mb-6">
              <p className="text-sm font-medium mb-4">
                Расширенные AI-агенты, исторический анализ, контекст
              </p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>До 100 событий в день</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>⚽ Футбол, 🏀 Баскетбол, 🎾 Теннис, 🏒 Хоккей</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>Reasoning: полный анализ</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>История: неограниченная</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>Контекст: составы, травмы, погода</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <span>AI Voting: детальный разбор моделей</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleSelectPlan('pro')}
              className="w-full py-3 bg-amber-600 text-white rounded-md font-medium hover:bg-amber-700 transition-colors"
            >
              Перейти на Pro
            </button>
          </div>
        </div>

        <div className="mt-12 bg-white border rounded-lg p-6 max-w-4xl mx-auto">
          <h3 className="font-semibold mb-2">Обратите внимание</h3>
          <p className="text-sm text-muted-foreground">
            Оплата и биллинг — это демонстрационный режим. Выбор плана меняет уровень доступа в интерфейсе.
            Для реальной интеграции платежей требуется подключение платёжных систем.
          </p>
        </div>
      </div>
    </div>
  );
}

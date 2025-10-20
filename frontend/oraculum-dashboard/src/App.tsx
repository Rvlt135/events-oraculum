import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { EventDetail } from './pages/EventDetail';
import { PredictedVsActual } from './pages/PredictedVsActual';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Header />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/event/:id" element={<EventDetail />} />
          <Route path="/history" element={<PredictedVsActual />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;

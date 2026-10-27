import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import AuthModal from './components/AuthModal';
import Landing from './pages/Landing';
import Tailor from './pages/Tailor';
import CareerBankPage from './pages/CareerBankPage';
import History from './pages/History';
import JobView from './pages/JobView';
import { isAuthenticated, logout } from './lib/api';

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [authOpen, setAuthOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const sync = () => setAuthed(isAuthenticated());
    window.addEventListener('auth-change', sync);
    return () => window.removeEventListener('auth-change', sync);
  }, []);

  // Logged out (or token expired) -> back to the landing page
  useEffect(() => {
    if (!authed) navigate('/', { replace: true });
  }, [authed, navigate]);

  const signIn = () => setAuthOpen(true);

  const guard = (page: JSX.Element) => (authed ? page : <Landing onGetStarted={signIn} />);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col text-slate-900">
      <Navbar authed={authed} onSignIn={signIn} onSignOut={logout} />
      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
        onSuccess={() => {
          setAuthOpen(false);
          navigate('/tailor');
        }}
      />
      <main className="max-w-6xl mx-auto px-5 sm:px-8 lg:px-12 flex-1 w-full py-10 sm:py-14">
        <Routes>
          <Route path="/" element={authed ? <Navigate to="/tailor" replace /> : <Landing onGetStarted={signIn} />} />
          <Route path="/tailor" element={guard(<Tailor />)} />
          <Route path="/career-bank" element={guard(<CareerBankPage />)} />
          <Route path="/jobs" element={guard(<History />)} />
          <Route path="/jobs/:id" element={guard(<JobView />)} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

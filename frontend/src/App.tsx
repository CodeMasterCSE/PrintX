import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { LandingPage } from './pages/LandingPage';
import { StudentPortal } from './pages/StudentPortal';
import { UserDashboard } from './pages/UserDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { KioskDisplay } from './pages/KioskDisplay';

const AppLayout: React.FC = () => {
  const location = useLocation();
  const isKioskMode = location.pathname.startsWith('/kiosk');

  if (isKioskMode) {
    return (
      <Routes>
        <Route path="/kiosk/:code" element={<KioskDisplay />} />
        <Route path="/kiosk" element={<KioskDisplay />} />
      </Routes>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 text-slate-900">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/print" element={<StudentPortal />} />
          <Route path="/dashboard" element={<UserDashboard />} />
          <Route path="/admin/*" element={<AdminDashboard />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
};

export default App;


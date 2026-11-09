import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Printer, Shield, User as UserIcon, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30000,
  });

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
            <Printer className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-slate-900">
              Print<span className="text-brand-600">X</span>
            </span>
            <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-brand-50 text-brand-700 rounded-full border border-brand-200">
              Self-Service
            </span>
          </div>
        </Link>

        {/* Live System Health Pill */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-600">
          <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
          <span>System {health?.status === 'healthy' ? 'Operational' : 'Connecting...'}</span>
          <span className="text-slate-400">|</span>
          <span className="font-mono text-slate-500">HP Smart Tank 585</span>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            to="/print"
            className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              location.pathname.startsWith('/print')
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            Print Portal
          </Link>
          <Link
            to="/dashboard"
            className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              location.pathname === '/dashboard'
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            My Jobs
          </Link>
          <Link
            to="/admin"
            className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              location.pathname.startsWith('/admin')
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
};


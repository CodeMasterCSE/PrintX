import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Printer,
  QrCode,
  Smartphone,
  CreditCard,
  FileCheck2,
  Maximize2,
  Minimize2,
  Clock,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Info,
  AlertCircle
} from 'lucide-react';
import { api } from '../api/client';
import { KioskConfig } from '../types';

export const KioskDisplay: React.FC = () => {
  const { code = 'KIOSK-01' } = useParams<{ code: string }>();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Track fullscreen changes
  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Fetch kiosk details with active polling
  const { data: kiosk, isLoading } = useQuery<KioskConfig>({
    queryKey: ['kiosk-display', code],
    queryFn: () => api.getKioskConfig(code),
    refetchInterval: 10000,
  });

  // Fetch printers status (with polling fallback)
  const { data: printers } = useQuery<any[]>({
    queryKey: ['printers-status'],
    queryFn: () => api.listPrinters(),
    refetchInterval: 5000,
  });

  const [livePrinters, setLivePrinters] = useState<any[]>([]);

  // Real-time SSE Telemetry Stream (Option B)
  useEffect(() => {
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource('/api/v1/printers/stream');

      eventSource.addEventListener('printer_snapshot', (e) => {
        try {
          const snapshot = JSON.parse(e.data);
          if (Array.isArray(snapshot)) setLivePrinters(snapshot);
        } catch (err) {
          console.error('SSE snapshot parse error:', err);
        }
      });

      eventSource.addEventListener('printer_update', (e) => {
        try {
          const updated = JSON.parse(e.data);
          setLivePrinters((prev) => {
            const index = prev.findIndex((p) => p.id === updated.id);
            if (index >= 0) {
              const copy = [...prev];
              copy[index] = updated;
              return copy;
            }
            return [...prev, updated];
          });
        } catch (err) {
          console.error('SSE printer_update parse error:', err);
        }
      });

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
      };
    } catch (err) {
      console.warn('SSE EventSource init failed:', err);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, []);

  const displayPrinters = livePrinters.length > 0 ? livePrinters : (printers || []);
  const activePrinter = displayPrinters?.find((p: any) => p.name?.includes('Smart Tank') || p.is_default) || displayPrinters?.[0];
  const isPaperOut = activePrinter?.status === 'out_of_paper' || activePrinter?.status === 'PAPER_OUT';
  const isOffline = activePrinter?.is_online === false || activePrinter?.status === 'offline';

  const qrUrl = `/api/v1/kiosks/${code}/qr.png?base_url=${encodeURIComponent(window.location.origin)}`;
  const mobilePortalUrl = `${window.location.origin}/print?device=${code}`;

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col justify-between selection:bg-indigo-500 selection:text-white font-sans">
      {/* Real-Time Paper-Out Hardware Interlock Banner (Option C) */}
      {isPaperOut && (
        <div className="bg-amber-600/95 text-white px-8 py-3.5 flex items-center justify-center gap-3 font-semibold text-sm shadow-lg border-b border-amber-500/50 animate-pulse">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>ATTENTION: Printer Paper Tray Empty — Please reload A4 paper tray to resume printing.</span>
        </div>
      )}
      {isOffline && !isPaperOut && (
        <div className="bg-rose-600/95 text-white px-8 py-3.5 flex items-center justify-center gap-3 font-semibold text-sm shadow-lg border-b border-rose-500/50">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>ATTENTION: Kiosk Printer Offline — Spooler subsystem disconnected. Attendant alerted.</span>
        </div>
      )}

      {/* Top Header Bar */}
      <header className="px-8 py-5 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Printer className="w-7 h-7 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-black tracking-tight text-white">PrintX</span>
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                Self-Service Kiosk
              </span>
            </div>
            <p className="text-sm text-slate-400 font-medium">
              Station: <strong className="text-slate-200">{kiosk?.name || code}</strong> ({kiosk?.location || 'Campus Terminal'})
            </p>
          </div>
        </div>

        {/* Live Hardware Telemetry & Clock */}
        <div className="flex items-center gap-5">
          {/* Printer Telemetry Badge */}
          <div className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700/60">
            <div className="relative">
              <div
                className={`w-3 h-3 rounded-full ${
                  isPaperOut ? 'bg-amber-400' : isOffline ? 'bg-rose-500' : 'bg-emerald-500'
                }`}
              />
              <div
                className={`absolute inset-0 rounded-full animate-ping opacity-75 ${
                  isPaperOut ? 'bg-amber-400' : isOffline ? 'bg-rose-500' : 'bg-emerald-500'
                }`}
              />
            </div>
            <div className="text-left">
              <div className="text-xs font-semibold text-slate-200">
                {activePrinter?.name || 'HP Smart Tank 585'}
              </div>
              <div className="text-[11px] text-slate-400">
                {isPaperOut ? (
                  <span className="text-amber-300 font-bold">Paper Tray Empty</span>
                ) : isOffline ? (
                  <span className="text-rose-400 font-bold">Offline</span>
                ) : (
                  'Ready to Print'
                )}
                {activePrinter?.queue_length ? ` • ${activePrinter.queue_length} in queue` : ' • Queue Empty'}
              </div>
            </div>
          </div>

          {/* Real-time Clock */}
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700/60 text-slate-200">
            <Clock className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-semibold tracking-wider font-mono">
              {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Kiosk Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Main Kiosk Hero Display */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-8 grid lg:grid-cols-12 gap-8 items-center">
        {/* Left Card: QR Scanner Target */}
        <div className="lg:col-span-5 flex flex-col items-center">
          <div className="w-full max-w-md bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-8 rounded-3xl border border-slate-800 shadow-2xl relative overflow-hidden text-center group">
            {/* Background Glow */}
            <div className="absolute -top-24 -left-24 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-300 text-xs font-semibold mb-4 border border-indigo-500/20">
              <Sparkles className="w-3.5 h-3.5" /> Scan to Start Printing
            </div>

            <h2 className="text-2xl font-bold text-white mb-2">
              Ready When You Are
            </h2>
            <p className="text-sm text-slate-400 mb-6">
              Point your smartphone camera at this code. No app or registration required.
            </p>

            {/* QR Code Container with Animated Scan Border */}
            <div className="relative mx-auto w-64 h-64 bg-white p-4 rounded-2xl shadow-xl flex items-center justify-center border-4 border-indigo-500/20 group-hover:border-indigo-500/40 transition-colors">
              <img
                src={qrUrl}
                alt={`Scan QR Code for Kiosk ${code}`}
                className="w-full h-full object-contain"
                onError={(e) => {
                  // Fallback to QR placeholder if server image loading
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
              <div className="absolute inset-x-4 top-4 h-0.5 bg-gradient-to-r from-transparent via-indigo-500 to-transparent animate-pulse" />
            </div>

            {/* Direct URL preview */}
            <div className="mt-6 pt-5 border-t border-slate-800/80">
              <p className="text-xs text-slate-400 mb-1">Direct Browser Link:</p>
              <code className="text-xs font-mono text-indigo-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 inline-block break-all">
                {mobilePortalUrl}
              </code>
            </div>

            {/* Live Pricing Badges */}
            <div className="grid grid-cols-2 gap-3 mt-6">
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/40 text-center">
                <span className="text-[11px] uppercase tracking-wider text-slate-400 block font-semibold">Grayscale</span>
                <span className="text-lg font-bold text-slate-100">₹{kiosk?.per_page_bw?.toFixed(2) || '2.00'}</span>
                <span className="text-[10px] text-slate-500 block">per page</span>
              </div>
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/40 text-center">
                <span className="text-[11px] uppercase tracking-wider text-slate-400 block font-semibold">Color</span>
                <span className="text-lg font-bold text-indigo-400">₹{kiosk?.per_page_color?.toFixed(2) || '10.00'}</span>
                <span className="text-[10px] text-slate-500 block">per page</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: 3-Step Guided Walkthrough */}
        <div className="lg:col-span-7 flex flex-col justify-center gap-6">
          <div>
            <div className="inline-flex items-center gap-2 text-indigo-400 font-semibold text-sm mb-2">
              <Zap className="w-4 h-4" /> Three Effortless Steps
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight leading-tight">
              Self-Service Printing Made Completely Touchless.
            </h1>
            <p className="text-slate-400 mt-2 text-base max-w-xl">
              From PDF on your phone to paper in the tray in under 60 seconds. Powered by the HP Smart Tank 585 series.
            </p>
          </div>

          {/* Step Cards */}
          <div className="space-y-4">
            {/* Step 1 */}
            <div className="flex items-start gap-5 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
                <Smartphone className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Step 1</span>
                  <h3 className="text-lg font-semibold text-white">Scan Kiosk QR Code</h3>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  Open your camera, Google Lens, or any QR scanner. Your phone immediately connects to this exact physical printer terminal.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex items-start gap-5 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400 flex items-center justify-center shrink-0">
                <FileCheck2 className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-violet-400">Step 2</span>
                  <h3 className="text-lg font-semibold text-white">Upload PDF & Configure Settings</h3>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  Select your document, choose pages (all or custom range), select Color or Grayscale, and review the transparent price.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex items-start gap-5 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <CreditCard className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Step 3</span>
                  <h3 className="text-lg font-semibold text-white">Instant UPI Pay & Collect Prints</h3>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  Pay with GPay, PhonePe, Paytm, or BHIM. Once verified, the printer starts automatically and paper exits into the tray.
                </p>
              </div>
            </div>
          </div>

          {/* Hardware & Safety Callout */}
          <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-900/40 flex items-center justify-between text-xs text-indigo-300">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
              <span>
                <strong>Hardware Protected:</strong> Single-sided simplex printing enforced for mechanical jam prevention on HP Smart Tank 585.
              </span>
            </div>
            <Link
              to={`/print?device=${code}`}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
            >
              Test Web Portal <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </main>

      {/* Kiosk Footer */}
      <footer className="px-8 py-4 border-t border-slate-800/80 bg-slate-950 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Windows Spooler Agent: Connected & Polling</span>
          <span>•</span>
          <span>Station ID: {code}</span>
        </div>
        <div>
          <span>PrintX Smart Printing Platform • Open Source SaaS Architecture</span>
        </div>
      </footer>
    </div>
  );
};

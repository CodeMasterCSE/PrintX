import React, { useState } from 'react';
import { 
  BarChart3, 
  Printer, 
  Layers, 
  DollarSign, 
  Activity, 
  HardDrive,
  Cpu, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Sliders, 
  Save, 
  Check,
  Settings,
  MapPin,
  Plus,
  Power,
  Star,
  RotateCcw,
  Search,
  Filter,
  Trash2,
  ShieldCheck,
  Wifi,
  Usb,
  X
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export const AdminDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'printers' | 'kiosks' | 'settings' | 'jobs'>('overview');

  // Queries
  const { data: analytics, refetch: refetchAnalytics } = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: api.getAdminAnalytics,
    refetchInterval: 5000,
  });

  const { data: printers, refetch: refetchPrinters } = useQuery({
    queryKey: ['admin-printers'],
    queryFn: api.listPrinters,
    refetchInterval: 5000,
  });

  const { data: adminJobs, refetch: refetchJobs } = useQuery({
    queryKey: ['admin-jobs'],
    queryFn: api.getAdminJobs,
    refetchInterval: 5000,
  });

  const { data: settingsData, refetch: refetchSettings } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: api.getAdminSettings,
  });

  const { data: kiosksData, refetch: refetchKiosks } = useQuery({
    queryKey: ['admin-kiosks'],
    queryFn: api.listAdminKiosks,
  });

  // State for pricing rule editor
  const [rateBw, setRateBw] = useState<number>(2.0);
  const [rateColor, setRateColor] = useState<number>(10.0);
  const [isSavedPricing, setIsSavedPricing] = useState<boolean>(false);

  // State for settings editor
  const [settingsForm, setSettingsForm] = useState<Record<string, string>>({});
  const [isSavedSettings, setIsSavedSettings] = useState<boolean>(false);

  // State for new kiosk modal / form
  const [newKioskCode, setNewKioskCode] = useState<string>('');
  const [newKioskName, setNewKioskName] = useState<string>('');
  const [newKioskLocation, setNewKioskLocation] = useState<string>('');
  const [showAddKiosk, setShowAddKiosk] = useState<boolean>(false);

  // State for printer discovery modal
  const [showDiscoverModal, setShowDiscoverModal] = useState<boolean>(false);
  const [isDiscovering, setIsDiscovering] = useState<boolean>(false);
  const [discoveredPrinters, setDiscoveredPrinters] = useState<any[]>([]);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [addingPrinterName, setAddingPrinterName] = useState<string | null>(null);
  const [newPrinterLocation, setNewPrinterLocation] = useState<string>('Campus Kiosk');

  // State for job filter
  const [jobSearch, setJobSearch] = useState<string>('');
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('ALL');

  // Pricing mutation
  const updatePricingMutation = useMutation({
    mutationFn: (newPricing: { per_page_bw: number; per_page_color: number }) =>
      api.updatePricingRule(newPricing),
    onSuccess: () => {
      setIsSavedPricing(true);
      setTimeout(() => setIsSavedPricing(false), 3000);
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    },
  });

  // Settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: Record<string, string>) =>
      api.updateAdminSettings(newSettings),
    onSuccess: () => {
      setIsSavedSettings(true);
      setTimeout(() => setIsSavedSettings(false), 3000);
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
    },
  });

  // Add Kiosk mutation
  const addKioskMutation = useMutation({
    mutationFn: (kiosk: { code: string; name: string; location: string }) =>
      api.createAdminKiosk(kiosk),
    onSuccess: () => {
      setShowAddKiosk(false);
      setNewKioskCode('');
      setNewKioskName('');
      setNewKioskLocation('');
      queryClient.invalidateQueries({ queryKey: ['admin-kiosks'] });
    },
  });

  const handleTogglePrinter = async (printerId: string, currentStatus: boolean) => {
    try {
      await api.togglePrinterStatus(printerId, !currentStatus);
      queryClient.invalidateQueries({ queryKey: ['admin-printers'] });
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  const handleSetDefaultPrinter = async (printerId: string) => {
    try {
      await api.setDefaultPrinter(printerId);
      queryClient.invalidateQueries({ queryKey: ['admin-printers'] });
    } catch (err: any) {
      alert(`Error setting default: ${err.message}`);
    }
  };

  const [purgeResult, setPurgeResult] = useState<string | null>(null);
  const [isPurging, setIsPurging] = useState<boolean>(false);

  const handlePurgeDocuments = async () => {
    setIsPurging(true);
    setPurgeResult(null);
    try {
      const res = await api.purgeDocuments({ retention_minutes: 15 });
      setPurgeResult(`Shredded ${res.purged_count} document(s), recovering ${res.freed_mb} MB disk space.`);
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    } catch (err: any) {
      alert(`Purge failed: ${err.message}`);
    } finally {
      setIsPurging(false);
    }
  };

  const handleUpdatePrinterStatus = async (printerId: string, statusText: string, isOnline: boolean = true) => {
    try {
      await api.updatePrinterStatus(printerId, statusText, isOnline);
      queryClient.invalidateQueries({ queryKey: ['admin-printers'] });
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleDiscoverPrinters = async () => {
    setShowDiscoverModal(true);
    setIsDiscovering(true);
    setDiscoveryError(null);
    try {
      const res = await api.discoverPrinters();
      setDiscoveredPrinters(res);
    } catch (err: any) {
      setDiscoveryError(err.message || 'Failed to scan for local or network printers');
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAddPrinter = async (item: any) => {
    setAddingPrinterName(item.name);
    try {
      await api.addPrinter({
        name: item.name,
        driver_name: item.driver_name,
        port_name: item.port_name,
        location: newPrinterLocation || 'Campus Kiosk',
        supports_color: item.supports_color ?? true,
        supports_duplex: item.supports_duplex ?? false,
        is_default: printerList.length === 0,
      });
      queryClient.invalidateQueries({ queryKey: ['admin-printers'] });
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
      setDiscoveredPrinters((prev) =>
        prev.map((p) => (p.name === item.name ? { ...p, is_already_added: true } : p))
      );
    } catch (err: any) {
      alert(`Failed to add printer: ${err.message}`);
    } finally {
      setAddingPrinterName(null);
    }
  };

  const handleDeletePrinter = async (printer: any) => {
    if (!window.confirm(`Are you sure you want to remove '${printer.name}' from PrintX?`)) {
      return;
    }
    try {
      await api.deletePrinter(printer.id);
      queryClient.invalidateQueries({ queryKey: ['admin-printers'] });
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    } catch (err: any) {
      alert(`Failed to remove printer: ${err.message}`);
    }
  };

  const printerList = printers || [];
  const rawJobList = adminJobs?.jobs || [];
  const kioskList = kiosksData || [];

  const filteredJobs = rawJobList.filter((j: any) => {
    const matchesSearch = 
      !jobSearch || 
      j.job_number.toLowerCase().includes(jobSearch.toLowerCase()) ||
      (j.document?.original_filename || '').toLowerCase().includes(jobSearch.toLowerCase());
    const matchesStatus = jobStatusFilter === 'ALL' || j.status === jobStatusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900 text-white text-[11px] font-semibold uppercase tracking-wider mb-2">
            Operations & Telemetry
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Kiosk System Administration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time Windows Spooler telemetry, hardware printer queues, and platform settings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchAnalytics();
              refetchPrinters();
              refetchJobs();
            }}
            className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-brand-600" />
            Refresh
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 mb-8 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Overview & Telemetry
        </button>
        <button
          onClick={() => setActiveTab('printers')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'printers'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Hardware & Printers ({printerList.length})
        </button>
        <button
          onClick={() => setActiveTab('kiosks')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'kiosks'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Kiosks ({kioskList.length})
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'jobs'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Job Audits ({rawJobList.length})
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'settings'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Platform Settings
        </button>
      </div>

      {/* ================= TAB 1: OVERVIEW & TELEMETRY ================= */}
      {activeTab === 'overview' && (
        <div>
          {/* KPI Cards Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase">Gross Revenue</span>
              <div className="text-2xl font-bold text-slate-900 mt-2">
                ₹{(analytics?.total_revenue || 0).toFixed(2)}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 font-mono">
                Today: ₹{(analytics?.daily_revenue || 0).toFixed(2)} | Week: ₹{(analytics?.weekly_revenue || 0).toFixed(2)}
              </div>
            </div>
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase">Completed Jobs</span>
              <div className="text-2xl font-bold text-emerald-600 mt-2">
                {analytics?.completed_jobs || 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 font-mono">
                Total Pages: {analytics?.total_pages_printed || 0}
              </div>
            </div>
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase">Spooler Queue Depth</span>
              <div className="text-2xl font-bold text-amber-600 mt-2">
                {analytics?.pending_jobs || 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 font-mono">
                Hardware Queues: {analytics?.total_spooler_queue_depth || 0}
              </div>
            </div>
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase">System Status</span>
              <div className="text-2xl font-bold text-slate-900 mt-2 flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${
                  analytics?.system_health?.toLowerCase().includes('offline')
                    ? 'bg-red-500 animate-ping'
                    : analytics?.system_health?.toLowerCase().includes('degraded')
                    ? 'bg-amber-500'
                    : 'bg-emerald-500 animate-pulse'
                }`} />
                <span className={`text-xl ${
                  analytics?.system_health?.toLowerCase().includes('offline')
                    ? 'text-red-600 font-bold'
                    : analytics?.system_health?.toLowerCase().includes('degraded')
                    ? 'text-amber-600 font-bold'
                    : 'text-slate-900'
                }`}>
                  {analytics?.system_health || 'Operational'}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1 font-mono">
                Active Agents: {analytics?.active_agents_count || 1} | Printers: {analytics?.active_printers_count || 0} Online
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Connected Queues Preview */}
            <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-bold text-slate-900">Connected Hardware Queues</h2>
                <span className="text-xs font-mono text-slate-400">pywin32 Spooler Integration</span>
              </div>
              <div className="space-y-3">
                {printerList.length === 0 ? (
                  <div className="py-8 px-4 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                    <Printer className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-700">No hardware printers connected</p>
                    <p className="text-xs text-slate-400 mt-1 mb-4">
                      Connect and discover any physical Wi-Fi or USB printer.
                    </p>
                    <button
                      onClick={handleDiscoverPrinters}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs shadow-xs transition-colors"
                    >
                      <Search className="w-3.5 h-3.5" />
                      Discover Printers
                    </button>
                  </div>
                ) : (
                  printerList.map((p: any) => (
                    <div key={p.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                          <Printer className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-bold text-sm text-slate-900">{p.name}</h4>
                            {p.is_default && (
                              <span className="px-1.5 py-0.5 rounded bg-brand-100 text-brand-700 text-[10px] font-bold">DEFAULT</span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 font-mono mt-0.5">
                            Driver: {p.driver_name || 'Generic'} | Port: {p.port_name || 'USB'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex flex-col items-end">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase inline-flex items-center gap-1.5 ${
                          p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : p.is_online
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-red-50 text-red-700 border border-red-200 shadow-xs'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                              ? 'bg-amber-500'
                              : p.is_online
                              ? 'bg-emerald-500 animate-pulse'
                              : 'bg-red-500'
                          }`} />
                          {p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                            ? 'Out of Paper'
                            : !p.is_online || p.status?.toLowerCase() === 'offline'
                            ? 'OFFLINE'
                            : p.status}
                        </span>
                        <p className={`text-[11px] font-mono mt-1 ${!p.is_online ? 'text-red-500 font-semibold' : 'text-slate-400'}`}>
                          {!p.is_online ? 'Hardware Disconnected' : `Queue Depth: ${p.queue_length} job(s)`}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Live Pricing Rules Editor */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sliders className="w-5 h-5 text-brand-600" />
                <h2 className="text-base font-bold text-slate-900">Configure Rates</h2>
              </div>
              <p className="text-xs text-slate-500 mb-6 leading-relaxed">
                Update real-time per-page prices enforced across the platform and kiosk displays.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                    Grayscale Rate (₹ / A4 page)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    value={rateBw}
                    onChange={(e) => setRateBw(parseFloat(e.target.value) || 2.0)}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                    Full Color Rate (₹ / A4 page)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1.0"
                    value={rateColor}
                    onChange={(e) => setRateColor(parseFloat(e.target.value) || 10.0)}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <button
                  onClick={() => updatePricingMutation.mutate({ per_page_bw: rateBw, per_page_color: rateColor })}
                  disabled={updatePricingMutation.isPending}
                  className="mt-2 w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2"
                >
                  {isSavedPricing ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-400" />
                      Rates Saved Successfully!
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Update Global Pricing Rules
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 2: PRINTER MANAGEMENT ================= */}
      {activeTab === 'printers' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">Windows 11 Hardware & Network Printers</h2>
              <p className="text-xs text-slate-500 mt-1">Discovered through win32print on host agent machine (USB & Wi-Fi).</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDiscoverPrinters}
                className="px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs flex items-center gap-2 shadow-sm transition-colors"
              >
                <Search className="w-4 h-4" />
                Discover Printers (Wi-Fi & USB)
              </button>
            </div>
          </div>

          {printerList.some((p: any) => !p.is_online || p.status?.toLowerCase() === 'offline') && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
                <div>
                  <span className="font-bold text-red-900">Hardware OFFLINE Alert: </span>
                  One or more configured printers are currently OFFLINE or disconnected. Print jobs will be held or routed to an online failover queue.
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-red-100 text-red-700 font-bold uppercase tracking-wider text-[10px] border border-red-200 shrink-0">
                OFFLINE DETECTED
              </span>
            </div>
          )}

          {printerList.length === 0 ? (
            <div className="py-16 px-6 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
              <div className="w-14 h-14 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto mb-4">
                <Printer className="w-7 h-7" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-1">No Printers Connected</h3>
              <p className="text-sm text-slate-500 max-w-md mx-auto mb-6 leading-relaxed">
                PrintX starts with zero pre-seeded demo devices. Any printer installed on this Windows 11 machine can be discovered and connected dynamically via Wi-Fi or USB.
              </p>
              <button
                onClick={handleDiscoverPrinters}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-sm transition-colors"
              >
                <Search className="w-4 h-4" />
                Discover Printers (Wi-Fi & USB)
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Printer Name</th>
                    <th className="px-6 py-3">Driver</th>
                    <th className="px-6 py-3">Port</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Queue Length</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {printerList.map((p: any) => (
                    <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900">{p.name}</span>
                          {p.is_default && (
                            <span className="px-1.5 py-0.5 rounded bg-brand-100 text-brand-700 text-[10px] font-bold">DEFAULT</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">{p.driver_name}</td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">{p.port_name}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase ${
                          p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : p.is_online
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-red-50 text-red-700 border border-red-200'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                              ? 'bg-amber-500'
                              : p.is_online
                              ? 'bg-emerald-500'
                              : 'bg-red-500'
                          }`} />
                          {p.status === 'out_of_paper' || p.status === 'PAPER_OUT'
                            ? 'Out of Paper'
                            : !p.is_online || p.status?.toLowerCase() === 'offline'
                            ? 'OFFLINE'
                            : p.status}
                        </span>
                        {!p.is_online && (
                          <div className="text-[10px] text-red-600 font-medium mt-1">
                            Printer offline or disconnected
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-900">{p.queue_length} job(s)</td>
                      <td className="px-6 py-4 text-right space-x-2">
                        {p.status === 'out_of_paper' ? (
                          <button
                            onClick={() => handleUpdatePrinterStatus(p.id, 'online', true)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-100 hover:bg-emerald-200 text-emerald-800 transition-colors"
                            title="Simulate paper refill"
                          >
                            Clear Paper Out
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpdatePrinterStatus(p.id, 'out_of_paper', true)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-800 transition-colors"
                            title="Simulate paper empty to test interlock"
                          >
                            Simulate Paper Out
                          </button>
                        )}
                        <button
                          onClick={() => handleTogglePrinter(p.id, p.is_online)}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold transition-colors ${
                            p.is_online ? 'bg-slate-100 hover:bg-slate-200 text-slate-700' : 'bg-emerald-100 hover:bg-emerald-200 text-emerald-800'
                          }`}
                        >
                          <Power className="w-3.5 h-3.5" />
                          {p.is_online ? 'Set Maintenance' : 'Set Ready'}
                        </button>
                        {!p.is_default && (
                          <button
                            onClick={() => handleSetDefaultPrinter(p.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
                          >
                            <Star className="w-3.5 h-3.5 text-amber-500" />
                            Set Default
                          </button>
                        )}
                        <button
                          onClick={() => handleDeletePrinter(p)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold transition-colors"
                          title="Remove device from PrintX"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 3: KIOSK MANAGEMENT ================= */}
      {activeTab === 'kiosks' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">Physical Kiosks</h2>
              <p className="text-xs text-slate-500 mt-1">Configure campus locations and bind kiosks to printers.</p>
            </div>
            <button
              onClick={() => setShowAddKiosk(!showAddKiosk)}
              className="px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Kiosk
            </button>
          </div>

          {/* Add Kiosk Form */}
          {showAddKiosk && (
            <div className="mb-6 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-3">Register New Kiosk</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Code (e.g. KIOSK-02)"
                  value={newKioskCode}
                  onChange={(e) => setNewKioskCode(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-slate-300 text-xs"
                />
                <input
                  type="text"
                  placeholder="Name (e.g. Science Library)"
                  value={newKioskName}
                  onChange={(e) => setNewKioskName(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-slate-300 text-xs"
                />
                <input
                  type="text"
                  placeholder="Location (e.g. Block C, Floor 1)"
                  value={newKioskLocation}
                  onChange={(e) => setNewKioskLocation(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-slate-300 text-xs"
                />
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => addKioskMutation.mutate({ code: newKioskCode, name: newKioskName, location: newKioskLocation })}
                  disabled={!newKioskCode || !newKioskName || addKioskMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-slate-900 text-white font-semibold text-xs disabled:opacity-50"
                >
                  Save Kiosk
                </button>
                <button
                  onClick={() => setShowAddKiosk(false)}
                  className="px-4 py-2 rounded-lg bg-white border border-slate-300 text-slate-700 font-semibold text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {kioskList.map((k: any) => (
              <div key={k.id} className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-bold text-brand-600 text-xs">{k.code}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    k.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                  }`}>
                    {k.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
                <h4 className="font-bold text-sm text-slate-900">{k.name}</h4>
                <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  {k.location}
                </p>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                  <div>
                    QR: <span className="font-mono text-slate-600">/print?device={k.code}</span>
                  </div>
                  <a
                    href={`/kiosk/${k.code}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-2 py-1 rounded transition-colors"
                  >
                    Launch Display &rarr;
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================= TAB 4: JOB AUDITS & MANAGEMENT ================= */}
      {activeTab === 'jobs' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Job Management & Audit Trail</h2>
              <p className="text-xs text-slate-500 mt-1">Review, search, and manage print job lifecycles.</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search by Job ID or file..."
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                  className="pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs w-56 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <select
                value={jobStatusFilter}
                onChange={(e) => setJobStatusFilter(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="COMPLETED">Completed</option>
                <option value="QUEUED">Queued</option>
                <option value="PRINTING">Printing</option>
                <option value="FAILED">Failed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Document</th>
                  <th className="px-6 py-3">Mode</th>
                  <th className="px-6 py-3">Price</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Spooler ID</th>
                  <th className="px-6 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredJobs.map((j: any) => (
                  <tr key={j.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{j.job_number}</td>
                    <td className="px-6 py-4 font-medium text-slate-800">{j.document?.original_filename || 'PDF Document'}</td>
                    <td className="px-6 py-4 capitalize text-slate-600">{j.configuration?.color_mode || 'Grayscale'}</td>
                    <td className="px-6 py-4 font-semibold text-slate-900">₹{j.price.toFixed(2)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                        j.status === 'COMPLETED'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : j.status === 'FAILED'
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">{j.spooler_job_id || 'N/A'}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(j.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= TAB 5: SYSTEM SETTINGS ================= */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-brand-600" />
              <h2 className="text-base font-bold text-slate-900">Platform Configuration Parameters</h2>
            </div>
            <p className="text-xs text-slate-500 mb-6 leading-relaxed">
              Configure global upload constraints, document retention policies, and hardware queue defaults.
            </p>

            <div className="space-y-4 max-w-xl">
              {(settingsData?.settings || []).map((s: any) => (
                <div key={s.key} className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                  <label className="block text-xs font-bold text-slate-800 font-mono mb-1">
                    {s.key}
                  </label>
                  <p className="text-xs text-slate-500 mb-2">{s.description}</p>
                  <input
                    type="text"
                    defaultValue={s.value}
                    onChange={(e) => setSettingsForm((prev) => ({ ...prev, [s.key]: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              ))}

              <button
                onClick={() => updateSettingsMutation.mutate(settingsForm)}
                disabled={Object.keys(settingsForm).length === 0 || updateSettingsMutation.isPending}
                className="mt-4 py-2.5 px-6 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSavedSettings ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    Settings Saved Successfully!
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Platform Settings
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Privacy Retention & Document Shredding Card (Option C) */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">FERPA & GDPR Privacy Shredder</h2>
            </div>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              PrintX enforces strict document privacy: student upload binaries are wiped from disk 15 minutes after completion.
              Financial transaction proofs, job numbers, and immutable audit events are preserved for reconciliation.
            </p>

            {purgeResult && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                {purgeResult}
              </div>
            )}

            <div className="flex items-center gap-4">
              <button
                onClick={handlePurgeDocuments}
                disabled={isPurging}
                className="py-2.5 px-5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                {isPurging ? 'Shredding Expired Documents...' : 'Run Privacy Shredder Now'}
              </button>
              <span className="text-[11px] text-slate-400">
                Retention threshold: 15 minutes post-print
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ================= PRINTER DISCOVERY MODAL ================= */}
      {showDiscoverModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center font-bold">
                  <Printer className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Hardware & Network Printer Discovery</h3>
                  <p className="text-xs text-slate-500 font-medium">
                    Scans Windows Spooler for USB cables & Wi-Fi / LAN network endpoints
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowDiscoverModal(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Location for new printers:
                  </span>
                  <input
                    type="text"
                    value={newPrinterLocation}
                    onChange={(e) => setNewPrinterLocation(e.target.value)}
                    placeholder="e.g. Campus Library Ground Floor"
                    className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <button
                  onClick={handleDiscoverPrinters}
                  disabled={isDiscovering}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isDiscovering ? 'animate-spin text-brand-600' : ''}`} />
                  Scan Again
                </button>
              </div>

              {isDiscovering ? (
                <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
                  <RefreshCw className="w-8 h-8 text-brand-600 animate-spin" />
                  <p className="text-sm font-semibold text-slate-700">Scanning local and network ports...</p>
                  <p className="text-xs text-slate-400">Querying win32print EnumPrinters for USB, WSD, and IP queues</p>
                </div>
              ) : discoveryError ? (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                  <div className="flex items-center gap-2 font-bold mb-1">
                    <AlertCircle className="w-4 h-4" />
                    Discovery Failed
                  </div>
                  <p>{discoveryError}</p>
                </div>
              ) : discoveredPrinters.length === 0 ? (
                <div className="py-10 text-center text-slate-500 text-xs">
                  No printers detected. Ensure your printer is powered on and connected via USB or Wi-Fi.
                </div>
              ) : (
                <div className="space-y-3">
                  {discoveredPrinters.map((p) => {
                    const isUsb = p.connection_type === 'USB';
                    const isWifi = p.connection_type === 'Wi-Fi / Network';
                    const isVirtual = p.is_virtual || p.connection_type === 'Virtual / Software';

                    return (
                      <div
                        key={p.name}
                        className={`p-4 rounded-xl border transition-all ${
                          p.is_already_added
                            ? 'bg-slate-50/60 border-slate-200 opacity-80'
                            : isVirtual
                            ? 'bg-slate-50 border-dashed border-slate-200'
                            : 'bg-white border-slate-200 shadow-sm hover:border-brand-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-3">
                            <div
                              className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
                                isWifi
                                  ? 'bg-emerald-50 text-emerald-600'
                                  : isUsb
                                  ? 'bg-blue-50 text-blue-600'
                                  : 'bg-slate-100 text-slate-500'
                              }`}
                            >
                              {isWifi ? (
                                <Wifi className="w-5 h-5" />
                              ) : isUsb ? (
                                <Usb className="w-5 h-5" />
                              ) : (
                                <Printer className="w-5 h-5" />
                              )}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-bold text-sm text-slate-900">{p.name}</h4>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border ${
                                    isWifi
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : isUsb
                                      ? 'bg-blue-50 text-blue-700 border-blue-200'
                                      : 'bg-slate-100 text-slate-600 border-slate-200'
                                  }`}
                                >
                                  {p.connection_type}
                                </span>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border inline-flex items-center gap-1 ${
                                    p.status === 'online'
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : 'bg-red-50 text-red-700 border-red-200'
                                  }`}
                                >
                                  <span className={`w-1.5 h-1.5 rounded-full ${p.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                  {p.status === 'online' ? 'Online' : 'OFFLINE'}
                                </span>
                              </div>
                              <p className="text-xs text-slate-500 font-mono mt-1">
                                Driver: {p.driver_name} | Port: {p.port_name}
                              </p>
                              {p.status_details && p.status === 'offline' && (
                                <p className="text-[11px] text-red-600 font-medium mt-1 flex items-center gap-1">
                                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                                  {p.status_details}
                                </p>
                              )}
                              <div className="flex items-center gap-2 mt-1.5">
                                <span className="text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                  {p.supports_color ? 'Color & B&W' : 'B&W Only'}
                                </span>
                                <span className="text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                  {p.supports_duplex ? 'Auto Duplex' : 'Single-Sided'}
                                </span>
                              </div>
                              {isVirtual && (
                                <p className="text-[11px] text-amber-600 mt-1 font-medium">
                                  Virtual/Software device (Not recommended for physical kiosk kiosks)
                                </p>
                              )}
                            </div>
                          </div>

                          <div className="flex-shrink-0">
                            {p.is_already_added ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200">
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                                Added
                              </span>
                            ) : (
                              <button
                                onClick={() => handleAddPrinter(p)}
                                disabled={addingPrinterName === p.name}
                                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold shadow-sm transition-all ${
                                  isVirtual
                                    ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                                    : 'bg-brand-600 hover:bg-brand-700 text-white'
                                } disabled:opacity-50`}
                              >
                                {addingPrinterName === p.name ? (
                                  <>
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                    Adding...
                                  </>
                                ) : (
                                  <>
                                    <Plus className="w-3.5 h-3.5" />
                                    Add to PrintX
                                  </>
                                )}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>
                Wi-Fi printers must be powered on and connected to the same LAN or configured via WSD / TCP-IP.
              </span>
              <button
                onClick={() => setShowDiscoverModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold text-xs transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

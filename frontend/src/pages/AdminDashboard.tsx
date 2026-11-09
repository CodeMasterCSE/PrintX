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
  Check
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export const AdminDashboard: React.FC = () => {
  const queryClient = useQueryClient();

  // Queries
  const { data: analytics, refetch: refetchAnalytics } = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: api.getAdminAnalytics,
    refetchInterval: 5000,
  });

  const { data: printers } = useQuery({
    queryKey: ['admin-printers'],
    queryFn: api.listPrinters,
    refetchInterval: 5000,
  });

  const { data: adminJobs } = useQuery({
    queryKey: ['admin-jobs'],
    queryFn: api.getAdminJobs,
    refetchInterval: 5000,
  });

  // State for pricing rule editor
  const [rateBw, setRateBw] = useState<number>(2.0);
  const [rateColor, setRateColor] = useState<number>(10.0);
  const [isSaved, setIsSaved] = useState<boolean>(false);

  const updatePricingMutation = useMutation({
    mutationFn: (newPricing: { per_page_bw: number; per_page_color: number }) =>
      api.updatePricingRule(newPricing),
    onSuccess: () => {
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
      queryClient.invalidateQueries({ queryKey: ['admin-analytics'] });
    },
  });

  const handleSavePricing = () => {
    updatePricingMutation.mutate({
      per_page_bw: rateBw,
      per_page_color: rateColor,
    });
  };

  const printerList = printers || [];
  const jobList = adminJobs?.jobs || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900 text-white text-[11px] font-semibold uppercase tracking-wider mb-2">
            Operations & Telemetry
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Kiosk System Administration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time Windows Spooler telemetry, HP Smart Tank queues, and pricing controls.
          </p>
        </div>
        <button
          onClick={() => refetchAnalytics()}
          className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="w-4 h-4 text-brand-600" />
          Refresh Metrics
        </button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Gross Revenue</span>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            ₹{(analytics?.total_revenue || 0).toFixed(2)}
          </div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Completed</span>
          <div className="text-2xl font-bold text-emerald-600 mt-2">
            {analytics?.completed_jobs || 0}
          </div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Active / In Queue</span>
          <div className="text-2xl font-bold text-amber-600 mt-2">
            {analytics?.pending_jobs || 0}
          </div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">System Status</span>
          <div className="text-2xl font-bold text-slate-900 mt-2 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            {analytics?.system_health || 'Operational'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Left: Registered Windows Printers */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900">
              Connected Hardware Queues
            </h2>
            <span className="text-xs font-mono text-slate-400">
              pywin32 Spooler Integration
            </span>
          </div>

          <div className="space-y-3">
            {printerList.map((p: any) => (
              <div 
                key={p.id} 
                className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Printer className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-slate-900">{p.name}</h4>
                    <p className="text-xs text-slate-500 font-mono">
                      Driver: {p.driver_name || 'Generic'} | Port: {p.port_name || 'USB'}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ${
                    p.is_online 
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}>
                    {p.status}
                  </span>
                  <p className="text-[11px] text-slate-400 font-mono mt-1">
                    Queue Depth: {p.queue_length} job(s)
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Dynamic Pricing Rules Editor */}
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
              onClick={handleSavePricing}
              disabled={updatePricingMutation.isPending}
              className="mt-2 w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2"
            >
              {isSaved ? (
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

      {/* Recent Print Jobs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Platform Jobs Audit Log</h2>
          <span className="text-xs text-slate-400 font-mono">{jobList.length} recent submissions</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Job Number</th>
                <th className="px-6 py-3">Document</th>
                <th className="px-6 py-3">Mode</th>
                <th className="px-6 py-3">Amount</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Idempotency Key</th>
                <th className="px-6 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobList.map((j: any) => (
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
                  <td className="px-6 py-4 font-mono text-xs text-slate-400 truncate max-w-xs">{j.idempotency_key}</td>
                  <td className="px-6 py-4 text-xs text-slate-400">{new Date(j.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

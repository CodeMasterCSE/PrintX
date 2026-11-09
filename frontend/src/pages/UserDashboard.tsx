import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Clock, CheckCircle, AlertTriangle, ArrowUpRight, RotateCcw, Printer } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { PrintJob } from '../types';

export const UserDashboard: React.FC = () => {
  const { data: jobs, isLoading } = useQuery({
    queryKey: ['user-jobs'],
    queryFn: api.listJobs,
    refetchInterval: 5000,
  });

  const jobList: PrintJob[] = jobs || [];
  const completedJobs = jobList.filter((j) => j.status === 'COMPLETED');
  const pendingJobs = jobList.filter((j) => ['PAYMENT_PENDING', 'PAYMENT_VERIFIED', 'QUEUED', 'DISPATCHED', 'SUBMITTED_TO_SPOOLER', 'PRINTING'].includes(j.status));
  const failedJobs = jobList.filter((j) => j.status === 'FAILED');
  const totalSpent = completedJobs.reduce((acc, j) => acc + j.price, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Student Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Track your recent print jobs, download receipts, and view payment histories.
          </p>
        </div>
        <Link
          to="/print?device=KIOSK-01"
          className="px-5 py-2.5 rounded-xl bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 transition-colors shadow-sm self-start sm:self-auto flex items-center gap-2"
        >
          <Printer className="w-4 h-4" />
          New Print Job
        </Link>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Jobs</span>
          <div className="text-2xl font-bold text-slate-900 mt-2">{jobList.length}</div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Completed</span>
          <div className="text-2xl font-bold text-emerald-600 mt-2">{completedJobs.length}</div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">In Progress</span>
          <div className="text-2xl font-bold text-amber-600 mt-2">{pendingJobs.length}</div>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Spent</span>
          <div className="text-2xl font-bold text-slate-900 mt-2">₹{totalSpent.toFixed(2)}</div>
        </div>
      </div>

      {/* Recent Jobs Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Print Job History</h2>
          <span className="text-xs text-slate-400 font-mono">{jobList.length} total records</span>
        </div>

        {jobList.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <FileText className="w-10 h-10 mx-auto text-slate-300 mb-3" />
            <p className="text-sm font-medium text-slate-600">No print jobs yet</p>
            <p className="text-xs text-slate-400 mt-1">Upload and configure your first document to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Document</th>
                  <th className="px-6 py-3">Mode</th>
                  <th className="px-6 py-3">Pages</th>
                  <th className="px-6 py-3">Amount</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobList.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-900">{j.job_number}</td>
                    <td className="px-6 py-4 font-medium text-slate-800">{j.document?.original_filename || 'PDF Document'}</td>
                    <td className="px-6 py-4 capitalize text-slate-600">{j.configuration?.color_mode || 'Grayscale'}</td>
                    <td className="px-6 py-4 text-slate-600">{j.total_pages} pg (x{j.configuration?.copies || 1})</td>
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
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(j.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

import React from 'react';
import { Printer, Shield, CheckCircle2, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white">
                <Printer className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold tracking-tight text-slate-900">
                Print<span className="text-brand-600">X</span>
              </span>
            </div>
            <p className="text-sm text-slate-500 max-w-sm mb-4 leading-relaxed">
              Open-source autonomous smart printing platform for campus libraries, coworking spaces, and retail centers.
            </p>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-brand-500" /> Server-side verified
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Windows 11 Native
              </span>
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              Supported Hardware
            </h4>
            <ul className="space-y-2 text-sm text-slate-600">
              <li>HP Smart Tank 585</li>
              <li>HP Smart Tank 580-590 Series</li>
              <li>A4 Single-Sided Documents</li>
              <li>Grayscale & Full Color Output</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              System Telemetry
            </h4>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600 space-y-1 font-mono">
              <div>Spooler: Windows 11 Native</div>
              <div>CLI: SumatraPDF Headless</div>
              <div>Rate: ₹2.00 B&W / ₹10.00 Color</div>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 mt-8 pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400">
          <p>© 2026 PrintX Platform. MIT Open Source License.</p>
          <p className="mt-2 sm:mt-0 flex items-center gap-1">
            Engineered with <Heart className="w-3 h-3 text-red-500 fill-red-500" /> for friction-free printing.
          </p>
        </div>
      </div>
    </footer>
  );
};


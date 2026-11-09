import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Printer, 
  Upload, 
  Sliders, 
  CreditCard, 
  FileCheck, 
  ShieldCheck, 
  Zap, 
  HelpCircle,
  ArrowRight,
  Sparkles
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-28 bg-gradient-to-b from-brand-50/60 via-white to-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-100/70 border border-brand-200 text-brand-800 text-xs font-semibold uppercase tracking-wider mb-8 animate-fade-in">
            <Sparkles className="w-3.5 h-3.5 text-brand-600" />
            Next-Gen Autonomous Kiosk Printing
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 max-w-4xl mx-auto leading-tight sm:leading-none">
            Your Documents. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-blue-600">
              Your Settings.
            </span>{' '}
            Your Prints.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Eliminate print shop lines and manual file handoffs. Scan the QR code at your nearest PrintX station, upload your PDF, customize your copies, pay via UPI, and collect your paper.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/print?device=KIOSK-01"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-base shadow-lg shadow-brand-500/25 hover:shadow-brand-500/35 transition-all flex items-center justify-center gap-2 group"
            >
              Start Printing Now
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-medium text-base border border-slate-200 shadow-sm transition-all text-center"
            >
              How It Works
            </a>
          </div>

          {/* Quick Hardware Capability Pill */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 font-medium">
            <div className="flex items-center gap-1.5">
              <Printer className="w-4 h-4 text-brand-600" />
              <span>Target: HP Smart Tank 585</span>
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Server-Validated Pricing</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-amber-500" />
              <span>Zero-Duplicate Spooler Guard</span>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2">
              Autonomous Workflow
            </h2>
            <h3 className="text-3xl font-bold text-slate-900 tracking-tight">
              From phone screen to printed paper in 60 seconds
            </h3>
            <p className="mt-3 text-slate-600">
              No software installation, no USB drives, and no operator assistance needed.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-brand-200 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center font-bold text-lg mb-4">
                1
              </div>
              <h4 className="text-lg font-semibold text-slate-900 mb-2">Scan & Upload</h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Scan the kiosk QR code and drag-and-drop your PDF. Our engine validates pages and dimensions automatically.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-brand-200 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg mb-4">
                2
              </div>
              <h4 className="text-lg font-semibold text-slate-900 mb-2">Set Preferences</h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Choose Grayscale (₹2/page) or Full Color (₹10/page), set copy counts (1–10), and select custom page ranges.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-brand-200 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-lg mb-4">
                3
              </div>
              <h4 className="text-lg font-semibold text-slate-900 mb-2">Instant UPI Payment</h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Pay via any UPI app (GPay, PhonePe, Paytm). The server cryptographically verifies payment before releasing paper.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-brand-200 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-lg mb-4">
                4
              </div>
              <h4 className="text-lg font-semibold text-slate-900 mb-2">Collect & Track</h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                The native Windows print agent submits your job to the HP Smart Tank 585 spooler and provides a verifiable receipt.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Preview Section */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2">
              Transparent Rates
            </h2>
            <h3 className="text-3xl font-bold text-slate-900 tracking-tight">
              Pay strictly for what you print
            </h3>
            <p className="mt-3 text-slate-600">
              Clear per-page pricing calculated on the server with zero hidden surcharges.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            {/* Grayscale Tier */}
            <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm relative overflow-hidden">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Academic Standard
              </span>
              <h4 className="text-2xl font-bold text-slate-900 mt-1">Grayscale / B&W</h4>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-slate-900">₹2.00</span>
                <span className="text-sm text-slate-500">/ per A4 page</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-slate-600">
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-500" /> Crisp 1200 DPI text rendering
                </li>
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-500" /> Ideal for notes, forms & research papers
                </li>
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-500" /> A4 Single-Sided output
                </li>
              </ul>
            </div>

            {/* Color Tier */}
            <div className="p-8 rounded-2xl bg-white border-2 border-brand-500 shadow-md relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-brand-500 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl-lg">
                High Quality
              </div>
              <span className="text-xs font-semibold uppercase tracking-wider text-brand-600">
                Vibrant & Detailed
              </span>
              <h4 className="text-2xl font-bold text-slate-900 mt-1">Full Color</h4>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-slate-900">₹10.00</span>
                <span className="text-sm text-slate-500">/ per A4 page</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-slate-600">
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-brand-500" /> High-saturation pigment ink
                </li>
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-brand-500" /> Ideal for charts, posters & certificates
                </li>
                <li className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-brand-500" /> A4 Single-Sided output
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Frequently Asked Questions */}
      <section className="py-20 bg-white border-t border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2">FAQ</h2>
            <h3 className="text-3xl font-bold text-slate-900 tracking-tight">
              Frequently Asked Questions
            </h3>
          </div>

          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <h4 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-brand-600" />
                What file formats are supported?
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                PrintX exclusively accepts Portable Document Format (.PDF) documents up to 50MB. Word docs or presentations can be saved as PDF prior to uploading.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <h4 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-brand-600" />
                Is double-sided (duplex) printing available?
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                The current campus kiosk printer (HP Smart Tank 585) is physically configured for reliable single-sided A4 printing. Duplex options are disabled in the interface to prevent paper jamming.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <h4 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-brand-600" />
                What happens if payment succeeds but printer runs out of paper?
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                PrintX tracks jobs through deterministic states. If a hardware spooler fault occurs, your job remains registered in the system with a unique job ID, allowing administrative reprint without double charging.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};


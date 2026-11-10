import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { 
  DocumentInfo, 
  PrintConfig, 
  PricingBreakdown,
  PrintJob,
  PaymentInfo
} from '../types';
import { 
  Upload, 
  Settings2, 
  Receipt, 
  CreditCard, 
  Printer, 
  CheckCircle2, 
  AlertCircle,
  FileText,
  FileCheck2,
  Trash2,
  Plus,
  Minus,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Info,
  Check,
  ShieldCheck,
  Eye,
  QrCode,
  Smartphone,
  ExternalLink,
  Download,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  X,
  Image as ImageIcon
} from 'lucide-react';

export const StudentPortal: React.FC = () => {
  const [searchParams] = useSearchParams();
  const kioskCode = searchParams.get('device') || 'KIOSK-01';

  // Wizard state
  const [activeStep, setActiveStep] = useState<number>(1);

  // Step 1: Document state
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [document, setDocument] = useState<DocumentInfo | null>(null);
  const [previewPage, setPreviewPage] = useState<number>(1);
  const [isZoomModalOpen, setIsZoomModalOpen] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Helper: check if a page number is within current configured page range
  const isPageInRange = (page: number, rangeStr: string): boolean => {
    if (!rangeStr || rangeStr === 'all' || !rangeStr.trim()) return true;
    const parts = rangeStr.split(',').map((p) => p.trim());
    for (const part of parts) {
      if (part.includes('-')) {
        const [start, end] = part.split('-').map(Number);
        if (!isNaN(start) && !isNaN(end) && page >= start && page <= end) return true;
      } else {
        if (Number(part) === page) return true;
      }
    }
    return false;
  };

  // Step 2: Configuration state
  const [config, setConfig] = useState<PrintConfig>({
    paper_size: 'A4',
    color_mode: 'grayscale',
    copies: 1,
    page_range: 'all',
    fit_to_page: true,
    duplex: false, // HP Smart Tank 585 is single-sided
  });

  // Step 3: Pricing breakdown
  const [pricing, setPricing] = useState<PricingBreakdown | null>(null);
  const [isEstimating, setIsEstimating] = useState<boolean>(false);

  // Step 4: Job & Payment state
  const [job, setJob] = useState<PrintJob | null>(null);
  const [payment, setPayment] = useState<PaymentInfo | null>(null);
  const [isCreatingJob, setIsCreatingJob] = useState<boolean>(false);
  const [isSimulatingPayment, setIsSimulatingPayment] = useState<boolean>(false);

  // Fetch Kiosk Configuration
  const { data: kiosk } = useQuery({
    queryKey: ['kiosk', kioskCode],
    queryFn: () => api.getKioskConfig(kioskCode),
  });

  // Fetch Printers Telemetry for Paper-Out / Online Interlock (Option C)
  const { data: printers } = useQuery({
    queryKey: ['printers-telemetry'],
    queryFn: () => api.listPrinters(),
    refetchInterval: 5000,
  });

  const targetPrinter = printers?.find((p: any) => p.name?.includes('Smart Tank') || p.is_default) || printers?.[0];
  const isPaperOut = targetPrinter?.status === 'out_of_paper' || targetPrinter?.status === 'PAPER_OUT';
  const isPrinterOffline = targetPrinter?.is_online === false || targetPrinter?.status === 'offline';

  // Re-estimate price whenever document or config changes
  useEffect(() => {
    if (!document) return;

    let isMounted = true;
    setIsEstimating(true);

    api.estimatePricing({
      page_count: document.page_count,
      copies: config.copies,
      color_mode: config.color_mode,
      page_range: config.page_range,
    })
      .then((res) => {
        if (isMounted) {
          setPricing(res.breakdown);
          setIsEstimating(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Pricing estimate error:', err);
          setIsEstimating(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [document, config]);

  // Real-Time Server-Sent Events (SSE) Stream with Polling Fallback (Option B)
  useEffect(() => {
    if (!job || activeStep < 4 || activeStep === 6) return;

    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(`/api/v1/jobs/${job.id}/stream`);

      eventSource.addEventListener('job_update', (e) => {
        try {
          const updatedJob = JSON.parse(e.data);
          setJob(updatedJob);

          // Zero-latency state progression
          if (activeStep === 4 && (updatedJob.status === 'PAYMENT_VERIFIED' || updatedJob.status === 'QUEUED')) {
            setActiveStep(5);
          }
          if (activeStep === 5 && updatedJob.status === 'COMPLETED') {
            setActiveStep(6);
          }
        } catch (err) {
          console.error('SSE job_update parse error:', err);
        }
      });

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
      };
    } catch (err) {
      console.warn('Failed to initialize SSE EventSource, using polling fallback:', err);
    }

    // Resilient Polling Fallback: runs every 4s
    const interval = setInterval(async () => {
      try {
        const updatedJob = await api.getJob(job.id);
        setJob(updatedJob);

        if (activeStep === 4 && (updatedJob.status === 'PAYMENT_VERIFIED' || updatedJob.status === 'QUEUED')) {
          setActiveStep(5);
        }

        if (activeStep === 5 && updatedJob.status === 'COMPLETED') {
          setActiveStep(6);
        }
      } catch (err) {
        console.error('Job polling error:', err);
      }
    }, 4000);

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      clearInterval(interval);
    };
  }, [job?.id, activeStep]);

  // Handle document/image file selection
  const handleFileUpload = async (file: File) => {
    setUploadError(null);

    const isPdf = file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
    const isImage = /\.(png|jpe?g|webp)$/i.test(file.name) || file.type.startsWith('image/');

    if (!isPdf && !isImage) {
      setUploadError('Only PDF documents or images (PNG, JPG, WEBP) are supported for printing.');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File size exceeds the 50MB maximum upload limit.');
      return;
    }

    setIsUploading(true);
    try {
      const res = await api.uploadDocument(file);
      setDocument(res.document);
      setPreviewPage(1);
      setActiveStep(2);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to process and validate document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleRemoveDocument = async () => {
    if (document) {
      try {
        await api.deleteDocument(document.id);
      } catch (err) {
        console.error('Error purging document:', err);
      }
      setDocument(null);
      setPricing(null);
      setJob(null);
      setPayment(null);
      setActiveStep(1);
    }
  };

  // Proceed from Step 3 (Review) to Step 4 (Payment)
  const handleProceedToPayment = async () => {
    if (!document || !pricing) return;
    setIsCreatingJob(true);

    try {
      // 1. Create Print Job on backend
      const idempotencyKey = `JOB-${document.id}-${Date.now()}`;
      const newJob = await api.createJob({
        document_id: document.id,
        kiosk_id: kiosk?.kiosk_id,
        configuration: {
          paper_size: 'A4',
          color_mode: config.color_mode,
          copies: config.copies,
          page_range: config.page_range,
          fit_to_page: config.fit_to_page,
          duplex: false
        },
        idempotency_key: idempotencyKey
      });
      setJob(newJob);

      // 2. Create Payment Order
      const newPayment = await api.createPayment({
        job_id: newJob.id,
        amount: newJob.price,
        provider: 'mock_upi',
        idempotency_key: `PAY-${newJob.id}`
      });
      setPayment(newPayment);

      setActiveStep(4);
    } catch (err: any) {
      alert(`Error initializing payment: ${err.message || err}`);
    } finally {
      setIsCreatingJob(false);
    }
  };

  // Simulate payment approval (Development Sandbox)
  const handleSimulatePaymentSuccess = async () => {
    if (!payment) return;
    setIsSimulatingPayment(true);
    try {
      const verified = await api.simulateUpiPaymentSuccess(payment.order_id);
      setPayment(verified);
      setActiveStep(5);
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setIsSimulatingPayment(false);
    }
  };

  const steps = [
    { num: 1, title: 'Upload', desc: 'Select PDF' },
    { num: 2, title: 'Configure', desc: 'Color & Copies' },
    { num: 3, title: 'Review', desc: 'Cost Breakdown' },
    { num: 4, title: 'Payment', desc: 'Instant UPI' },
    { num: 5, title: 'Printing', desc: 'Spooler Status' },
    { num: 6, title: 'Receipt', desc: 'Digital Proof' },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Kiosk Location Banner */}
      <div className="mb-8 p-4 rounded-xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-brand-600">
            Connected Kiosk Station
          </span>
          <h2 className="text-lg font-bold text-slate-900">
            {kiosk?.name || 'Loading Kiosk...'} ({kioskCode})
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {kiosk?.location || 'Detecting hardware location...'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 rounded-lg bg-slate-100 border border-slate-200 text-xs font-mono text-slate-700">
            {kiosk?.printer_name || 'HP Smart Tank 585'}
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Spooler Ready
          </div>
        </div>
      </div>

      {/* 6-Step Stepper Header */}
      <div className="mb-10">
        <div className="grid grid-cols-6 gap-2 sm:gap-4">
          {steps.map((s) => {
            const isCurrent = s.num === activeStep;
            const isCompleted = s.num < activeStep;
            return (
              <div 
                key={s.num} 
                onClick={() => {
                  if (document && s.num <= 3 && activeStep <= 3) {
                    setActiveStep(s.num);
                  }
                }}
                className={`flex flex-col items-center text-center p-2 rounded-xl transition-all ${
                  activeStep <= 3 ? 'cursor-pointer' : 'cursor-default'
                } ${
                  isCurrent ? 'bg-brand-50 border border-brand-200 shadow-sm' : ''
                }`}
              >
                <div 
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs mb-1.5 transition-colors ${
                    isCurrent 
                      ? 'bg-brand-600 text-white shadow-md shadow-brand-500/30 ring-2 ring-brand-300' 
                      : isCompleted 
                        ? 'bg-emerald-500 text-white' 
                        : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : s.num}
                </div>
                <span className={`text-xs font-bold ${isCurrent ? 'text-brand-900' : 'text-slate-700'}`}>
                  {s.title}
                </span>
                <span className="hidden sm:inline text-[10px] text-slate-400">
                  {s.desc}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Dynamic Step Area */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden p-6 sm:p-8">

        {/* ================= STEP 1: UPLOAD DOCUMENT ================= */}
        {activeStep === 1 && (
          <div>
            <div className="text-center max-w-xl mx-auto mb-8">
              <h3 className="text-2xl font-bold text-slate-900">Upload Your Document or Image</h3>
              <p className="text-sm text-slate-500 mt-1">
                Upload your assignment, thesis, ID card, or notes. PDF and images (PNG, JPG, WEBP) are automatically formatted to A4 single-sided print.
              </p>
            </div>

            {uploadError && (
              <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-800 text-sm">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold">Upload Validation Failed</h4>
                  <p className="mt-0.5 text-red-700">{uploadError}</p>
                </div>
              </div>
            )}

            {!document ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${
                  isUploading 
                    ? 'border-brand-400 bg-brand-50/50' 
                    : 'border-slate-300 hover:border-brand-500 hover:bg-slate-50'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".pdf,application/pdf,image/png,image/jpeg,image/jpg,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileUpload(e.target.files[0]);
                    }
                  }}
                />

                <div className="w-16 h-16 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto mb-4">
                  <Upload className={`w-8 h-8 ${isUploading ? 'animate-bounce' : ''}`} />
                </div>

                <h4 className="text-base font-bold text-slate-900">
                  {isUploading ? 'Validating and Formatting Document...' : 'Click to upload or drag & drop file'}
                </h4>
                <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                  PDF, PNG, JPG, or WEBP. Max 50MB. Images are automatically centered and fitted to standard A4 single-sided print.
                </p>

                <div className="mt-6 flex flex-wrap justify-center items-center gap-2 text-xs">
                  <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                    PDF Document
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
                    PNG / JPG Image
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                    Auto-Fit A4
                  </span>
                </div>
              </div>
            ) : (
              <div className="border border-slate-200 rounded-2xl p-6 bg-slate-50">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                      <FileCheck2 className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-slate-900 text-base">{document.original_filename}</h4>
                        {/\.(png|jpe?g|webp)$/i.test(document.original_filename) && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-[10px] font-semibold">
                            <ImageIcon className="w-3 h-3" /> Converted to A4
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                        <span className="font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                          {document.page_count} {document.page_count === 1 ? 'Page' : 'Pages'}
                        </span>
                        <span>{(document.file_size_bytes / 1024 / 1024).toFixed(2)} MB</span>
                        <span className="font-mono text-slate-400">SHA256 Verified</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <button
                      onClick={handleRemoveDocument}
                      className="p-2.5 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                      title="Remove Document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setActiveStep(2)}
                      className="flex-1 sm:flex-initial px-5 py-2.5 rounded-xl bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 transition-colors flex items-center justify-center gap-2"
                    >
                      Configure Prints
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Multi-Page Document Preview Carousel */}
                <div className="mt-6 pt-6 border-t border-slate-200">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                        <Eye className="w-3.5 h-3.5 text-brand-600" /> Document Preview
                      </span>
                      {document.page_count > 1 && (
                        <span className="text-xs text-slate-500 font-medium">
                          — Page {previewPage} of {document.page_count}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {document.page_count > 1 && (
                        <div className="flex items-center gap-1 bg-white px-2 py-1 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700">
                          <button
                            type="button"
                            onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                            disabled={previewPage <= 1}
                            className="p-1 rounded hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent"
                            title="Previous Page"
                          >
                            <ChevronLeft className="w-3.5 h-3.5" />
                          </button>
                          <span className="px-1 text-[11px] font-mono">
                            {previewPage} / {document.page_count}
                          </span>
                          <button
                            type="button"
                            onClick={() => setPreviewPage((p) => Math.min(document.page_count, p + 1))}
                            disabled={previewPage >= document.page_count}
                            className="p-1 rounded hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent"
                            title="Next Page"
                          >
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={() => setIsZoomModalOpen(true)}
                        className="p-1.5 rounded-lg border border-slate-200 hover:bg-white text-slate-600 transition-colors"
                        title="Zoom Preview"
                      >
                        <Maximize2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Main Page Preview Image */}
                  <div className="relative group flex justify-center p-4 bg-white rounded-xl border border-slate-200 overflow-hidden min-h-[280px] items-center">
                    <img 
                      src={api.getDocumentPreviewUrl(document.id, previewPage)} 
                      alt={`Page ${previewPage} Preview`}
                      className="max-h-80 object-contain rounded shadow-sm border border-slate-100 transition-transform group-hover:scale-[1.01]" 
                    />
                    
                    {/* Floating Page navigation buttons */}
                    {document.page_count > 1 && (
                      <>
                        <button
                          type="button"
                          onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                          disabled={previewPage <= 1}
                          className="absolute left-3 p-2 rounded-full bg-slate-900/60 hover:bg-slate-900 text-white backdrop-blur-sm disabled:opacity-0 transition-opacity"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setPreviewPage((p) => Math.min(document.page_count, p + 1))}
                          disabled={previewPage >= document.page_count}
                          className="absolute right-3 p-2 rounded-full bg-slate-900/60 hover:bg-slate-900 text-white backdrop-blur-sm disabled:opacity-0 transition-opacity"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>

                  {/* Thumbnail Strip (if > 1 page) */}
                  {document.page_count > 1 && (
                    <div className="mt-3 flex items-center gap-2 overflow-x-auto pb-2">
                      {Array.from({ length: document.page_count }, (_, i) => i + 1).map((pNum) => {
                        const isSelected = pNum === previewPage;
                        const inRange = isPageInRange(pNum, config.page_range);
                        return (
                          <button
                            key={pNum}
                            type="button"
                            onClick={() => setPreviewPage(pNum)}
                            className={`relative shrink-0 w-16 h-22 rounded-lg border p-1 transition-all text-center flex flex-col justify-between items-center ${
                              isSelected
                                ? 'border-brand-600 ring-2 ring-brand-500/30 bg-brand-50/50'
                                : 'border-slate-200 hover:border-slate-300 bg-white'
                            }`}
                          >
                            <img
                              src={api.getDocumentPreviewUrl(document.id, pNum)}
                              alt={`Thumbnail p.${pNum}`}
                              className="w-full h-14 object-cover rounded"
                            />
                            <div className="w-full flex items-center justify-between px-0.5 text-[10px] font-semibold">
                              <span className={isSelected ? 'text-brand-700' : 'text-slate-500'}>p.{pNum}</span>
                              {inRange ? (
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Included in print" />
                              ) : (
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-300" title="Excluded from print" />
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= STEP 2: CONFIGURE PRINTING ================= */}
        {activeStep === 2 && document && (
          <div>
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-2xl font-bold text-slate-900">Configure Print Preferences</h3>
                <p className="text-sm text-slate-500 mt-0.5">
                  Target Printer: <span className="font-semibold text-slate-700">HP Smart Tank 585</span>
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Document</span>
                <p className="text-sm font-bold text-slate-900">{document.original_filename}</p>
                <p className="text-xs text-brand-600 font-semibold">{document.page_count} Total Pages</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-6">

                {/* Color Mode Selection */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Color Mode
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => setConfig({ ...config, color_mode: 'grayscale' })}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        config.color_mode === 'grayscale'
                          ? 'border-brand-600 bg-brand-50/50 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">Grayscale / B&W</span>
                        {config.color_mode === 'grayscale' && (
                          <CheckCircle2 className="w-5 h-5 text-brand-600" />
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">Standard black & white laser-sharp text</p>
                      <div className="mt-3 text-sm font-extrabold text-slate-900">
                        ₹2.00 <span className="text-xs text-slate-500 font-normal">/ page</span>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setConfig({ ...config, color_mode: 'color' })}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        config.color_mode === 'color'
                          ? 'border-brand-600 bg-brand-50/50 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">Full Color</span>
                        {config.color_mode === 'color' && (
                          <CheckCircle2 className="w-5 h-5 text-brand-600" />
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">High-saturation pigment color</p>
                      <div className="mt-3 text-sm font-extrabold text-slate-900">
                        ₹10.00 <span className="text-xs text-slate-500 font-normal">/ page</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Copies Stepper */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Number of Copies (1 – 10)
                  </label>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setConfig({ ...config, copies: Math.max(1, config.copies - 1) })}
                      disabled={config.copies <= 1}
                      className="w-10 h-10 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 flex items-center justify-center text-slate-700 font-bold disabled:opacity-40"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-12 text-center text-xl font-bold text-slate-900">
                      {config.copies}
                    </span>
                    <button
                      type="button"
                      onClick={() => setConfig({ ...config, copies: Math.min(10, config.copies + 1) })}
                      disabled={config.copies >= 10}
                      className="w-10 h-10 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 flex items-center justify-center text-slate-700 font-bold disabled:opacity-40"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Page Range Input */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Page Range
                  </label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setConfig({ ...config, page_range: 'all' })}
                      className={`px-4 py-2 rounded-xl text-xs font-bold border transition-colors ${
                        config.page_range === 'all'
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      All ({document.page_count} Pages)
                    </button>
                    <input
                      type="text"
                      placeholder="e.g. 1-3, 5"
                      value={config.page_range === 'all' ? '' : config.page_range}
                      onChange={(e) => {
                        const val = e.target.value.trim();
                        setConfig({ ...config, page_range: val === '' ? 'all' : val });
                      }}
                      className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Enter individual pages or ranges separated by commas (e.g. 1-2, 4).
                  </p>
                </div>

                {/* Hardware Constraints: Single-Sided Badge */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
                    <Info className="w-4 h-4 text-brand-600" />
                    Hardware Notice: Single-Sided Printing Only
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    The HP Smart Tank 585 does not support automatic duplex. Documents are printed single-sided to guarantee smooth paper feeding.
                  </p>
                </div>
              </div>

              {/* Right Column: Live Price Breakdown Card */}
              <div>
                <div className="bg-slate-50 rounded-2xl border border-slate-200 p-6 sticky top-24">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">
                    Live Order Estimate
                  </h4>

                  {pricing ? (
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between text-slate-600">
                        <span>Selected Pages</span>
                        <span className="font-semibold text-slate-900">{pricing.selected_pages}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Copies</span>
                        <span className="font-semibold text-slate-900">{pricing.copies}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Rate per page</span>
                        <span className="font-semibold text-slate-900">₹{pricing.rate_per_page.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Total Impressions</span>
                        <span className="font-semibold text-slate-900">{pricing.total_impressions} sheets</span>
                      </div>
                      <div className="border-t border-slate-200 pt-3 flex justify-between items-baseline">
                        <span className="font-bold text-slate-900 text-base">Total Amount</span>
                        <span className="font-extrabold text-2xl text-brand-600">
                          ₹{pricing.total_amount.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-xs text-slate-400">
                      Calculating price breakdown...
                    </div>
                  )}

                  <div className="mt-6 flex flex-col gap-2">
                    <button
                      onClick={() => setActiveStep(3)}
                      disabled={!pricing || isEstimating}
                      className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm transition-colors shadow-md shadow-brand-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      Review Order
                      <ArrowRight className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setActiveStep(1)}
                      className="w-full py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200 transition-colors"
                    >
                      Back to Upload
                    </button>
                  </div>

                  {/* Compact Live Page Preview in Step 2 */}
                  <div className="mt-6 pt-5 border-t border-slate-200">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
                      <span className="flex items-center gap-1.5">
                        <Eye className="w-3.5 h-3.5 text-brand-600" />
                        Page {previewPage} of {document.page_count}
                      </span>
                      {document.page_count > 1 && (
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                            disabled={previewPage <= 1}
                            className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"
                            title="Previous Page"
                          >
                            <ChevronLeft className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setPreviewPage((p) => Math.min(document.page_count, p + 1))}
                            disabled={previewPage >= document.page_count}
                            className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"
                            title="Next Page"
                          >
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                    <div 
                      onClick={() => setIsZoomModalOpen(true)}
                      className="flex justify-center p-2 bg-white rounded-xl border border-slate-200 overflow-hidden cursor-pointer hover:border-brand-400 transition-colors group relative"
                      title="Click to Zoom"
                    >
                      <img
                        src={api.getDocumentPreviewUrl(document.id, previewPage)}
                        alt={`Page ${previewPage} Preview`}
                        className="max-h-48 object-contain rounded"
                      />
                      <div className="absolute inset-0 bg-slate-900/10 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <span className="p-1.5 rounded-lg bg-white/90 text-slate-800 shadow text-xs font-medium flex items-center gap-1">
                          <Maximize2 className="w-3 h-3" /> Zoom
                        </span>
                      </div>
                    </div>
                    {/* Range Inclusion Feedback */}
                    <div className="mt-2 text-center text-[11px]">
                      {isPageInRange(previewPage, config.page_range) ? (
                        <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          ✓ Page {previewPage} included in this print
                        </span>
                      ) : (
                        <span className="text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                          ✕ Page {previewPage} skipped by page range
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= STEP 3: REVIEW ORDER ================= */}
        {activeStep === 3 && document && pricing && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-wider text-brand-600">Step 3 of 6</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">Review Print Order</h3>
              <p className="text-sm text-slate-500 mt-1">
                Please verify your printing specifications before generating the payment order.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 space-y-4 mb-6">
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-sm text-slate-500">Document</span>
                <span className="font-bold text-slate-900 text-sm">{document.original_filename}</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-sm text-slate-500">Target Printer</span>
                <span className="font-bold text-slate-900 text-sm">HP Smart Tank 585 (A4 Single-Sided)</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-sm text-slate-500">Color Mode</span>
                <span className="font-bold text-slate-900 text-sm capitalize">{config.color_mode}</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-sm text-slate-500">Selected Pages</span>
                <span className="font-bold text-slate-900 text-sm">{pricing.selected_pages} page(s)</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-sm text-slate-500">Copies</span>
                <span className="font-bold text-slate-900 text-sm">{config.copies}</span>
              </div>
              <div className="flex justify-between items-baseline pt-2">
                <div>
                  <span className="font-bold text-slate-900 text-base">Grand Total</span>
                  <p className="text-[11px] text-slate-400">Server verified with ₹{pricing.rate_per_page.toFixed(2)}/page rate</p>
                </div>
                <span className="font-extrabold text-3xl text-brand-600">
                  ₹{pricing.total_amount.toFixed(2)}
                </span>
              </div>
            </div>

            {isPaperOut && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-800 flex items-start gap-3 mb-6 text-left">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm">Paper Tray Empty — Checkout Blocked</div>
                  <div className="text-xs text-amber-700 mt-0.5">
                    The printer at this kiosk is currently out of paper. To protect your payment, checkout is locked until the paper tray is reloaded.
                  </div>
                </div>
              </div>
            )}
            {isPrinterOffline && !isPaperOut && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-800 flex items-start gap-3 mb-6 text-left">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm">Printer Currently Offline</div>
                  <div className="text-xs text-amber-700 mt-0.5">
                    The kiosk printer is currently offline or disconnected. Please notify attendant before proceeding.
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center gap-4">
              <button
                onClick={() => setActiveStep(2)}
                className="w-1/3 py-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm transition-colors"
              >
                Modify Settings
              </button>
              <button
                onClick={handleProceedToPayment}
                disabled={isCreatingJob || isPaperOut || isPrinterOffline}
                className="w-2/3 py-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-base transition-colors shadow-lg shadow-brand-500/25 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPaperOut
                  ? 'Paper Tray Empty'
                  : isPrinterOffline
                  ? 'Printer Offline'
                  : isCreatingJob
                  ? 'Initializing Payment...'
                  : 'Proceed to UPI Payment'}
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* ================= STEP 4: PAYMENT (UPI QR) ================= */}
        {activeStep === 4 && job && payment && (
          <div className="max-w-lg mx-auto text-center">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold uppercase tracking-wider mb-3">
              <Smartphone className="w-3.5 h-3.5 text-brand-600" />
              Scan with any UPI App
            </div>
            <h3 className="text-2xl font-bold text-slate-900">Complete UPI Payment</h3>
            <p className="text-sm text-slate-500 mt-1">
              Order Ref: <span className="font-mono text-slate-700 font-semibold">{payment.order_id}</span>
            </p>

            {isPaperOut && (
              <div className="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-800 flex items-start gap-3 text-left">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm">Hardware Interlock: Paper Tray Empty</div>
                  <div className="text-xs text-amber-700 mt-0.5">
                    The printer paper tray is currently empty. Please notify attendant or reload paper before completing payment.
                  </div>
                </div>
              </div>
            )}

            {/* UPI QR Display Card */}
            <div className="mt-8 p-6 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col items-center">
              <div className="w-56 h-56 bg-white p-3 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-center overflow-hidden">
                {payment.qr_code_base64 ? (
                  <img
                    src={payment.qr_code_base64}
                    alt="UPI Payment QR Code"
                    className="w-full h-full object-contain rounded-lg"
                  />
                ) : (
                  <img
                    src={`/api/v1/payments/${payment.id}/qr.png`}
                    alt="UPI Payment QR Code"
                    className="w-full h-full object-contain rounded-lg"
                  />
                )}
              </div>

              {/* Mobile UPI Deep Link */}
              {payment.upi_qr_data && (
                <a
                  href={payment.upi_qr_data}
                  className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors shadow-2xs"
                >
                  <Smartphone className="w-3.5 h-3.5 text-brand-600" />
                  Open UPI App on Phone
                </a>
              )}

              <div className="mt-3 text-[11px] font-mono text-slate-500 break-all max-w-xs text-center">
                {payment.upi_qr_data}
              </div>

              <div className="mt-4 flex items-center gap-2 text-xs font-medium text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping" />
                <span>Listening for secure server verification...</span>
              </div>
            </div>

            {/* Development Sandbox Simulation Controls */}
            <div className="mt-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-left">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                <Sparkles className="w-4 h-4 text-amber-600" />
                Development Sandbox Mode
              </div>
              <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                In local testing, you can simulate instantaneous UPI payment verification without real money.
              </p>
              <button
                onClick={handleSimulatePaymentSuccess}
                disabled={isSimulatingPayment}
                className="mt-3 w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs transition-colors shadow-sm disabled:opacity-50"
              >
                {isSimulatingPayment ? 'Verifying...' : 'Simulate UPI Approval (Authorize Print)'}
              </button>
            </div>
          </div>
        )}

        {/* ================= STEP 5: PRINTING STATUS TIMELINE ================= */}
        {activeStep === 5 && job && (
          <div className="max-w-xl mx-auto">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-wider text-brand-600">Live Progress</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">Executing Print Job</h3>
              <p className="text-sm text-slate-500 mt-1">
                Job ID: <span className="font-mono font-bold text-slate-900">{job.job_number}</span>
              </p>
            </div>

            {/* Stepper Timeline */}
            <div className="space-y-6 relative pl-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              
              {/* Event 1: Payment Verified */}
              <div className="relative">
                <div className="absolute -left-8 top-0.5 w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                  <Check className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Payment Verified</h4>
                  <p className="text-xs text-slate-500">Server verified UPI payment transaction.</p>
                </div>
              </div>

              {/* Event 2: Queued */}
              <div className="relative">
                <div className={`absolute -left-8 top-0.5 w-6 h-6 rounded-full flex items-center justify-center ${
                  ['QUEUED', 'DISPATCHED', 'SUBMITTED_TO_SPOOLER', 'PRINTING', 'COMPLETED'].includes(job.status)
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-200 text-slate-500'
                }`}>
                  <Check className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Queued for Windows Controller</h4>
                  <p className="text-xs text-slate-500">
                    {job.status === 'QUEUED' && job.queue_position ? (
                      <span className="font-semibold text-brand-600">
                        Position #{job.queue_position} in line (Estimated wait: ~{job.estimated_wait_seconds || 10}s)
                      </span>
                    ) : (
                      'Authorized job entered the local print dispatch queue.'
                    )}
                  </p>
                </div>
              </div>

              {/* Event 3: Submitted to Spooler */}
              <div className="relative">
                <div className={`absolute -left-8 top-0.5 w-6 h-6 rounded-full flex items-center justify-center ${
                  ['SUBMITTED_TO_SPOOLER', 'PRINTING', 'COMPLETED'].includes(job.status)
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-200 text-slate-500'
                }`}>
                  <Check className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Submitted to Windows Spooler</h4>
                  <p className="text-xs text-slate-500">
                    SumatraPDF CLI transferred document to queue: HP Smart Tank 580-590 series.
                  </p>
                </div>
              </div>

              {/* Event 4: Physical Spool Completion */}
              <div className="relative">
                <div className={`absolute -left-8 top-0.5 w-6 h-6 rounded-full flex items-center justify-center ${
                  job.status === 'COMPLETED'
                    ? 'bg-emerald-500 text-white'
                    : job.status === 'FAILED'
                    ? 'bg-red-500 text-white'
                    : 'bg-slate-200 text-slate-500 animate-pulse'
                }`}>
                  {job.status === 'COMPLETED' ? (
                    <Check className="w-3.5 h-3.5" />
                  ) : job.status === 'FAILED' ? (
                    <AlertCircle className="w-3.5 h-3.5" />
                  ) : (
                    <Printer className="w-3.5 h-3.5" />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    {job.status === 'COMPLETED'
                      ? 'Paper Output Ready'
                      : job.status === 'FAILED'
                      ? 'Print Interrupted'
                      : 'Paper Spooling & Printing...'}
                  </h4>
                  <p className="text-xs text-slate-500">
                    {job.status === 'COMPLETED'
                      ? 'Job cleared spooler buffer. Please collect your paper from the output tray.'
                      : job.status === 'FAILED'
                      ? (job.error_message || 'Hardware or transmission issue detected.')
                      : 'Hardware buffer transmission in progress.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Failure State & Safe Retry Card */}
            {job.status === 'FAILED' && (
              <div className="mt-6 p-4 rounded-xl bg-red-50 border border-red-200 text-left">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-red-900">Printing Interrupted</h4>
                    <p className="text-xs text-red-700 mt-1">
                      {job.error_message || 'The printer reported an error or spooler timeout.'}
                    </p>
                    <p className="text-xs text-red-600 mt-2 font-medium">
                      Duplicate Protection: Please verify whether paper exited the HP Smart Tank 585 tray before retrying.
                    </p>
                    <button
                      onClick={async () => {
                        try {
                          const updated = await api.retryJob(job.id, true, "Student retry from web portal");
                          setJob(updated);
                        } catch (err: any) {
                          alert(`Retry error: ${err.message}`);
                        }
                      }}
                      className="mt-3 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-xs transition-colors shadow-2xs"
                    >
                      Safe Retry Print Job
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Advance to Receipt Button */}
            <div className="mt-8 text-center">
              <button
                onClick={() => setActiveStep(6)}
                className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm transition-colors"
              >
                View Digital Receipt
              </button>
            </div>
          </div>
        )}

        {/* ================= STEP 6: DIGITAL RECEIPT ================= */}
        {activeStep === 6 && job && (
          <div className="max-w-xl mx-auto">
            <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm print:border-none print:shadow-none">
              <div className="text-center pb-6 border-b border-slate-200">
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto mb-3">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900">PrintX Official Receipt</h3>
                <p className="text-xs text-slate-500 mt-0.5">Automated Self-Service Document Center</p>
              </div>

              <div className="py-6 space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Job Reference</span>
                  <span className="font-mono font-bold text-slate-900">{job.job_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Transaction Ref</span>
                  <span className="font-mono text-slate-700">{payment?.gateway_transaction_id || payment?.order_id || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Document</span>
                  <span className="font-semibold text-slate-900">{document?.original_filename}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Pages Printed</span>
                  <span className="font-semibold text-slate-900">{job.total_pages} page(s)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Copies</span>
                  <span className="font-semibold text-slate-900">{job.configuration?.copies || 1}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Printing Mode</span>
                  <span className="font-semibold text-slate-900 capitalize">
                    {job.configuration?.color_mode || 'Grayscale'} (A4 Single-Sided)
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Timestamp</span>
                  <span className="text-slate-700">{new Date(job.created_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Final Status</span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {job.status}
                  </span>
                </div>
                <div className="border-t border-slate-200 pt-3 flex justify-between items-baseline">
                  <span className="font-bold text-slate-900 text-base">Total Paid</span>
                  <span className="font-extrabold text-2xl text-emerald-600">₹{job.price.toFixed(2)}</span>
                </div>
              </div>

              <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row gap-3 print:hidden">
                <button
                  onClick={() => window.print()}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm flex items-center justify-center gap-2 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Print Receipt
                </button>
                <button
                  onClick={() => {
                    setDocument(null);
                    setPricing(null);
                    setJob(null);
                    setPayment(null);
                    setActiveStep(1);
                  }}
                  className="flex-1 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors shadow-sm"
                >
                  <RotateCcw className="w-4 h-4" />
                  Start New Job
                </button>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* High-Resolution Zoom Preview Modal */}
      {isZoomModalOpen && document && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setIsZoomModalOpen(false)}
        >
          <div
            className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <span className="font-bold text-white text-sm">{document.original_filename}</span>
                <span className="text-xs text-slate-400 font-mono">
                  Page {previewPage} of {document.page_count}
                </span>
                {isPageInRange(previewPage, config.page_range) ? (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold">
                    Included in Order
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-semibold">
                    Excluded by Page Range
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setIsZoomModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body: Large Preview */}
            <div className="flex-1 overflow-auto p-4 flex items-center justify-center relative min-h-[400px]">
              <img
                src={api.getDocumentPreviewUrl(document.id, previewPage)}
                alt={`Page ${previewPage} Full View`}
                className="max-h-[68vh] object-contain rounded-lg shadow-2xl border border-slate-800 bg-white"
              />

              {document.page_count > 1 && (
                <>
                  <button
                    type="button"
                    onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                    disabled={previewPage <= 1}
                    className="absolute left-6 p-3 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white backdrop-blur-md disabled:opacity-0 transition-opacity"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewPage((p) => Math.min(document.page_count, p + 1))}
                    disabled={previewPage >= document.page_count}
                    className="absolute right-6 p-3 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white backdrop-blur-md disabled:opacity-0 transition-opacity"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <span>Press Esc or click outside to dismiss</span>
              {document.page_count > 1 && (
                <div className="flex items-center gap-1 font-mono">
                  <span>Use arrow buttons to flip pages</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import { 
  HealthResponse, 
  HealthReadyResponse, 
  PricingEstimateResponse, 
  KioskConfig,
  DocumentUploadResponse,
  DocumentInfo
} from '../types';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('printx_token');
  const headers = new Headers(options.headers || {});
  
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Network request failed';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Health
  getHealth: () => request<HealthResponse>('/health'),
  getReady: () => request<HealthReadyResponse>('/health/ready'),

  // Documents
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<DocumentUploadResponse>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },
  getDocument: (id: string) => request<DocumentInfo>(`/documents/${id}`),
  getDocumentPreviewUrl: (id: string, page: number = 1) => `${API_BASE}/documents/${id}/preview?page=${page}`,
  deleteDocument: (id: string) => request<{ message: string }>(`/documents/${id}`, { method: 'DELETE' }),

  // Kiosks
  getKioskConfig: (kioskId: string) => request<KioskConfig>(`/kiosks/${kioskId}/configuration`),

  // Pricing
  estimatePricing: (payload: {
    page_count: number;
    copies: number;
    color_mode: string;
    page_range: string;
  }) => request<PricingEstimateResponse>('/pricing/estimate', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // Jobs
  createJob: (payload: {
    document_id: string;
    kiosk_id?: string;
    printer_id?: string;
    configuration: {
      paper_size: string;
      color_mode: string;
      copies: number;
      page_range: string;
      fit_to_page: boolean;
      duplex: boolean;
    };
    idempotency_key: string;
  }) => request<any>('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getJob: (jobId: string) => request<any>(`/jobs/${jobId}`),
  listJobs: () => request<any[]>('/jobs'),
  cancelJob: (jobId: string) => request<any>(`/jobs/${jobId}/cancel`, { method: 'POST' }),
  retryJob: (jobId: string, forceRetry: boolean = false, notes?: string) => request<any>(`/jobs/${jobId}/retry`, {
    method: 'POST',
    body: JSON.stringify({ force_retry: forceRetry, operator_notes: notes }),
  }),

  // Payments
  createPayment: (payload: {
    job_id: string;
    amount: number;
    provider: string;
    idempotency_key: string;
  }) => request<any>('/payments/create', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getPayment: (paymentId: string) => request<any>(`/payments/${paymentId}`),
  simulateUpiPaymentSuccess: (orderId: string) => request<any>(`/payments/simulate-success/${orderId}`, {
    method: 'POST',
  }),

  // Admin
  getAdminAnalytics: () => request<any>('/admin/analytics'),
  getAdminJobs: () => request<any>('/admin/jobs'),
  getAdminPayments: () => request<any>('/admin/payments'),
  updatePricingRule: (payload: any) => request<any>('/admin/pricing', {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  listPrinters: () => request<any[]>('/printers'),
};


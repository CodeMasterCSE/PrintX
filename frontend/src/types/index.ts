export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface HealthReadyResponse {
  status: string;
  database: string;
  storage: string;
  timestamp: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  role: 'student' | 'admin' | 'agent';
  is_active: boolean;
  created_at: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  is_encrypted: boolean;
  is_color: boolean;
  status: string;
  sha256_checksum: string;
  created_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentInfo;
  message: string;
}

export interface PrintConfig {
  paper_size: 'A4';
  color_mode: 'grayscale' | 'color';
  copies: number;
  page_range: string;
  fit_to_page: boolean;
  duplex: boolean; // Always false for MVP
}

export interface PricingBreakdown {
  selected_pages: number;
  copies: number;
  total_impressions: number;
  rate_per_page: number;
  base_fee: number;
  subtotal: number;
  discount: number;
  total_amount: number;
  currency: string;
}

export interface PricingEstimateResponse {
  breakdown: PricingBreakdown;
  pricing_rule_name: string;
}

export interface PaymentInfo {
  id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: 'pending' | 'verified' | 'failed' | 'expired' | 'refunded';
  provider: string;
  payment_method: string;
  gateway_transaction_id?: string;
  upi_qr_data?: string;
  qr_code_base64?: string;
  is_mock?: boolean;
  created_at: string;
}

export type JobStatus =
  | 'CREATED'
  | 'DOCUMENT_VALIDATED'
  | 'PAYMENT_PENDING'
  | 'PAYMENT_VERIFIED'
  | 'QUEUED'
  | 'DISPATCHED'
  | 'SUBMITTED_TO_SPOOLER'
  | 'PRINTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'EXPIRED';

export interface JobEvent {
  id: string;
  previous_status?: string;
  new_status: string;
  message?: string;
  created_at: string;
}

export interface PrintJob {
  id: string;
  job_number: string;
  status: JobStatus;
  price: number;
  total_pages: number;
  sheets_used: number;
  error_message?: string;
  spooler_job_id?: number;
  idempotency_key: string;
  queue_position?: number;
  estimated_wait_seconds?: number;
  document_id: string;
  document?: DocumentInfo;
  configuration?: PrintConfig;
  payment?: PaymentInfo;
  events?: JobEvent[];
  created_at: string;
  updated_at: string;
}

export interface KioskConfig {
  kiosk_id: string;
  code: string;
  name: string;
  location: string;
  printer_name?: string;
  supports_color: boolean;
  supports_duplex: boolean;
  per_page_bw: number;
  per_page_color: number;
  lan_ip?: string;
  mobile_portal_url?: string;
}


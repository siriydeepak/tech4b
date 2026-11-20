export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "jeweller" | "admin";
  phone?: string;
  business_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Deduction {
  label: string;
  amount: number;
}

export interface DeductionOut extends Deduction {
  id: string;
}

export interface ExchangeCalculateRequest {
  gross_weight: number;
  non_gold_weight: number;
  purity_percentage: number;
  reference_rate: number;
  deductions: Deduction[];
}

export interface ExchangeCalculateResponse {
  gross_weight: number;
  non_gold_weight: number;
  net_gold_weight: number;
  purity_percentage: number;
  reference_rate: number;
  fine_gold_equivalent: number;
  metal_value: number;
  deductions: Deduction[];
  total_deductions: number;
  final_value: number;
}

export interface TransactionCreate {
  customer_id: string;
  article_id?: string;
  gross_weight: number;
  non_gold_weight: number;
  purity_percentage: number;
  reference_rate: number;
  deductions: Deduction[];
  notes?: string;
}

export interface Transaction {
  id: string;
  jeweller_id: string;
  customer_id: string;
  article_id?: string;
  gross_weight: number;
  non_gold_weight: number;
  net_gold_weight: number;
  purity_percentage: number;
  reference_rate: number;
  fine_gold_equivalent: number;
  metal_value: number;
  total_deductions: number;
  final_value: number;
  status: "draft" | "confirmed" | "completed" | "cancelled";
  notes?: string;
  created_at: string;
  deductions: DeductionOut[];
}

export interface GoldArticle {
  id: string;
  owner_id: string;
  article_name: string;
  description?: string;
  hallmark?: string;
  created_at: string;
}

export interface ApiError {
  detail: string;
}


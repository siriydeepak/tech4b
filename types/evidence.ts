/**
 * AURUM — Evidence Categorization & Media Types
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Strict architectural rule:
 * Every piece of evidence in AURUM MUST be categorized into one of 4 provenance tiers
 * to prevent manually entered or customer-submitted values from being represented
 * as independently verified data.
 */

export type EvidenceProvenance = 
  | 'OFFICIALLY_VERIFIED'    // Retrieved from BIS CARE portal or authorized gov APIs
  | 'INSTRUMENT_RECORDED'   // Direct XRF spectrum / electronic scale readout photos/logs
  | 'JEWELLER_ENTERED'      // Physical values manually entered by the jeweller at exchange counter
  | 'CUSTOMER_PROVIDED';    // Initial claims, purchase bills, old receipts uploaded by customer

export type EvidenceCategory =
  | 'JEWELLERY_PHOTO'
  | 'HALLMARK_HUID_PHOTO'
  | 'XRF_SPECTROMETER_READOUT'
  | 'WEIGHING_SCALE_READOUT'
  | 'ORIGINAL_PURCHASE_INVOICE'
  | 'LAB_ASSAY_CERTIFICATE'
  | 'BIS_CARE_SCREENSHOT';

export interface EvidenceItem {
  id: string;
  transactionId?: string;
  jewelleryId: string;
  category: EvidenceCategory;
  provenance: EvidenceProvenance;
  fileUrl: string;
  fileName: string;
  mimeType: 'image/jpeg' | 'image/png' | 'image/webp' | 'application/pdf';
  fileSizeBytes: number;
  sha256Hash: string; // Cryptographic hash for tamper resistance & dispute replay
  uploadedBy: {
    userId: string;
    role: 'CUSTOMER' | 'JEWELLER' | 'ADMIN';
  };
  recordedAt: string; // ISO 8601 UTC timestamp
  notes?: string;
}

/**
 * UI display metadata for evidence tiers
 */
export const PROVENANCE_METADATA: Record<EvidenceProvenance, {
  label: string;
  description: string;
  badgeVariant: 'default' | 'secondary' | 'outline' | 'destructive';
  colorHex: string;
  trustScoreWeight: number; // 0 to 1
}> = {
  OFFICIALLY_VERIFIED: {
    label: 'Officially Verified',
    description: 'Validated through Bureau of Indian Standards (BIS CARE) official hallmark database.',
    badgeVariant: 'default',
    colorHex: '#16a34a', // Emerald Green
    trustScoreWeight: 1.0,
  },
  INSTRUMENT_RECORDED: {
    label: 'Instrument Recorded',
    description: 'Direct measurement proof from certified XRF Spectrometer or calibrated digital precision balance.',
    badgeVariant: 'secondary',
    colorHex: '#0284c7', // Sky Blue
    trustScoreWeight: 0.9,
  },
  JEWELLER_ENTERED: {
    label: 'Jeweller Entered',
    description: 'Manual measurement recorded by certified assayer/jeweller during counter inspection.',
    badgeVariant: 'outline',
    colorHex: '#d97706', // Amber
    trustScoreWeight: 0.7,
  },
  CUSTOMER_PROVIDED: {
    label: 'Customer Provided',
    description: 'Self-reported details, old bills or preliminary photographs uploaded by customer.',
    badgeVariant: 'outline',
    colorHex: '#64748b', // Slate Gray
    trustScoreWeight: 0.4,
  },
};

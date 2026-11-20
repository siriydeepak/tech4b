/**
 * AURUM — Physical & Hallmark Verification Types
 * Member 2: Verification, Evidence Pipeline & Data Management
 */

import { GoldKarat, JewelleryType } from './jewellery';
import { EvidenceItem } from './evidence';

export type HUIDVerificationStatus = 
  | 'VALID_VERIFIED'   // Official record found in BIS registry and matches submitted item
  | 'MISMATCH'         // Record found in BIS registry, but purity or article type differs
  | 'NOT_FOUND'        // 6-digit HUID not present in BIS database
  | 'INVALID_FORMAT';  // Does not match standard 6-character alphanumeric pattern

export interface BISCareRecord {
  huid: string;
  articleType: JewelleryType;
  purityKarat: GoldKarat;
  purityFineness: number; // e.g. 916, 750, 999
  jewellerName: string;
  jewellerRegistrationNumber: string;
  ahcCenterName: string; // Assaying & Hallmarking Centre
  ahcRegistrationNumber: string;
  hallmarkingDate: string;
  recordedWeightGrams?: number;
  officialPhotoUrl?: string;
}

export interface PhysicalMeasurementInput {
  jewelleryId: string;
  jewellerId: string;
  grossWeightGrams: number;
  stoneWeightGrams: number;
  netGoldWeightGrams: number;
  xrfPurityPercent: number; // 0 to 100
  xrfMeasuredFineness: number; // e.g. 916.5
  elementalComposition?: {
    Au: number; // Gold percentage
    Ag?: number; // Silver percentage
    Cu?: number; // Copper percentage
    Zn?: number; // Zinc percentage
    Cd?: number; // Cadmium percentage (toxic alert if > 0.1)
  };
  weighScaleDeviceModel?: string;
  xrfDeviceModel?: string;
  measurementTimestamp: string;
}

export type DiscrepancySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface DiscrepancyReport {
  code: 
    | 'PURITY_DOWNGRADE'
    | 'PURITY_UPGRADE'
    | 'WEIGHT_MISMATCH'
    | 'ARTICLE_TYPE_MISMATCH'
    | 'HUID_NOT_FOUND'
    | 'MISSING_MANDATORY_EVIDENCE'
    | 'TOXIC_SOLDER_DETECTED';
  severity: DiscrepancySeverity;
  field: string;
  declaredValue: string | number;
  measuredOrVerifiedValue: string | number;
  variancePercentage?: number;
  explanation: string;
}

export interface VerificationSessionResult {
  sessionId: string;
  jewelleryId: string;
  huidStatus: HUIDVerificationStatus;
  bisDetails?: BISCareRecord;
  physicalMeasurements: PhysicalMeasurementInput;
  attachedEvidence: EvidenceItem[];
  discrepancies: DiscrepancyReport[];
  trustScore: number; // 0 - 100
  isApprovedForValuation: boolean;
  verifiedAt: string;
}

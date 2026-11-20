/**
 * AURUM — BIS CARE HUID Verification Service
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Handles Bureau of Indian Standards (BIS) Hallmarking Unique Identification (HUID)
 * format validation, lookup against registry, and discrepancy detection.
 */

import { BISCareRecord, DiscrepancyReport, HUIDVerificationStatus } from '../types/verification';
import { GoldKarat, JewelleryType } from '../types/jewellery';

/**
 * Validates the syntax of a 6-character alphanumeric BIS HUID
 */
export function validateHUIDFormat(huid: string): { isValid: boolean; normalizedHUID: string; error?: string } {
  if (!huid) {
    return { isValid: false, normalizedHUID: '', error: 'HUID cannot be empty.' };
  }

  const cleaned = huid.trim().toUpperCase();

  // BIS HUIDs are strictly 6 alphanumeric characters (A-Z, 0-9)
  const huidRegex = /^[A-Z0-9]{6}$/;

  if (!huidRegex.test(cleaned)) {
    return { 
      isValid: false, 
      normalizedHUID: cleaned, 
      error: 'Invalid format. A valid BIS HUID must be exactly 6 alphanumeric characters (e.g., A1B2C3).' 
    };
  }

  return { isValid: true, normalizedHUID: cleaned };
}

/**
 * Mock / Simulated BIS Hallmarking Registry database for MVP demonstration.
 * In production, this interfaces with BIS CARE verified APIs or official scraping pipelines.
 */
const MOCK_BIS_REGISTRY: Record<string, BISCareRecord> = {
  'A1B2C3': {
    huid: 'A1B2C3',
    articleType: 'CHAIN',
    purityKarat: '22K',
    purityFineness: 916,
    jewellerName: 'Tanishq Jewellers Indiranagar',
    jewellerRegistrationNumber: 'BIS-JWL-KA-560038',
    ahcCenterName: 'Bangalore Assaying & Hallmarking Centre',
    ahcRegistrationNumber: 'AHC-KA-004',
    hallmarkingDate: '2025-08-14T10:30:00Z',
    recordedWeightGrams: 12.50,
  },
  'H7K9M2': {
    huid: 'H7K9M2',
    articleType: 'BANGLE',
    purityKarat: '22K',
    purityFineness: 916,
    jewellerName: 'Malabar Gold & Diamonds MG Road',
    jewellerRegistrationNumber: 'BIS-JWL-KA-560001',
    ahcCenterName: 'South India Hallmarking Federation',
    ahcRegistrationNumber: 'AHC-KA-012',
    hallmarkingDate: '2024-11-20T14:15:00Z',
    recordedWeightGrams: 24.80,
  },
  'X8Y9Z1': {
    huid: 'X8Y9Z1',
    articleType: 'RING',
    purityKarat: '18K',
    purityFineness: 750,
    jewellerName: 'CaratLane Jayanagar',
    jewellerRegistrationNumber: 'BIS-JWL-KA-560011',
    ahcCenterName: 'Deccan Assay Labs Bangalore',
    ahcRegistrationNumber: 'AHC-KA-009',
    hallmarkingDate: '2025-01-10T16:45:00Z',
    recordedWeightGrams: 4.20,
  },
  'N4P6Q8': {
    huid: 'N4P6Q8',
    articleType: 'NECKLACE',
    purityKarat: '22K',
    purityFineness: 916,
    jewellerName: 'Kalyan Jewellers Commercial Street',
    jewellerRegistrationNumber: 'BIS-JWL-KA-560042',
    ahcCenterName: 'Karnataka Bullion Assaying Laboratory',
    ahcRegistrationNumber: 'AHC-KA-002',
    hallmarkingDate: '2023-05-18T11:00:00Z',
    recordedWeightGrams: 36.40,
  },
  'C2D3E4': {
    huid: 'C2D3E4',
    articleType: 'GOLD_COIN',
    purityKarat: '24K',
    purityFineness: 999,
    jewellerName: 'MMTC-PAMP India Bullion Outlet',
    jewellerRegistrationNumber: 'BIS-JWL-DL-110001',
    ahcCenterName: 'National Refineries & Hallmark Centre',
    ahcRegistrationNumber: 'AHC-DL-001',
    hallmarkingDate: '2025-03-01T09:30:00Z',
    recordedWeightGrams: 10.00,
  },
  // Intentional Mismatch Record for test demonstrations:
  'MIS001': {
    huid: 'MIS001',
    articleType: 'BANGLE',
    purityKarat: '18K', // Customer may declare 22K Chain!
    purityFineness: 750,
    jewellerName: 'Apex Hallmarked Ornaments',
    jewellerRegistrationNumber: 'BIS-JWL-KA-560099',
    ahcCenterName: 'Apex Assay Hub',
    ahcRegistrationNumber: 'AHC-KA-099',
    hallmarkingDate: '2024-02-12T15:00:00Z',
    recordedWeightGrams: 8.50,
  }
};

/**
 * Look up HUID in official BIS Registry (or simulated cache)
 */
export async function queryBISHUID(huid: string): Promise<{
  status: HUIDVerificationStatus;
  record?: BISCareRecord;
  message: string;
}> {
  const { isValid, normalizedHUID, error } = validateHUIDFormat(huid);

  if (!isValid) {
    return {
      status: 'INVALID_FORMAT',
      message: error || 'Invalid HUID format.',
    };
  }

  // Simulate network latency (250ms)
  await new Promise((resolve) => setTimeout(resolve, 250));

  const foundRecord = MOCK_BIS_REGISTRY[normalizedHUID];

  if (!foundRecord) {
    return {
      status: 'NOT_FOUND',
      message: `HUID "${normalizedHUID}" was not found in the official BIS hallmarking registry. Please verify the 6-character code or inspect the hallmark stamp with a 10x loupe.`,
    };
  }

  return {
    status: 'VALID_VERIFIED',
    record: foundRecord,
    message: `HUID "${normalizedHUID}" successfully verified against BIS hallmarking registry.`,
  };
}

/**
 * Compare declared customer attributes with official BIS CARE record
 */
export function compareDeclaredWithBIS(
  declared: {
    type: JewelleryType;
    karat: GoldKarat;
    grossWeightGrams?: number;
  },
  bisRecord: BISCareRecord
): {
  isMatch: boolean;
  discrepancies: DiscrepancyReport[];
} {
  const discrepancies: DiscrepancyReport[] = [];

  // 1. Article type comparison
  if (declared.type !== bisRecord.articleType) {
    discrepancies.push({
      code: 'ARTICLE_TYPE_MISMATCH',
      severity: 'CRITICAL',
      field: 'articleType',
      declaredValue: declared.type,
      measuredOrVerifiedValue: bisRecord.articleType,
      explanation: `Customer declared article as "${declared.type}", but BIS hallmarking record registers HUID ${bisRecord.huid} as a "${bisRecord.articleType}". Possible hallmark cloning or counterfeit stamp.`,
    });
  }

  // 2. Karat / Purity comparison
  if (declared.karat !== bisRecord.purityKarat) {
    const isDowngrade = bisRecord.purityFineness < (declared.karat === '22K' ? 916 : declared.karat === '24K' ? 999 : 750);
    discrepancies.push({
      code: isDowngrade ? 'PURITY_DOWNGRADE' : 'PURITY_UPGRADE',
      severity: 'CRITICAL',
      field: 'purityKarat',
      declaredValue: declared.karat,
      measuredOrVerifiedValue: bisRecord.purityKarat,
      explanation: `Customer declared ${declared.karat}, but official BIS hallmarking registers this item as ${bisRecord.purityKarat} (${bisRecord.purityFineness} fineness).`,
    });
  }

  // 3. Weight comparison (if recorded in BIS 2026 digital records)
  if (declared.grossWeightGrams && bisRecord.recordedWeightGrams) {
    const diff = Math.abs(declared.grossWeightGrams - bisRecord.recordedWeightGrams);
    const variancePercent = (diff / bisRecord.recordedWeightGrams) * 100;

    // Tolerance of 2% or 0.2g for normal wear & tear
    if (diff > 0.5 && variancePercent > 3) {
      discrepancies.push({
        code: 'WEIGHT_MISMATCH',
        severity: 'HIGH',
        field: 'grossWeight',
        declaredValue: `${declared.grossWeightGrams} g`,
        measuredOrVerifiedValue: `${bisRecord.recordedWeightGrams} g`,
        variancePercentage: parseFloat(variancePercent.toFixed(2)),
        explanation: `Declared gross weight (${declared.grossWeightGrams}g) differs by ${variancePercent.toFixed(1)}% from official BIS hallmarking recorded weight (${bisRecord.recordedWeightGrams}g).`,
      });
    }
  }

  return {
    isMatch: discrepancies.length === 0,
    discrepancies,
  };
}

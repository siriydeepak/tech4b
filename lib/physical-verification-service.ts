/**
 * AURUM — Physical Verification & Instrument Logger Service
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Handles weighing balance data, XRF spectrometer measurement processing,
 * Cadmium/toxic solder detection, and composite trust score computation.
 */

import { 
  PhysicalMeasurementInput, 
  DiscrepancyReport, 
  VerificationSessionResult, 
  HUIDVerificationStatus, 
  BISCareRecord 
} from '../types/verification';
import { GoldKarat, KARAT_TO_FINENESS_MAP } from '../types/jewellery';
import { EvidenceItem, PROVENANCE_METADATA } from '../types/evidence';

export interface WeighingValidationResult {
  isValid: boolean;
  computedNetWeightGrams: number;
  discrepancyError?: string;
}

/**
 * Validates precision weighing scale inputs: Gross, Stone, and Net Gold Weight.
 * Ensures arithmetic integrity and flags stone weight anomalies.
 */
export function validateWeighingMeasurements(
  grossWeightGrams: number,
  stoneWeightGrams: number,
  reportedNetWeightGrams: number
): WeighingValidationResult {
  if (grossWeightGrams <= 0) {
    return {
      isValid: false,
      computedNetWeightGrams: 0,
      discrepancyError: 'Gross weight must be greater than 0 grams.',
    };
  }

  if (stoneWeightGrams < 0) {
    return {
      isValid: false,
      computedNetWeightGrams: 0,
      discrepancyError: 'Stone / non-gold weight cannot be negative.',
    };
  }

  if (stoneWeightGrams >= grossWeightGrams) {
    return {
      isValid: false,
      computedNetWeightGrams: 0,
      discrepancyError: 'Stone weight cannot equal or exceed total gross weight.',
    };
  }

  const computedNet = parseFloat((grossWeightGrams - stoneWeightGrams).toFixed(3));
  const difference = Math.abs(computedNet - reportedNetWeightGrams);

  // Allow minor 0.005g float precision variance
  if (difference > 0.01) {
    return {
      isValid: false,
      computedNetWeightGrams: computedNet,
      discrepancyError: `Net weight calculation mismatch: Gross (${grossWeightGrams}g) - Stone (${stoneWeightGrams}g) = ${computedNet}g, but reported net weight was ${reportedNetWeightGrams}g.`,
    };
  }

  return {
    isValid: true,
    computedNetWeightGrams: computedNet,
  };
}

/**
 * Evaluates XRF Spectrometer readings against declared karat standards.
 * Flags purities below legal tolerances and checks for illegal Cadmium (Cd) solder.
 */
export function evaluateXRFMeasurement(
  xrfPurityPercent: number,
  declaredKarat: GoldKarat,
  elementalComposition?: { Au: number; Ag?: number; Cu?: number; Zn?: number; Cd?: number }
): {
  measuredFineness: number;
  expectedFineness: number;
  discrepancies: DiscrepancyReport[];
} {
  const measuredFineness = parseFloat((xrfPurityPercent * 10).toFixed(1));
  const expectedFineness = KARAT_TO_FINENESS_MAP[declaredKarat] || 916;
  const discrepancies: DiscrepancyReport[] = [];

  // Fineness difference
  const finenessDelta = measuredFineness - expectedFineness;

  // BIS Hallmarking tolerance in India allows a 0.2% (2 ppt) assay tolerance
  if (finenessDelta < -3) {
    const purityLossPercent = parseFloat((((expectedFineness - measuredFineness) / expectedFineness) * 100).toFixed(2));
    discrepancies.push({
      code: 'PURITY_DOWNGRADE',
      severity: finenessDelta < -20 ? 'CRITICAL' : 'HIGH',
      field: 'xrfPurity',
      declaredValue: `${declaredKarat} (${expectedFineness} fineness)`,
      measuredOrVerifiedValue: `${measuredFineness} fineness (${xrfPurityPercent}%)`,
      variancePercentage: purityLossPercent,
      explanation: `XRF analysis indicates pure gold content of ${measuredFineness} fineness, which is below the declared standard of ${declaredKarat} (${expectedFineness} fineness) by ${purityLossPercent}%.`,
    });
  }

  // Check for toxic Cadmium (Cd) soldering ban
  if (elementalComposition?.Cd && elementalComposition.Cd > 0.05) {
    discrepancies.push({
      code: 'TOXIC_SOLDER_DETECTED',
      severity: 'CRITICAL',
      field: 'elementalComposition.Cd',
      declaredValue: '0% Cadmium (Lead/Cd Free)',
      measuredOrVerifiedValue: `${elementalComposition.Cd}% Cd`,
      explanation: `XRF spectrometry detected ${elementalComposition.Cd}% Cadmium. Cadmium solders are banned under BIS IS 1417 due to health hazards and brittle melt qualities. Requires refining deduction.`,
    });
  }

  return {
    measuredFineness,
    expectedFineness,
    discrepancies,
  };
}

/**
 * Calculates a composite trust score (0 to 100) based on evidence provenance,
 * BIS verification status, and physical measurement consistency.
 */
export function calculateCompositeTrustScore(params: {
  huidStatus: HUIDVerificationStatus;
  discrepancies: DiscrepancyReport[];
  attachedEvidence: EvidenceItem[];
}): number {
  let score = 50; // Neutral baseline

  // 1. HUID Status modifier
  switch (params.huidStatus) {
    case 'VALID_VERIFIED':
      score += 25;
      break;
    case 'MISMATCH':
      score -= 35;
      break;
    case 'NOT_FOUND':
      score -= 20;
      break;
    case 'INVALID_FORMAT':
      score -= 15;
      break;
  }

  // 2. Evidence Provenance Quality
  let provenanceBonus = 0;
  for (const item of params.attachedEvidence) {
    const meta = PROVENANCE_METADATA[item.provenance];
    if (meta) {
      provenanceBonus += meta.trustScoreWeight * 6; // Max ~24 pts across 4 verified items
    }
  }
  score += Math.min(25, provenanceBonus);

  // 3. Penalty for Discrepancies
  for (const disc of params.discrepancies) {
    if (disc.severity === 'CRITICAL') score -= 30;
    else if (disc.severity === 'HIGH') score -= 15;
    else if (disc.severity === 'MEDIUM') score -= 8;
    else if (disc.severity === 'LOW') score -= 3;
  }

  // Clamp score between 0 and 100
  return Math.max(0, Math.min(100, Math.round(score)));
}

/**
 * Assembles a complete, auditable verification session result ready for valuation.
 */
export function createVerificationSession(params: {
  sessionId: string;
  jewelleryId: string;
  jewellerId: string;
  huidStatus: HUIDVerificationStatus;
  bisRecord?: BISCareRecord;
  physicalMeasurements: PhysicalMeasurementInput;
  attachedEvidence: EvidenceItem[];
  bisDiscrepancies: DiscrepancyReport[];
  xrfDiscrepancies: DiscrepancyReport[];
}): VerificationSessionResult {
  const allDiscrepancies = [...params.bisDiscrepancies, ...params.xrfDiscrepancies];

  const trustScore = calculateCompositeTrustScore({
    huidStatus: params.huidStatus,
    discrepancies: allDiscrepancies,
    attachedEvidence: params.attachedEvidence,
  });

  const hasCriticalDiscrepancy = allDiscrepancies.some((d) => d.severity === 'CRITICAL');
  const isApproved = !hasCriticalDiscrepancy && trustScore >= 40;

  return {
    sessionId: params.sessionId,
    jewelleryId: params.jewelleryId,
    huidStatus: params.huidStatus,
    bisDetails: params.bisRecord,
    physicalMeasurements: params.physicalMeasurements,
    attachedEvidence: params.attachedEvidence,
    discrepancies: allDiscrepancies,
    trustScore,
    isApprovedForValuation: isApproved,
    verifiedAt: new Date().toISOString(),
  };
}

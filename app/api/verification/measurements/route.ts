/**
 * API Route: /api/verification/measurements
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Ingests physical counter measurements:
 * - Scale weights (gross, stone, net) with arithmetic verification
 * - XRF Spectrometer readings with legal tolerance checks and Cadmium alerts
 * - Computes composite trust score
 */

import { validateWeighingMeasurements, evaluateXRFMeasurement, calculateCompositeTrustScore } from '../../../../lib/physical-verification-service';
import { GoldKarat } from '../../../../types/jewellery';
import { HUIDVerificationStatus } from '../../../../types/verification';
import { EvidenceItem } from '../../../../types/evidence';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      jewelleryId,
      jewellerId,
      grossWeightGrams,
      stoneWeightGrams,
      reportedNetWeightGrams,
      xrfPurityPercent,
      declaredKarat,
      elementalComposition,
      huidStatus = 'VALID_VERIFIED',
      attachedEvidence = [] as EvidenceItem[],
    } = body;

    // 1. Validate Weighing measurements
    const weightValidation = validateWeighingMeasurements(
      parseFloat(grossWeightGrams),
      parseFloat(stoneWeightGrams || 0),
      parseFloat(reportedNetWeightGrams)
    );

    if (!weightValidation.isValid) {
      return Response.json(
        {
          success: false,
          error: weightValidation.discrepancyError,
        },
        { status: 400 }
      );
    }

    // 2. Evaluate XRF Spectrometer purity
    const xrfEvaluation = evaluateXRFMeasurement(
      parseFloat(xrfPurityPercent),
      declaredKarat as GoldKarat,
      elementalComposition
    );

    // 3. Compute Composite Trust Score
    const trustScore = calculateCompositeTrustScore({
      huidStatus: huidStatus as HUIDVerificationStatus,
      discrepancies: xrfEvaluation.discrepancies,
      attachedEvidence,
    });

    return Response.json({
      success: true,
      measurements: {
        jewelleryId,
        jewellerId,
        grossWeightGrams: parseFloat(grossWeightGrams),
        stoneWeightGrams: parseFloat(stoneWeightGrams || 0),
        netGoldWeightGrams: weightValidation.computedNetWeightGrams,
        measuredFineness: xrfEvaluation.measuredFineness,
        xrfPurityPercent: parseFloat(xrfPurityPercent),
        elementalComposition,
      },
      discrepancies: xrfEvaluation.discrepancies,
      trustScore,
      isApprovedForValuation: !xrfEvaluation.discrepancies.some((d) => d.severity === 'CRITICAL') && trustScore >= 40,
    });
  } catch (error: any) {
    return Response.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

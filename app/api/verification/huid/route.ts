/**
 * API Route: /api/verification/huid
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Verifies 6-character BIS HUID against the hallmarking registry
 * and compares official registered specs with customer claims.
 */

import { validateHUIDFormat, queryBISHUID, compareDeclaredWithBIS } from '../../../../lib/bis-huid-service';
import { GoldKarat, JewelleryType } from '../../../../types/jewellery';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { huid, declaredType, declaredKarat, declaredGrossWeightGrams } = body;

    // 1. Validate format
    const formatCheck = validateHUIDFormat(huid);
    if (!formatCheck.isValid) {
      return Response.json(
        {
          success: false,
          error: formatCheck.error,
          status: 'INVALID_FORMAT',
        },
        { status: 400 }
      );
    }

    // 2. Query official registry
    const bisLookup = await queryBISHUID(formatCheck.normalizedHUID);

    if (bisLookup.status !== 'VALID_VERIFIED' || !bisLookup.record) {
      return Response.json({
        success: false,
        status: bisLookup.status,
        message: bisLookup.message,
      });
    }

    // 3. Optional customer claim comparison
    let comparison = { isMatch: true, discrepancies: [] as any[] };
    if (declaredType && declaredKarat) {
      comparison = compareDeclaredWithBIS(
        {
          type: declaredType as JewelleryType,
          karat: declaredKarat as GoldKarat,
          grossWeightGrams: declaredGrossWeightGrams ? parseFloat(declaredGrossWeightGrams) : undefined,
        },
        bisLookup.record
      );
    }

    return Response.json({
      success: true,
      status: comparison.isMatch ? 'VALID_VERIFIED' : 'MISMATCH',
      huid: formatCheck.normalizedHUID,
      bisRecord: bisLookup.record,
      discrepancies: comparison.discrepancies,
      isMatch: comparison.isMatch,
      message: comparison.isMatch 
        ? 'HUID verified and matches declared jewellery attributes.'
        : 'HUID verified, but detected attribute discrepancies.',
    });
  } catch (error: any) {
    return Response.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

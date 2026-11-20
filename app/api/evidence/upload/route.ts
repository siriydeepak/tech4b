/**
 * API Route: /api/evidence/upload
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Validates incoming evidence files, assigns provenance tiers,
 * and generates Supabase Storage upload metadata.
 */

import { validateUploadFile, generateStoragePath, buildEvidenceRecord } from '../../../../lib/storage-service';
import { EvidenceCategory, EvidenceProvenance } from '../../../../types/evidence';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      jewelleryId,
      transactionId,
      fileName,
      fileSizeBytes,
      mimeType,
      category,
      provenance,
      userId,
      userRole,
      sha256Hash = 'mock_sha256_hash_preview',
      notes,
    } = body;

    // 1. File validation
    const fileValidation = validateUploadFile({
      name: fileName,
      sizeBytes: parseInt(fileSizeBytes),
      mimeType,
    });

    if (!fileValidation.isValid) {
      return Response.json(
        { success: false, error: fileValidation.error },
        { status: 400 }
      );
    }

    // 2. Generate secure storage path in Supabase bucket
    const storagePath = generateStoragePath({
      jewelleryId,
      category: category as EvidenceCategory,
      fileName,
    });

    // 3. Construct evidence record
    const evidenceItem = buildEvidenceRecord({
      id: `ev_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      jewelleryId,
      transactionId,
      category: category as EvidenceCategory,
      provenance: provenance as EvidenceProvenance,
      fileUrl: `https://your-supabase-project.supabase.co/storage/v1/object/public/aurum-evidence/${storagePath}`,
      fileName,
      mimeType,
      fileSizeBytes: parseInt(fileSizeBytes),
      sha256Hash,
      uploadedBy: {
        userId: userId || 'anonymous',
        role: userRole || 'JEWELLER',
      },
      notes,
    });

    return Response.json({
      success: true,
      storagePath,
      evidenceItem,
      message: 'File upload metadata validated. Ready for Supabase Storage push.',
    });
  } catch (error: any) {
    return Response.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

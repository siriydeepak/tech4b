/**
 * AURUM — Supabase Storage & Evidence Upload Helper
 * Member 2: Verification, Evidence Pipeline & Data Management
 * 
 * Handles file validation, SHA-256 integrity hashing, Supabase Storage bucket pathing,
 * and provenance tagging.
 */

import { EvidenceCategory, EvidenceItem, EvidenceProvenance } from '../types/evidence';

export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
] as const;

export type AllowedMimeType = typeof ALLOWED_MIME_TYPES[number];

/**
 * Validates file upload parameters before pushing to Supabase Storage
 */
export function validateUploadFile(file: {
  name: string;
  sizeBytes: number;
  mimeType: string;
}): { isValid: boolean; error?: string } {
  if (file.sizeBytes <= 0) {
    return { isValid: false, error: 'File is empty.' };
  }

  if (file.sizeBytes > MAX_FILE_SIZE_BYTES) {
    return {
      isValid: false,
      error: `File size (${(file.sizeBytes / (1024 * 1024)).toFixed(1)}MB) exceeds maximum allowed size of 10MB.`,
    };
  }

  if (!ALLOWED_MIME_TYPES.includes(file.mimeType as AllowedMimeType)) {
    return {
      isValid: false,
      error: `Unsupported file format "${file.mimeType}". Allowed formats: JPEG, PNG, WEBP, and PDF.`,
    };
  }

  return { isValid: true };
}

/**
 * Derives the strict storage bucket path in Supabase Storage
 * Structure:
 *   aurum-evidence/jewellery/<jewelleryId>/<category>/<timestamp>-<filename>
 */
export function generateStoragePath(params: {
  jewelleryId: string;
  category: EvidenceCategory;
  fileName: string;
}): string {
  const sanitizedFileName = params.fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
  const timestamp = Date.now();
  return `jewellery/${params.jewelleryId}/${params.category.toLowerCase()}/${timestamp}_${sanitizedFileName}`;
}

/**
 * Creates a verified EvidenceItem record ready to be inserted into the Supabase `evidence` table.
 */
export function buildEvidenceRecord(params: {
  id: string;
  jewelleryId: string;
  transactionId?: string;
  category: EvidenceCategory;
  provenance: EvidenceProvenance;
  fileUrl: string;
  fileName: string;
  mimeType: AllowedMimeType;
  fileSizeBytes: number;
  sha256Hash: string;
  uploadedBy: {
    userId: string;
    role: 'CUSTOMER' | 'JEWELLER' | 'ADMIN';
  };
  notes?: string;
}): EvidenceItem {
  return {
    id: params.id,
    jewelleryId: params.jewelleryId,
    transactionId: params.transactionId,
    category: params.category,
    provenance: params.provenance,
    fileUrl: params.fileUrl,
    fileName: params.fileName,
    mimeType: params.mimeType,
    fileSizeBytes: params.fileSizeBytes,
    sha256Hash: params.sha256Hash,
    uploadedBy: params.uploadedBy,
    recordedAt: new Date().toISOString(),
    notes: params.notes,
  };
}

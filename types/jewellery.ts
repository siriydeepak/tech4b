/**
 * AURUM — Jewellery Asset Types
 * Member 2: Verification, Evidence Pipeline & Data Management
 */

export type JewelleryType =
  | 'CHAIN'
  | 'NECKLACE'
  | 'BANGLE'
  | 'RING'
  | 'EARRINGS'
  | 'BRACELET'
  | 'PENDANT'
  | 'GOLD_COIN'
  | 'GOLD_BAR'
  | 'OTHER';

export type GoldKarat = '24K' | '22K' | '20K' | '18K' | '14K' | '10K' | '9K';

export interface JewelleryAsset {
  id: string;
  ownerId: string;
  type: JewelleryType;
  description: string;
  declaredKarat: GoldKarat;
  declaredFineness: number; // e.g. 916 for 22K, 750 for 18K, 999 for 24K
  declaredGrossWeightGrams: number;
  declaredStoneWeightGrams?: number;
  declaredHUID?: string; // 6-character alphanumeric code
  photoUrls: string[];
  purchaseDate?: string;
  originalJewellerName?: string;
  status: 'REGISTERED' | 'IN_VERIFICATION' | 'VERIFIED' | 'EXCHANGED' | 'REJECTED';
  createdAt: string;
  updatedAt: string;
}

export interface CreateJewelleryInput {
  ownerId: string;
  type: JewelleryType;
  description?: string;
  declaredKarat: GoldKarat;
  declaredGrossWeightGrams: number;
  declaredStoneWeightGrams?: number;
  declaredHUID?: string;
  photoUrls?: string[];
  purchaseDate?: string;
  originalJewellerName?: string;
}

export const KARAT_TO_FINENESS_MAP: Record<GoldKarat, number> = {
  '24K': 999,
  '22K': 916,
  '20K': 833,
  '18K': 750,
  '14K': 585,
  '10K': 417,
  '9K': 375,
};

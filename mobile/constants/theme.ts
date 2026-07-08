import { Colors } from './colors';

/**
 * Neon glow i mekane sjene — potpisni element dizajna.
 * Koristi se kroz `style={glow}` na ključnim CTA-ovima, aktivnom tabu i
 * hero elementima. Ostalo ostaje mirno.
 */
export const glow = {
  shadowColor: Colors.neon,
  shadowOpacity: 0.55,
  shadowRadius: 18,
  shadowOffset: { width: 0, height: 0 },
  elevation: 12,
} as const;

export const glowSoft = {
  shadowColor: Colors.neon,
  shadowOpacity: 0.3,
  shadowRadius: 12,
  shadowOffset: { width: 0, height: 4 },
  elevation: 7,
} as const;

export const cardShadow = {
  shadowColor: '#000000',
  shadowOpacity: 0.45,
  shadowRadius: 16,
  shadowOffset: { width: 0, height: 10 },
  elevation: 6,
} as const;

/** Standardni tamni gradijent preko slika (scrim ispod teksta). */
export const scrim = ['transparent', 'rgba(5,0,8,0.55)', 'rgba(5,0,8,0.96)'] as const;

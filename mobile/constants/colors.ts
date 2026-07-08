/**
 * Paleta — crna baza + neon ljubičasti akcent (UNVRS / Hi Ibiza dojam).
 * Stari nazivi (bgDark, bgCard, accent*, textLight, textMuted) zadržani kao
 * aliasi da postojeće reference ostanu ispravne; nove vrijednosti daju čišći,
 * tamniji izgled s neonom kao jedinim električnim akcentom.
 */
export const Colors = {
  // Nova semantika
  ink: '#050008',        // baza — gotovo crna
  inkSoft: '#0B0014',    // header / suptilno uzdignuta ploha
  surface: '#14011F',    // kartice
  surfaceHi: '#1E0733',  // uzdignute plohe / press stanje
  line: '#2A0F3D',       // suptilni rub kad je nužan
  neon: '#CE00FF',       // električni akcent (glow)
  neonDim: '#7A0AA0',    // prigušeni neon
  white: '#FFFFFF',
  text: '#F3ECFF',       // primarni tekst (gotovo bijeli)
  muted: '#9385AB',      // sekundarni tekst

  // Legacy aliasi
  bgDark: '#050008',
  bgCard: '#14011F',
  accent1: '#CE00FF',
  accent2: '#8B00CC',
  accent3: '#2A0F3D',
  textLight: '#F3ECFF',
  textMuted: '#9385AB',

  success: '#34C759',
  warning: '#F4B860',
  error: '#FF453A',
} as const;

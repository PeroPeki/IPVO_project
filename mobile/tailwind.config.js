/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      // Crna baza + neon ljubičasti akcent
      colors: {
        ink: '#050008',
        inkSoft: '#0B0014',
        surface: '#14011F',
        surfaceHi: '#1E0733',
        line: '#2A0F3D',
        neon: '#CE00FF',
        neonDim: '#7A0AA0',
        text: '#F3ECFF',
        muted: '#9385AB',
        // legacy aliasi
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
      },
      // Syne (display) + Inter (body). Nazivi ne kolidiraju s tailwind
      // weight/family utilitima pa je mapiranje na RN fontFamily jednoznačno.
      fontFamily: {
        display: ['Syne_800ExtraBold'],
        heading: ['Syne_700Bold'],
        sub: ['Syne_600SemiBold'],
        body: ['Inter_400Regular'],
        bodyMd: ['Inter_500Medium'],
        bodySb: ['Inter_600SemiBold'],
        bodyBd: ['Inter_700Bold'],
      },
    },
  },
  plugins: [],
};

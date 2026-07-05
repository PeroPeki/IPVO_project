/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      // Službena paleta — tamna tema, bez light modea
      colors: {
        bgDark: '#0A0010',
        bgCard: '#1A0030',
        accent1: '#CC00FF',
        accent2: '#8B00CC',
        accent3: '#4A0080',
        textLight: '#F0E6FF',
        textMuted: '#9B7BC0',
        success: '#34C759',
        warning: '#F4B860',
        error: '#FF3B30',
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#FAF7F0',
          100: '#F4ECE0',
          200: '#E7D7BE',
          300: '#D9C099',
          400: '#CFA96F',
          500: '#C5A059', // Primary Antique Architectural Bronze/Gold
          600: '#B08940',
          700: '#8E6B2C',
          800: '#6D5020',
          900: '#4A3515',
          950: '#261B0A',
        },
        parchment: {
          base: '#E3DACA', // Exact image background
          card: '#EDE6DB', // Card surface
          panel: '#EAE2D5', // Panel surface
          border: '#C5A059', // Border tone
          dark: '#D8CDBA',
          deep: '#C9BEAA',
        },
        obsidian: {
          950: '#0E0C0A', // Deepest charcoal
          900: '#141210', // Field / Input surface
          850: '#1A1714',
          800: '#26221D',
          700: '#3A342D',
          600: '#524B41',
          500: '#736A5E',
          400: '#9C9183',
          300: '#C4B9AC',
          200: '#E3DDD5',
          100: '#F4EFEB',
        },
      },
      fontFamily: {
        serif: ['Cinzel', 'Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

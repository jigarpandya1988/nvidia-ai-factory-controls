/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        nvidia: { DEFAULT: '#76b900', dark: '#5a8f00', light: '#8fd400' },
        surface: { 1: '#0a0a0f', 2: '#12121a', 3: '#1a1a24', 4: '#22222e' },
      },
    },
  },
  plugins: [],
};

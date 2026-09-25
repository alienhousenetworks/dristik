/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#efe8dc',
          50: '#fbf7f0',
          100: '#f7f1e6',
          200: '#efe8dc',
          300: '#e4d9c8',
        },
        ink: {
          DEFAULT: '#1c1915',
          700: '#3d3832',
          500: '#6b6459',
          400: '#8a8278',
          300: '#b7aea3',
        },
        line: 'rgba(28, 25, 21, 0.10)',
        pine: {
          DEFAULT: '#1f3d36',
          700: '#16312c',
          100: '#e4ece9',
        },
        good: '#2f6b4f',
        warn: '#9a6b24',
        bad: '#9a3b32',
      },
      fontFamily: {
        serif: ['Instrument Serif', 'Georgia', 'serif'],
        sans: ['Source Sans 3', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};

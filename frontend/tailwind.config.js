/** @type {import('tailwindcss').Config} */
const channel = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: channel('paper'),
          50: channel('paper-50'),
          100: channel('paper-100'),
          200: channel('paper-200'),
          300: channel('paper-300'),
        },
        ink: {
          DEFAULT: channel('ink'),
          50: channel('ink-50'),
          100: channel('ink-100'),
          200: channel('ink-200'),
          300: channel('ink-300'),
          400: channel('ink-400'),
          500: channel('ink-500'),
          600: channel('ink-600'),
          700: channel('ink-700'),
          800: channel('ink-800'),
          900: channel('ink-900'),
          950: channel('ink-950'),
        },
        line: channel('line'),
        pine: {
          DEFAULT: channel('pine'),
          700: channel('pine-700'),
          100: channel('pine-100'),
        },
        good: channel('good'),
        warn: channel('warn'),
        bad: channel('bad'),
      },
      fontFamily: {
        serif: ['Instrument Serif', 'Georgia', 'serif'],
        sans: ['Source Sans 3', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        display: ['2.5rem', { lineHeight: '1.1', letterSpacing: '-0.03em' }],
        heading: ['1.5rem', { lineHeight: '1.25', letterSpacing: '-0.02em' }],
        body: ['0.9375rem', { lineHeight: '1.55' }],
        caption: ['0.75rem', { lineHeight: '1.4' }],
        label: ['0.6875rem', { lineHeight: '1.2', letterSpacing: '0.12em' }],
      },
      boxShadow: {
        '2xs': '0 1px 1px rgb(var(--shadow-color) / 0.04)',
        xs: '0 1px 2px rgb(var(--shadow-color) / 0.06)',
        sm: '0 1px 2px rgb(var(--shadow-color) / 0.06), 0 1px 3px rgb(var(--shadow-color) / 0.08)',
        md: '0 8px 24px rgb(var(--shadow-color) / 0.08)',
        lg: '0 16px 40px rgb(var(--shadow-color) / 0.14)',
        overlay: '0 24px 64px rgb(var(--shadow-color) / 0.22)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      zIndex: {
        sticky: '30',
        dropdown: '40',
        overlay: '50',
        modal: '60',
        toast: '70',
        command: '80',
      },
      transitionDuration: {
        DEFAULT: '160ms',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateX(8px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.22s cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        slideIn: 'slideIn 0.2s cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
      },
      maxWidth: {
        page: '1360px',
      },
    },
  },
  plugins: [],
};

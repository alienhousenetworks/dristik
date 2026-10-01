/** Runtime mirror of src/styles/tokens.css for components that cannot use Tailwind. */

export const zIndex = {
  sticky: 30,
  dropdown: 40,
  overlay: 50,
  modal: 60,
  toast: 70,
  command: 80,
} as const;

export const duration = {
  fast: 120,
  base: 160,
  slow: 240,
} as const;

export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export const themeStorageKey = 'dristik_theme';

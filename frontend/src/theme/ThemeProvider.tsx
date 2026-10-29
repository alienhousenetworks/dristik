import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { themeStorageKey } from '../design/tokens';

export type ThemeChoice = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  choice: ThemeChoice;
  dark: boolean;
  setChoice: (choice: ThemeChoice) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function apply(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => {
    const stored = localStorage.getItem(themeStorageKey);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
    return 'system';
  });
  const [system, setSystem] = useState(systemDark);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystem(media.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  const dark = choice === 'dark' || (choice === 'system' && system);

  useEffect(() => {
    apply(dark);
  }, [dark]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      choice,
      dark,
      setChoice: (next) => {
        localStorage.setItem(themeStorageKey, next);
        setChoiceState(next);
      },
      toggle: () => {
        const next = dark ? 'light' : 'dark';
        localStorage.setItem(themeStorageKey, next);
        setChoiceState(next);
      },
    }),
    [choice, dark],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "cris-sme-theme";

function readInitialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Theme is applied by toggling a `dark` class on <html>; every component
 * already reads colors through the semantic CSS tokens in index.css, so
 * nothing else needs to know which theme is active. A matching inline
 * script in index.html applies the class before React mounts, so there's
 * no flash of the wrong theme on load.
 */
export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const [theme, setTheme] = useState<Theme>(() => readInitialTheme());

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  return { theme, toggleTheme };
}

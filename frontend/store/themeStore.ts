import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "dark" | "light";

interface ThemeState {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme: ThemeMode) => {
        if (typeof document !== "undefined") {
          const root = document.documentElement;
          if (theme === "dark") {
            root.classList.add("dark");
            root.classList.remove("light");
          } else {
            root.classList.add("light");
            root.classList.remove("dark");
          }
        }
        set({ theme });
      },
      toggleTheme: () => {
        const nextTheme = get().theme === "dark" ? "light" : "dark";
        get().setTheme(nextTheme);
      },
    }),
    {
      name: "orbit-theme",
      onRehydrateStorage: () => (state) => {
        if (typeof document !== "undefined" && state?.theme) {
          const root = document.documentElement;
          if (state.theme === "dark") {
            root.classList.add("dark");
            root.classList.remove("light");
          } else {
            root.classList.add("light");
            root.classList.remove("dark");
          }
        }
      },
    }
  )
);

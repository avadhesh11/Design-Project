import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/types";
import api from "@/lib/api";

interface AuthState {
  user: User | null;

  setUser: (user: User) => void;

  logout: () => void;

  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,

      setUser: (user) => {
        set({ user });
      },


      logout: async () => {
        try {
          await api.post("/auth/logout");
        } catch (err) {
          console.log(err);
        }
        // Clear all persisted stores
        localStorage.removeItem("orbit-workspace");
        localStorage.removeItem("orbit-auth");

        // Reset Zustand in-memory state
        const { useWorkspaceStore } = await import("@/store/workspaceStore");
        useWorkspaceStore.getState().clearWorkspace();

        set({ user: null });
      },

      isAuthenticated: () => !!get().user,
    }),

    {
      name: "orbit-auth",

      partialize: (state) => ({
        user: state.user,
      }),
    }
  )
);
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  email: string | null;
  isOnboarded: boolean;
  setToken: (token: string, email?: string, isOnboarded?: boolean) => void;
  setEmail: (email: string) => void;
  setOnboarded: (isOnboarded: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      isOnboarded: false,
      setToken: (token, email, isOnboarded) =>
        set({ token, email: email ?? null, isOnboarded: isOnboarded ?? false }),
      setEmail: (email) => set({ email }),
      setOnboarded: (isOnboarded) => set({ isOnboarded }),
      logout: () => set({ token: null, email: null, isOnboarded: false }),
    }),
    { name: "phd-copilot-auth" }
  )
);

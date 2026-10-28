"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api, getStoredToken, setStoredToken, setUnauthorizedHandler } from "@/lib/api";
import { User } from "@/types/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (data: { email: string; password: string }) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    display_name: string;
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const logout = useCallback(() => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  // Register the 401 callback
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null);
      setUser(null);
      router.push("/login");
    });
  }, [router]);

  const refreshUser = useCallback(async () => {
    const existingToken = getStoredToken();
    if (!existingToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.getCurrentUser();
      setUser(profile);
      setToken(existingToken);
    } catch {
      setStoredToken(null);
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize session on mount
  useEffect(() => {
    let isCurrent = true;
    const existingToken = getStoredToken();

    if (!existingToken) {
      // Defer to microtask to satisfy React 19 effect rules
      Promise.resolve().then(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });
      return () => {
        isCurrent = false;
      };
    }

    api
      .getCurrentUser()
      .then((profile) => {
        if (isCurrent) {
          setUser(profile);
          setToken(existingToken);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setStoredToken(null);
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const login = async (credentials: { email: string; password: string }) => {
    const res = await api.login(credentials);
    setStoredToken(res.access_token);
    setToken(res.access_token);
    const profile = await api.getCurrentUser();
    setUser(profile);
    router.push("/dashboard");
  };

  const register = async (data: {
    email: string;
    password: string;
    display_name: string;
  }) => {
    await api.register(data);
    await login({ email: data.email, password: data.password });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

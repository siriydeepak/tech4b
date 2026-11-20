import React, { createContext, useContext, useState, useEffect } from "react";
import type { User, Token } from "../types";
import api from "../lib/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

interface RegisterData {
  email: string;
  full_name: string;
  password: string;
  role: "customer" | "jeweller";
  phone?: string;
  business_name?: string;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("aurum_user");
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("aurum_token")
  );
  const [isLoading, setIsLoading] = useState(false);

  const saveSession = (data: Token) => {
    localStorage.setItem("aurum_token", data.access_token);
    localStorage.setItem("aurum_user", JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.post<Token>("/api/auth/login", { email, password });
      saveSession(res.data);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      const res = await api.post<Token>("/api/auth/register", data);
      saveSession(res.data);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("aurum_token");
    localStorage.removeItem("aurum_user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}


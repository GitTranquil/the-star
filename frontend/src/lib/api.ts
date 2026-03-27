import { createClient } from "@/utils/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return { "Content-Type": "application/json" };
  }

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  };
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || `API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  createReading: (mode: string = "intuitive") =>
    apiRequest<{ reading_id: string; message: string }>("/api/reading", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  sendMessage: (readingId: string, message: string) =>
    apiRequest(`/api/reading/${readingId}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  completeReading: (readingId: string) =>
    apiRequest(`/api/reading/${readingId}/complete`, {
      method: "POST",
    }),

  getReading: (readingId: string) =>
    apiRequest(`/api/reading/${readingId}`),

  listReadings: (limit = 20, offset = 0) =>
    apiRequest<Array<Record<string, unknown>>>(
      `/api/readings?limit=${limit}&offset=${offset}`
    ),

  getProfile: () => apiRequest("/api/profile"),

  updateProfile: (data: Record<string, unknown>) =>
    apiRequest("/api/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

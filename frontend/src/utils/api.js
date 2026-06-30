import { getToken, getRefreshToken, setAuth, logout } from "./auth";

export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";

let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
  });

  if (!res.ok) {
    return null;
  }

  const data = await res.json();
  setAuth(data);
  return data.token;
}

export const authFetch = async (url, options = {}, retried = false) => {
  const token = getToken();

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (response.status === 401 && !retried) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }

    const newToken = await refreshPromise;
    if (newToken) {
      return authFetch(url, options, true);
    }

    logout();
  }

  return response;
};

export async function uploadDocument(chatId, file) {
  const formData = new FormData();
  formData.append("chatId", chatId);
  formData.append("pdf", file);
  return authFetch("/upload", {
    method: "POST",
    body: formData,
  });
}

export async function fetchExecutiveSummary(chatId) {
  const res = await authFetch(`/insights/${chatId}/summary`);
  return res.json();
}

export async function generateExecutiveSummary(chatId, { regenerate = false } = {}) {
  const query = regenerate ? "?regenerate=true" : "";
  const res = await authFetch(`/insights/${chatId}/summary${query}`, {
    method: "POST",
  });
  return res.json();
}

export async function fetchRiskAnalysis(chatId) {
  const res = await authFetch(`/insights/${chatId}/risks`);
  return res.json();
}

export async function generateRiskAnalysis(chatId, { regenerate = false } = {}) {
  const query = regenerate ? "?regenerate=true" : "";
  const res = await authFetch(`/insights/${chatId}/risks${query}`, {
    method: "POST",
  });
  return res.json();
}


import type { ApiError } from "@/lib/types/api";
import { toast } from "@/lib/hooks/use-toast";

export interface ApiClientConfig {
  baseUrl: string;
  credentials: "include" | "same-origin";
}

/**
 * Reads the CSRF token from the browser's cookies.
 * Django sets the `csrftoken` cookie on responses.
 */
function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Type-safe HTTP client wrapping all backend API calls.
 *
 * Responsibilities:
 * - Prepend base URL to all requests
 * - Include credentials (cookies) for session-based auth
 * - Attach CSRF token to mutating requests (POST, PUT, DELETE)
 * - Parse JSON responses with type assertions
 * - Throw typed ApiError on non-2xx responses
 * - Handle 401 by redirecting to login (window.location)
 */
export class ApiClient {
  private baseUrl: string;
  private credentials: RequestCredentials;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl;
    this.credentials = config.credentials;
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = this.buildUrl(path, params);
    return this.request<T>(url, { method: "GET" });
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    return this.request<T>(url, {
      method: "POST",
      headers: this.mutationHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  async postForm<T>(path: string, body: FormData): Promise<T> {
    const url = this.buildUrl(path);
    return this.request<T>(url, {
      method: "POST",
      headers: this.csrfHeaders(),
      body,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    return this.request<T>(url, {
      method: "PUT",
      headers: this.mutationHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    const url = this.buildUrl(path);
    return this.request<T>(url, {
      method: "DELETE",
      headers: this.mutationHeaders(),
    });
  }

  /**
   * Returns headers for mutating requests (POST/PUT/DELETE).
   * Includes Content-Type and the CSRF token.
   */
  private mutationHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    return { ...headers, ...this.csrfHeaders() };
  }

  private csrfHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
    return headers;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    let url: string;
    if (this.baseUrl) {
      url = new URL(path, this.baseUrl).toString();
    } else {
      url = path;
    }
    if (params && Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams(params);
      url += (url.includes("?") ? "&" : "?") + searchParams.toString();
    }
    return url;
  }

  private async request<T>(url: string, init: RequestInit): Promise<T> {
    const response = await fetch(url, {
      ...init,
      credentials: this.credentials,
    });

    if (!response.ok) {
      const error = await this.parseError(response);

      // Handle 401 by showing session expiry toast then redirecting to login
      if (error.status === 401 && typeof window !== "undefined") {
        toast({
          title: "Session expired",
          description: "Your session has expired. Redirecting to login...",
          variant: "destructive",
        });
        setTimeout(() => {
          window.location.href = "/login";
        }, 2000);
      }

      throw error;
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  private async parseError(response: Response): Promise<ApiError> {
    try {
      const body = await response.json();
      return {
        status: response.status,
        message: body.message || body.error || body.detail || response.statusText,
        detail: body.detail,
        code: body.code,
      };
    } catch {
      // Response body is not valid JSON
      return {
        status: response.status,
        message: response.statusText || "Something went wrong",
      };
    }
  }
}

/**
 * Default API client instance configured for the Django backend.
 * Uses Next.js rewrites to proxy /api/* requests to the backend,
 * so all requests are same-origin (no CORS issues, cookies work naturally).
 */
export const apiClient = new ApiClient({
  baseUrl: "",
  credentials: "same-origin",
});

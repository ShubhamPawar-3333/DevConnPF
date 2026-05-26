import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "./client";
import type { ApiError } from "@/lib/types/api";

describe("ApiClient", () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient({
      baseUrl: "http://localhost:8000",
      credentials: "include",
    });
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetch(response: Partial<Response>) {
    const mockResponse = {
      ok: true,
      status: 200,
      statusText: "OK",
      json: vi.fn().mockResolvedValue({}),
      ...response,
    };
    vi.mocked(fetch).mockResolvedValue(mockResponse as unknown as Response);
    return mockResponse;
  }

  describe("get", () => {
    it("sends GET request with correct URL", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({ id: 1 }) });

      const result = await client.get<{ id: number }>("/api/repos/1/");

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/repos/1/",
        expect.objectContaining({ method: "GET", credentials: "include" })
      );
      expect(result).toEqual({ id: 1 });
    });

    it("appends query params to URL", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue([]) });

      await client.get("/api/search/", { q: "hello", page: "1" });

      const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string;
      expect(calledUrl).toContain("q=hello");
      expect(calledUrl).toContain("page=1");
    });
  });

  describe("post", () => {
    it("sends POST request with JSON body", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({ id: 2 }) });

      const result = await client.post<{ id: number }>("/api/repos/", {
        url: "https://github.com/user/repo",
      });

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/repos/",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "https://github.com/user/repo" }),
        })
      );
      expect(result).toEqual({ id: 2 });
    });

    it("sends POST without body when body is undefined", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({}) });

      await client.post("/api/logout/");

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/logout/",
        expect.objectContaining({
          method: "POST",
          body: undefined,
        })
      );
    });
  });

  describe("postForm", () => {
    it("sends FormData without forcing a JSON content type", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({ id: 3 }) });
      const formData = new FormData();
      formData.append("zip_file", new Blob(["zip"]), "repo.zip");

      const result = await client.postForm<{ id: number }>("/api/repos/", formData);

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/repos/",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: {},
          body: formData,
        })
      );
      expect(result).toEqual({ id: 3 });
    });
  });

  describe("put", () => {
    it("sends PUT request with JSON body", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({ updated: true }) });

      await client.put("/api/settings/", { language: "es" });

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/settings/",
        expect.objectContaining({
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language: "es" }),
        })
      );
    });
  });

  describe("delete", () => {
    it("sends DELETE request", async () => {
      mockFetch({ ok: true, json: vi.fn().mockResolvedValue({}) });

      await client.delete("/api/repos/1/");

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/repos/1/",
        expect.objectContaining({ method: "DELETE", credentials: "include" })
      );
    });
  });

  describe("error handling", () => {
    it("throws ApiError on non-2xx response with JSON body", async () => {
      mockFetch({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        json: vi.fn().mockResolvedValue({
          message: "Invalid input",
          detail: "Field 'url' is required",
          code: "VALIDATION_ERROR",
        }),
      });

      await expect(client.get("/api/repos/")).rejects.toMatchObject({
        status: 400,
        message: "Invalid input",
        detail: "Field 'url' is required",
        code: "VALIDATION_ERROR",
      } satisfies ApiError);
    });

    it("throws ApiError with statusText when body is not JSON", async () => {
      mockFetch({
        ok: false,
        status: 502,
        statusText: "Bad Gateway",
        json: vi.fn().mockRejectedValue(new Error("not json")),
      });

      await expect(client.get("/api/repos/")).rejects.toMatchObject({
        status: 502,
        message: "Bad Gateway",
      } satisfies ApiError);
    });

    it("redirects to /login on 401 response after showing toast", async () => {
      vi.useFakeTimers();

      const locationDescriptor = Object.getOwnPropertyDescriptor(window, "location");
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      mockFetch({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: vi.fn().mockResolvedValue({ message: "Session expired" }),
      });

      await expect(client.get("/api/me/")).rejects.toMatchObject({
        status: 401,
      });

      // Redirect is delayed to allow the toast to be visible
      expect(mockLocation.href).toBe("");

      // Advance timers to trigger the redirect
      vi.advanceTimersByTime(2000);
      expect(mockLocation.href).toBe("/login");

      // Restore
      if (locationDescriptor) {
        Object.defineProperty(window, "location", locationDescriptor);
      }

      vi.useRealTimers();
    });

    it("handles 204 No Content responses", async () => {
      mockFetch({ ok: true, status: 204 });

      const result = await client.delete("/api/repos/1/");

      expect(result).toBeUndefined();
    });
  });
});

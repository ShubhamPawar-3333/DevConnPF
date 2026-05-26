import { describe, it, expect } from "vitest";
import { handleApiError, type ErrorAction } from "./error-handler";
import type { ApiError } from "@/lib/types/api";

describe("handleApiError", () => {
  it("returns redirect to /login for 401", () => {
    const error: ApiError = { status: 401, message: "Unauthorized" };
    const action = handleApiError(error);
    expect(action).toEqual({ type: "redirect", target: "/login" });
  });

  it("returns permission toast for 403", () => {
    const error: ApiError = { status: 403, message: "Forbidden" };
    const action = handleApiError(error);
    expect(action).toEqual({
      type: "toast",
      message: "You don't have permission for this action",
    });
  });

  it("returns not-found for 404", () => {
    const error: ApiError = { status: 404, message: "Not Found" };
    const action = handleApiError(error);
    expect(action).toEqual({ type: "not-found" });
  });

  it("returns rate limit toast for 429", () => {
    const error: ApiError = { status: 429, message: "Too Many Requests" };
    const action = handleApiError(error);
    expect(action).toEqual({
      type: "toast",
      message: "Too many requests. Please wait a moment.",
    });
  });

  it("returns toast with error message for 500", () => {
    const error: ApiError = { status: 500, message: "Internal Server Error" };
    const action = handleApiError(error);
    expect(action).toEqual({
      type: "toast",
      message: "Internal Server Error",
    });
  });

  it("returns fallback message when error message is empty", () => {
    const error: ApiError = { status: 502, message: "" };
    const action = handleApiError(error);
    expect(action).toEqual({
      type: "toast",
      message: "Something went wrong",
    });
  });

  it("returns toast with custom message for other status codes", () => {
    const error: ApiError = { status: 422, message: "Validation failed" };
    const action = handleApiError(error);
    expect(action).toEqual({
      type: "toast",
      message: "Validation failed",
    });
  });
});

import { describe, it, expect } from "vitest";
import { validateSearchQuery } from "./validation";

describe("validateSearchQuery", () => {
  it("returns too_short for empty string", () => {
    const result = validateSearchQuery("");
    expect(result).toEqual({ valid: false, reason: "too_short" });
  });

  it("returns too_short for 1 character", () => {
    const result = validateSearchQuery("a");
    expect(result).toEqual({ valid: false, reason: "too_short" });
  });

  it("returns too_short for 2 characters", () => {
    const result = validateSearchQuery("ab");
    expect(result).toEqual({ valid: false, reason: "too_short" });
  });

  it("returns valid for exactly 3 characters (minimum boundary)", () => {
    const result = validateSearchQuery("abc");
    expect(result).toEqual({ valid: true });
  });

  it("returns valid for a typical search query", () => {
    const result = validateSearchQuery("where is auth handled");
    expect(result).toEqual({ valid: true });
  });

  it("returns valid for exactly 300 characters (maximum boundary)", () => {
    const query = "a".repeat(300);
    const result = validateSearchQuery(query);
    expect(result).toEqual({ valid: true });
  });

  it("returns too_long for 301 characters", () => {
    const query = "a".repeat(301);
    const result = validateSearchQuery(query);
    expect(result).toEqual({ valid: false, reason: "too_long" });
  });

  it("returns too_long for a very long string", () => {
    const query = "a".repeat(1000);
    const result = validateSearchQuery(query);
    expect(result).toEqual({ valid: false, reason: "too_long" });
  });

  it("counts whitespace characters toward length", () => {
    const result = validateSearchQuery("   ");
    expect(result).toEqual({ valid: true });
  });

  it("handles unicode characters", () => {
    const result = validateSearchQuery("検索クエリ");
    expect(result).toEqual({ valid: true });
  });
});

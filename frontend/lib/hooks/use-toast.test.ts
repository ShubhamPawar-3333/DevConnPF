import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { reducer } from "./use-toast";

describe("use-toast reducer", () => {
  it("adds a toast to the state", () => {
    const state = { toasts: [] };
    const result = reducer(state, {
      type: "ADD_TOAST",
      toast: { id: "1", title: "Hello", open: true },
    });
    expect(result.toasts).toHaveLength(1);
    expect(result.toasts[0].title).toBe("Hello");
  });

  it("limits toasts to max 3 simultaneous", () => {
    const state = {
      toasts: [
        { id: "1", title: "First", open: true },
        { id: "2", title: "Second", open: true },
        { id: "3", title: "Third", open: true },
      ],
    };
    const result = reducer(state, {
      type: "ADD_TOAST",
      toast: { id: "4", title: "Fourth", open: true },
    });
    expect(result.toasts).toHaveLength(3);
    // Newest toast is first
    expect(result.toasts[0].title).toBe("Fourth");
    // Oldest toast is dropped
    expect(result.toasts.find((t) => t.title === "Third")).toBeUndefined();
  });

  it("updates an existing toast", () => {
    const state = {
      toasts: [{ id: "1", title: "Original", open: true }],
    };
    const result = reducer(state, {
      type: "UPDATE_TOAST",
      toast: { id: "1", title: "Updated" },
    });
    expect(result.toasts[0].title).toBe("Updated");
  });

  it("dismisses a specific toast by id", () => {
    const state = {
      toasts: [
        { id: "1", title: "First", open: true },
        { id: "2", title: "Second", open: true },
      ],
    };
    const result = reducer(state, {
      type: "DISMISS_TOAST",
      toastId: "1",
    });
    expect(result.toasts[0].open).toBe(false);
    expect(result.toasts[1].open).toBe(true);
  });

  it("dismisses all toasts when no id provided", () => {
    const state = {
      toasts: [
        { id: "1", title: "First", open: true },
        { id: "2", title: "Second", open: true },
      ],
    };
    const result = reducer(state, {
      type: "DISMISS_TOAST",
    });
    expect(result.toasts.every((t) => t.open === false)).toBe(true);
  });

  it("removes a specific toast by id", () => {
    const state = {
      toasts: [
        { id: "1", title: "First", open: true },
        { id: "2", title: "Second", open: true },
      ],
    };
    const result = reducer(state, {
      type: "REMOVE_TOAST",
      toastId: "1",
    });
    expect(result.toasts).toHaveLength(1);
    expect(result.toasts[0].id).toBe("2");
  });

  it("removes all toasts when no id provided", () => {
    const state = {
      toasts: [
        { id: "1", title: "First", open: true },
        { id: "2", title: "Second", open: true },
      ],
    };
    const result = reducer(state, {
      type: "REMOVE_TOAST",
    });
    expect(result.toasts).toHaveLength(0);
  });

  it("new toasts are prepended (newest first)", () => {
    const state = {
      toasts: [{ id: "1", title: "First", open: true }],
    };
    const result = reducer(state, {
      type: "ADD_TOAST",
      toast: { id: "2", title: "Second", open: true },
    });
    expect(result.toasts[0].id).toBe("2");
    expect(result.toasts[1].id).toBe("1");
  });
});

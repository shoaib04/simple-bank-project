import { afterEach, describe, expect, it, vi } from "vitest";
import { createTransfer } from "./api.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createTransfer", () => {
  it("posts decimal-string transfer fields only under /api/v1", async () => {
    const request = {
      from_account: "10000001",
      to_account: "20000002",
      amount: "25.00",
      idempotency_key: "request-001",
    };
    const expectedResult = {
      transaction_id: "4de58d6c-840b-47eb-a2de-1950eaa1c113",
      from_account: "XXXX0001",
      to_account: "XXXX0002",
      amount: "25.00",
      status: "completed",
      created_at: "2026-10-17T12:00:00Z",
      error_code: null,
      message: "Transfer completed.",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => expectedResult,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(createTransfer(request)).resolves.toEqual(expectedResult);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/transfers",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
    expect(fetchMock.mock.calls.every(([url]) => url.startsWith("/api/v1/"))).toBe(true);
  });
});

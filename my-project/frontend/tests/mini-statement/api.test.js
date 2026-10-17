import { afterEach, describe, expect, it, vi } from "vitest";
import { getMiniStatement } from "../../src/features/mini-statement/api.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getMiniStatement", () => {
  it("encodes the account path and requests only the versioned endpoint", async () => {
    const statement = { account_number: "XXXX1234", transactions: [] };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => statement,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getMiniStatement("12345678/90123456")).resolves.toEqual(statement);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/accounts/12345678%2F90123456/mini-statement",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
    expect(fetchMock.mock.calls.every(([url]) => url.startsWith("/api/v1/"))).toBe(true);
  });

  it.each([401, 404])("surfaces an API error for status %s", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status,
        json: async () => ({ code: "INVALID_REQUEST", message: "Statement unavailable." }),
      }),
    );

    await expect(getMiniStatement("1234567890121234")).rejects.toMatchObject({
      status,
      code: "INVALID_REQUEST",
      message: "Statement unavailable.",
    });
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import TransferForm from "./TransferForm.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TransferForm rejection result", () => {
  it("shows the rejection code and transaction ID without showing success", async () => {
    const user = userEvent.setup();
    const transactionId = "4de58d6c-840b-47eb-a2de-1950eaa1c113";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        transaction_id: transactionId,
        from_account: "XXXX0001",
        to_account: "XXXX0002",
        amount: "500.00",
        status: "rejected",
        created_at: "2026-10-17T12:00:00Z",
        error_code: "DAILY_LIMIT_EXCEEDED",
        message: "The transfer limit for this account has been reached.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", { randomUUID: () => "request-rejection-001" });

    render(<TransferForm />);
    await user.type(screen.getByLabelText("From account"), "10000001");
    await user.type(screen.getByLabelText("To account"), "20000002");
    await user.type(screen.getByLabelText("Amount"), "500.00");
    await user.click(screen.getByRole("button", { name: /Review transfer/ }));

    expect(await screen.findByText("Transfer declined")).toBeInTheDocument();
    expect(screen.getByText("DAILY_LIMIT_EXCEEDED")).toBeInTheDocument();
    expect(screen.getByText(transactionId)).toBeInTheDocument();
    expect(screen.queryByText("Transfer complete")).not.toBeInTheDocument();
  });
});

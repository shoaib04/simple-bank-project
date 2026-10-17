import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import MiniStatement from "../../src/features/mini-statement/MiniStatement.jsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function setSuccessfulStatement(statement) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => statement }),
  );
}

async function submitAccount(user) {
  await user.type(screen.getByLabelText("Account number"), "1234567890121234");
  await user.click(screen.getByRole("button", { name: "View statement" }));
}

describe("MiniStatement", () => {
  it("shows a loading state then renders a masked newest-first statement", async () => {
    let resolveResponse;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(new Promise((resolve) => { resolveResponse = resolve; })),
    );
    const user = userEvent.setup();
    render(<MiniStatement />);
    await submitAccount(user);
    expect(screen.getByText("Loading statement…")).toBeInTheDocument();

    resolveResponse({
      ok: true,
      status: 200,
      json: async () => ({
        account_number: "XXXX1234",
        transactions: [
          {
            date: "2026-10-17T12:00:00Z",
            description: "Transfer to XXXX5678",
            debit: "25.00",
            credit: "0.00",
            amount: "25.00",
            balance_after: "75.00",
          },
        ],
      }),
    });

    expect(await screen.findByText("XXXX1234")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Transfer to XXXX5678")).toBeInTheDocument();
    expect(screen.getByText("75.00")).toBeInTheDocument();
    expect(screen.queryByText("1234567890121234")).not.toBeInTheDocument();
  });

  it("shows an empty state when the account has no completed transactions", async () => {
    setSuccessfulStatement({ account_number: "XXXX1234", transactions: [] });
    const user = userEvent.setup();
    render(<MiniStatement />);
    await submitAccount(user);

    expect(await screen.findByText("No completed transactions yet.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows a retryable error when the statement request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Connection unavailable.")),
    );
    const user = userEvent.setup();
    render(<MiniStatement />);
    await submitAccount(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to connect. Try again.");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

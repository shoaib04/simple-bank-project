import { useState } from "react";
import TransferForm from "./features/transfers/TransferForm.jsx";
import MiniStatement from "./features/mini-statement/MiniStatement.jsx";

export default function App() {
  const [activeView, setActiveView] = useState("transfer");

  return (
    <main className="app-shell">
      <header className="app-header">
        <a className="brand" href="/" aria-label="Simple Bank home">
          <span className="brand-mark" aria-hidden="true">S</span>
          <span>Simple Bank</span>
        </a>
      </header>
      <section className="transfer-page" aria-labelledby="page-title">
        <p className="eyebrow">SIMPLE BANK / ACCOUNTS</p>
        <h1 id="page-title">
          {activeView === "transfer" ? "Move money with confidence." : "Your recent account activity."}
        </h1>
        <p className="page-intro">
          {activeView === "transfer"
            ? "Transfer funds to another Simple Bank account."
            : "Review completed transfers for an account you own."}
        </p>
        <nav className="account-view-nav" aria-label="Account tools">
          <button
            aria-pressed={activeView === "transfer"}
            className={activeView === "transfer" ? "active" : ""}
            onClick={() => setActiveView("transfer")}
            type="button"
          >
            Transfer
          </button>
          <button
            aria-pressed={activeView === "statement"}
            className={activeView === "statement" ? "active" : ""}
            onClick={() => setActiveView("statement")}
            type="button"
          >
            Mini statement
          </button>
        </nav>
        {activeView === "transfer" ? <TransferForm /> : <MiniStatement />}
      </section>
    </main>
  );
}

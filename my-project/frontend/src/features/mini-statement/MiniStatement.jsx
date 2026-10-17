import { useState } from "react";
import { getMiniStatement } from "./api.js";

function formatDate(value) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default function MiniStatement() {
  const [accountNumber, setAccountNumber] = useState("");
  const [statement, setStatement] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  async function loadStatement(event) {
    event?.preventDefault();
    if (!accountNumber.trim()) return;

    setPending(true);
    setStatement(null);
    setError(null);
    try {
      setStatement(await getMiniStatement(accountNumber.trim()));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mini-statement" aria-labelledby="mini-statement-title">
      <header className="statement-heading">
        <div>
          <p className="eyebrow">ACCOUNT ACTIVITY</p>
          <h2 id="mini-statement-title">Mini statement</h2>
          <p className="statement-intro">Review your 10 most recent completed transactions.</p>
        </div>
        {statement ? <p className="statement-account">{statement.account_number}</p> : null}
      </header>

      <form className="statement-lookup" onSubmit={loadStatement}>
        <label className="statement-account-field">
          <span>Account number</span>
          <input
            autoComplete="off"
            inputMode="numeric"
            name="account_number"
            onChange={(event) => setAccountNumber(event.target.value)}
            placeholder="Enter an account you own"
            required
            value={accountNumber}
          />
        </label>
        <button className="statement-submit" disabled={pending} type="submit">
          {pending ? "Loading statement..." : "View statement"}
        </button>
      </form>

      {pending ? (
        <p className="statement-loading" role="status" aria-live="polite">
          Loading statement…
        </p>
      ) : null}

      {error ? (
        <div className="statement-error" role="alert">
          <div>
            <h3>Statement unavailable</h3>
            <p>{error.message || "Unable to load this account's statement."}</p>
          </div>
          <button className="statement-retry" onClick={() => loadStatement()} type="button">
            Try again
          </button>
        </div>
      ) : null}

      {statement && statement.transactions.length === 0 ? (
        <div className="statement-empty" role="status">
          <span className="statement-empty-mark" aria-hidden="true">—</span>
          <div>
            <h3>No completed transactions yet.</h3>
            <p>New account activity will appear here.</p>
          </div>
        </div>
      ) : null}

      {statement?.transactions.length > 0 ? (
        <div className="statement-table-wrap">
          <table className="statement-table">
            <caption>Recent transactions for {statement.account_number}</caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Description</th>
                <th scope="col">Debit</th>
                <th scope="col">Credit</th>
                <th scope="col">Amount</th>
                <th scope="col">Balance after</th>
              </tr>
            </thead>
            <tbody>
              {statement.transactions.map((transaction, index) => (
                <tr key={`${transaction.date}-${index}`}>
                  <td>{formatDate(transaction.date)} UTC</td>
                  <td>{transaction.description}</td>
                  <td className="statement-debit">{transaction.debit}</td>
                  <td className="statement-credit">{transaction.credit}</td>
                  <td>{transaction.amount}</td>
                  <td>{transaction.balance_after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

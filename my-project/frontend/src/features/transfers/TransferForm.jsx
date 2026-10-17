import { useRef, useState } from "react";
import { createTransfer } from "./api.js";

const initialFields = {
  from_account: "",
  to_account: "",
  amount: "",
};

export default function TransferForm() {
  const [fields, setFields] = useState(initialFields);
  const [pending, setPending] = useState(false);
  const [outcome, setOutcome] = useState(null);
  const [failure, setFailure] = useState(null);
  const idempotencyRef = useRef(null);

  function updateField(event) {
    const { name, value } = event.target;
    setFields((current) => ({ ...current, [name]: value }));
    setOutcome(null);
    setFailure(null);
  }

  async function submitTransfer(event) {
    event.preventDefault();
    const fingerprint = JSON.stringify(fields);
    if (idempotencyRef.current?.fingerprint !== fingerprint) {
      idempotencyRef.current = {
        fingerprint,
        key: crypto.randomUUID(),
      };
    }

    setPending(true);
    setOutcome(null);
    setFailure(null);
    try {
      const result = await createTransfer({
        ...fields,
        idempotency_key: idempotencyRef.current.key,
      });
      setOutcome(result);
    } catch (error) {
      setFailure({ code: error.code ?? "NETWORK_ERROR", message: error.message });
    } finally {
      setPending(false);
    }
  }

  function startNewTransfer() {
    idempotencyRef.current = null;
    setFields(initialFields);
    setOutcome(null);
    setFailure(null);
  }

  return (
    <div className="transfer-layout">
      <form className="transfer-form" onSubmit={submitTransfer}>
        <div className="form-heading">
          <span className="form-index">01</span>
          <div>
            <h2>New transfer</h2>
            <p>Simple Bank account to account</p>
          </div>
        </div>

        <label className="field">
          <span>From account</span>
          <input
            autoComplete="off"
            name="from_account"
            onChange={updateField}
            placeholder="Enter account number"
            required
            value={fields.from_account}
          />
        </label>

        <label className="field">
          <span>To account</span>
          <input
            autoComplete="off"
            name="to_account"
            onChange={updateField}
            placeholder="Enter recipient account number"
            required
            value={fields.to_account}
          />
        </label>

        <label className="field amount-field">
          <span>Amount</span>
          <span className="amount-input-wrap">
            <span aria-hidden="true">Rs</span>
            <input
              aria-label="Amount"
              inputMode="decimal"
              name="amount"
              onChange={updateField}
              placeholder="0.00"
              required
              type="text"
              value={fields.amount}
            />
          </span>
        </label>

        <button className="submit-button" disabled={pending} type="submit">
          <span>{pending ? "Submitting..." : "Review transfer"}</span>
          <span aria-hidden="true">{pending ? "..." : "→"}</span>
        </button>
      </form>

      <aside className="transfer-aside" aria-label="Transfer result">
        <div className="aside-rule" />
        <p className="eyebrow">TRANSFER STATUS</p>
        {outcome ? (
          <div
            className={`outcome outcome-${outcome.status}`}
            aria-live="polite"
            role="status"
          >
            <span className="outcome-symbol" aria-hidden="true">
              {outcome.status === "completed" ? "✓" : "!"}
            </span>
            <div>
              <h2>{outcome.status === "completed" ? "Transfer complete" : "Transfer declined"}</h2>
              <p>{outcome.message}</p>
              <dl className="result-details">
                <div>
                  <dt>Amount</dt>
                  <dd>Rs {outcome.amount}</dd>
                </div>
                <div>
                  <dt>Transaction ID</dt>
                  <dd className="transaction-id">{outcome.transaction_id}</dd>
                </div>
              </dl>
              {outcome.error_code ? <p className="error-code">{outcome.error_code}</p> : null}
              <button className="text-button" onClick={startNewTransfer} type="button">
                Start another transfer <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        ) : failure ? (
          <div className="outcome outcome-error" aria-live="assertive" role="alert">
            <span className="outcome-symbol" aria-hidden="true">!</span>
            <div>
              <h2>We could not submit this transfer</h2>
              <p>{failure.message}</p>
              <p className="error-code">{failure.code}</p>
              <p className="retry-note">Your entries are unchanged. You can retry this request.</p>
            </div>
          </div>
        ) : (
          <div className="empty-result">
            <span className="empty-mark" aria-hidden="true">↗</span>
            <p>Your transfer result will appear here.</p>
          </div>
        )}
      </aside>
    </div>
  );
}

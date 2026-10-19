# Agent Wallet Guard

**Let AI agents use PayPal without handing them the keys.**

Agent Wallet Guard is an [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that sits between an AI agent and PayPal. The agent never calls PayPal directly: every invoice or refund request goes through a policy layer that decides **allow**, **deny** or **ask a human**. The owner writes the rules in plain language, and every decision comes with a plain-language explanation and an audit trail.

Built for the *Build What's Next with PayPal and AI* hackathon. Everything runs against the **PayPal sandbox**; no real money is involved.

## Why

AI agents are starting to invoice, buy and refund on our behalf. One bad prompt, one hallucinated recipient or one runaway loop can drain an account. Agent Wallet Guard puts enforceable limits and a human approval step between the agent and the money.

## How it works

```
AI agent --(MCP tools)--> policy engine --> PayPal sandbox
                              |
              needs approval  |  deny
                    v         v
              approval queue  audit log (SQLite) --> read-only dashboard
                    ^
         human: python approve.py approve ID
```

1. The owner states the rules in plain language, for example:
   *"Invoices: at most $80 each, $200 per day, ask me above $50. Refunds: at most $30 each, $100 per day, ask me above $20."*
2. An LLM turns that sentence into structured limits. The result is **validated in code** and shown to the owner, who must confirm before it is saved.
3. The agent calls MCP tools. A deterministic policy engine (no AI involved) checks each request and returns a verdict.
4. Small requests run immediately. Requests above the approval threshold wait in a queue until a human approves or rejects them. Limits are re-checked at approval time, so a human "yes" cannot break a budget.
5. Every decision is written to an audit log, and the LLM adds a short plain-language explanation to each response.

### Design principles

- **The LLM never decides whether money moves.** It only translates rules and explains decisions. Enforcement is deterministic, tested code.
- **The agent cannot approve its own requests or change its own limits.** Approval and policy changes exist only as a command line tool for the human, not as MCP tools.
- **Defense in depth on inputs.** Amounts are strictly validated (no NaN or negative values), capture ids are format-checked, refund approvals use PayPal idempotency keys so a request cannot be executed twice, and the dashboard escapes all agent-supplied text.
- **Works without an AI key.** Without `GEMINI_API_KEY`, the server still enforces the stored policy; explanations fall back to the technical reason. (Setting a policy from plain language needs the key.)

## MCP tools (what the agent sees)

| Tool | Description |
|---|---|
| `create_invoice(email, description, amount)` | Creates a PayPal sandbox invoice draft, subject to the invoice policy. Returns `executed`, `needs_approval` (with an `approval_id`) or `denied`, plus an explanation. |
| `refund(capture_id, amount, reason)` | Refunds part or all of a captured payment, subject to the refund policy. Same three outcomes. |
| `check_approval(approval_id)` | Read-only status of a pending request. |
| `get_policy()` | Read-only view of the active limits. |

## Human commands

```
python approve.py list                  # pending approvals
python approve.py approve ID            # approve and execute (limits re-checked)
python approve.py reject ID             # reject
python approve.py audit                 # latest decisions
python approve.py policy                # show active policy
python approve.py policy "rule text"    # set policy from plain language (asks to confirm)
python dashboard.py                     # read-only dashboard at http://127.0.0.1:8000
python make_test_payment.py             # create a sandbox payment to refund (see below)
```

Replace `ID` with the number shown by `list` (no angle brackets).

## AI usage

| Where | Model | Purpose |
|---|---|---|
| `awg/policy_nl.py` | Google Gemini API (`gemini-flash-lite-latest` by default) | Converts a plain-language rule into structured JSON limits. Output is validated (positive numbers, consistent limits, valid emails) before anything is saved. |
| `awg/explain.py` | Same | Writes a short human-readable explanation of each decision. Falls back to the technical reason if the model is unavailable. |

The model can be changed with `GEMINI_MODEL`. The provider is isolated in `awg/llm.py`.

## PayPal usage

PayPal sandbox, REST API, OAuth 2.0 client-credentials:

- **Invoicing API v2**: create invoice drafts (`create_invoice`)
- **Orders API v2**: create and capture a test payment (`make_test_payment.py`)
- **Payments API v2**: refund a captured payment (`refund`), with `PayPal-Request-Id` for idempotency

## Setup

Requirements: Python 3.10+, Node.js (only for the MCP Inspector demo), a free PayPal sandbox app and a free Gemini API key.

```bash
git clone https://github.com/Zhannatik/agent-wallet-guard.git
cd agent-wallet-guard
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS / Linux:       source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (see `.env.example`):

```
PAYPAL_CLIENT_ID=...
PAYPAL_SECRET=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-flash-lite-latest
```

- **PayPal:** [developer.paypal.com](https://developer.paypal.com) -> Apps & Credentials -> Sandbox -> create an app, enable **Invoicing**, copy Client ID and Secret. Sandbox test accounts (a Business merchant and a Personal buyer) are created for you under Testing Tools -> Sandbox Accounts.
- **Gemini:** free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

Run the tests (no network needed):

```bash
python -m pytest
```

## Try it

1. **Set a policy** from plain language (on PowerShell use single quotes so `$` is not expanded):
```bash
   python approve.py policy 'Invoices: at most $80 each, $200 per day, ask me above $50. Refunds: at most $30 each, $100 per day, ask me above $20'
```
   Check the parsed limits and answer `y`.

2. **Start the MCP Inspector** with the server and open the printed URL:
```bash
   npx @modelcontextprotocol/inspector python -m awg.server
```
   (On Windows with a virtual environment: `npx @modelcontextprotocol/inspector .venv\Scripts\python.exe -m awg.server`.) Click **Connect**, then **Tools**.

3. **Invoices.** Call `create_invoice` with `test@example.com`, `Test item` and:
   - `10.00` -> `executed` (a draft invoice appears in the sandbox)
   - `60.00` -> `needs_approval`; then `python approve.py list` and `python approve.py approve ID`
   - `100.00` -> `denied` (above the per-transaction limit)

4. **Refunds.** A refund needs a completed payment:
```bash
   python make_test_payment.py
```
   Open the printed link (a private window works best), log in with your sandbox **Personal** buyer account, approve the payment, press Enter in the terminal, and copy the printed `capture_id`. Then call `refund` with that id and:
   - `10.00` -> `executed`
   - `25.00` -> `needs_approval`; approve it with `python approve.py approve ID`
   - `40.00` -> `denied` (above the per-refund limit)

5. **Watch the audit trail**, in the terminal (`python approve.py audit`) or on the dashboard (`python dashboard.py`, then open http://127.0.0.1:8000).

The dashboard is read-only and listens on localhost only. Approvals stay a deliberate human action in the terminal.

To use the server from an MCP client such as Claude Desktop or Claude Code, register the command `python -m awg.server` with the project folder as working directory.

State (approvals, audit log, policy) lives in a local `awg.db` SQLite file. Delete it to reset. "Today" in daily budgets means the current UTC day.

## Project structure

```
awg/
  server.py        MCP tools
  paypal_client.py PayPal sandbox calls (invoices, orders, refunds)
  policy.py        deterministic policy engine (invoices and refunds)
  policy_nl.py     plain language -> validated policy (LLM)
  explain.py       decision explanations (LLM)
  llm.py           Gemini API wrapper
  approvals.py     human approval flow
  store.py         SQLite: approvals, audit log, policy
approve.py         human command line tool
dashboard.py       read-only dashboard
make_test_payment.py  creates a sandbox payment so refunds can be tested
tests/             unit tests for the policy engine and policy validation
```

## Roadmap

- Payout tool guarded by the same policy engine
- Approvals through messaging apps (WhatsApp, Slack)
- Per-agent identities and separate budgets
- Anomaly detection on agent spending patterns

## License

MIT
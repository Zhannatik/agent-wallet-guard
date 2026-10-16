# Agent Wallet Guard

**Let AI agents use PayPal without handing them the keys.**

Agent Wallet Guard is an [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that sits between an AI agent and PayPal. The agent never calls PayPal directly: every payment request goes through a policy layer that decides **allow**, **deny** or **ask a human**. The owner writes the rules in plain language, and every decision comes with a plain-language explanation.

Built for the *Build What's Next with PayPal and AI* hackathon. Everything runs against the **PayPal sandbox**.

## Why

AI agents are starting to invoice, buy and refund on our behalf. One bad prompt, one hallucinated recipient or one runaway loop can drain an account. Agent Wallet Guard puts enforceable limits and a human approval step between the agent and the money.

## How it works

```
AI agent --(MCP tools)--> policy engine --> PayPal sandbox
                              |
              needs approval  |  deny
                    v         v
              approval queue  audit log (SQLite)
                    ^
         human: python approve.py approve <id>
```

1. The owner states the rules in plain language, for example:
   *"Spend at most $200 per day, no single payment over $80, and ask me before anything above $30."*
2. An LLM turns that sentence into structured limits. The result is **validated in code** and shown to the owner, who must confirm before it is saved.
3. The agent calls MCP tools. A deterministic policy engine (no AI involved) checks each request against the limits and returns a verdict.
4. Small requests run immediately. Requests above the approval threshold wait in a queue until a human approves or rejects them. Limits are re-checked at approval time, so a human "yes" cannot break the daily budget.
5. Every decision is written to an audit log, and the LLM adds a short plain-language explanation to each response.

### Design principles

- **The LLM never decides whether money moves.** It only translates rules and explains decisions. Enforcement is deterministic, tested code.
- **The agent cannot approve its own payments or change its own limits.** Approval and policy changes exist only as a command line tool for the human, not as MCP tools.
- **Works without an AI key.** Without `GEMINI_API_KEY`, the server still enforces the default policy; explanations fall back to the technical reason.

## MCP tools (what the agent sees)

| Tool | Description |
|---|---|
| `create_invoice(email, description, amount)` | Creates a PayPal sandbox invoice draft, subject to the active policy. Returns `executed`, `needs_approval` (with an `approval_id`) or `denied`, plus an explanation. |
| `check_approval(approval_id)` | Read-only status of a pending request. |
| `get_policy()` | Read-only view of the active limits. |

## Human commands

```
python approve.py list                 # pending approvals
python approve.py approve <id>         # approve and execute
python approve.py reject <id>          # reject
python approve.py policy               # show active policy
python approve.py policy "<rule text>" # set policy from plain language (asks to confirm)
```

## AI usage

| Where | Model | Purpose |
|---|---|---|
| `awg/policy_nl.py` | Google Gemini API (`gemini-flash-lite-latest` by default) | Converts a plain-language rule into structured JSON limits. Output is validated (positive numbers, consistent limits, valid emails). |
| `awg/explain.py` | Same | Writes a short human-readable explanation of each decision. Falls back to the technical reason if the model is unavailable. |

The model is configurable through `GEMINI_MODEL`. The AI provider is isolated in `awg/llm.py`.

## PayPal usage

- OAuth 2.0 client-credentials token
- Invoicing API v2 (`POST /v2/invoicing/invoices`) in the **sandbox**

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

Create a `.env` file (see `.env.example`):

```
PAYPAL_CLIENT_ID=...
PAYPAL_SECRET=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-flash-lite-latest
```

- PayPal: [developer.paypal.com](https://developer.paypal.com) -> Apps & Credentials -> Sandbox -> create an app, enable **Invoicing** in its features, copy Client ID and Secret.
- Gemini: free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

Run the tests (no network needed):

```bash
python -m pytest
```

## Try it

1. Set a policy from plain language:
```bash
   python approve.py policy "Spend at most $200 per day, no single payment over $80, and ask me before anything above $30"
```
   (On PowerShell use single quotes around the text so `$` is not expanded.) Check the parsed limits and answer `y`.

2. Start the MCP Inspector with the server:
```bash
   npx @modelcontextprotocol/inspector python -m awg.server
```
   Open the printed URL, click **Connect**, then **Tools**.

3. Call `create_invoice` with `test@example.com`, `Test item` and:
   - `10.00` -> `executed` (a draft invoice is created in the sandbox)
   - `50.00` -> `needs_approval`; then run `python approve.py list` and `python approve.py approve <id>`
   - `100.00` -> `denied` (above the per-transaction limit)

   Each response includes a plain-language `explanation`.

To use the server from an MCP client such as Claude Desktop or Claude Code, register the command `python -m awg.server` with the project folder as working directory.

State (approvals, audit log, policy) is stored in a local `awg.db` SQLite file; delete it to reset.

## Project structure

```
awg/
  server.py        MCP tools
  paypal_client.py PayPal sandbox calls
  policy.py        deterministic policy engine
  policy_nl.py     plain language -> validated policy (LLM)
  explain.py       decision explanations (LLM)
  llm.py           Gemini API wrapper
  approvals.py     human approval flow
  store.py         SQLite: approvals, audit log, policy
approve.py         human command line tool
tests/             unit tests for the policy engine and policy validation
```

## Roadmap

- Refund and payout tools guarded by the same policy engine
- Web dashboard for the audit log and approval queue
- Approvals through messaging apps
- Per-agent identities and budgets

## License

MIT
from mcp.server.fastmcp import FastMCP

from awg import paypal_client, store
from awg.policy import DEFAULT_POLICY, Verdict, evaluate

mcp = FastMCP("agent-wallet-guard")
store.init()


@mcp.tool()
async def create_invoice(email: str, description: str, amount: str) -> dict:
    """Create a PayPal invoice draft (sandbox), checked against the spending policy."""
    decision = evaluate(amount, email, store.spent_today(), DEFAULT_POLICY)

    if decision.verdict == Verdict.DENY:
        store.log("invoice", email, amount, "denied", decision.reason)
        return {"status": "denied", "reason": decision.reason}

    if decision.verdict == Verdict.NEEDS_APPROVAL:
        approval_id = store.add_approval(email, description, amount, decision.reason)
        store.log("invoice", email, amount, "needs_approval", decision.reason)
        return {"status": "needs_approval", "approval_id": approval_id, "reason": decision.reason}

    result = await paypal_client.create_invoice_draft(email, description, amount)
    store.log("invoice", email, amount, "executed", decision.reason)
    return {"status": "executed", "reason": decision.reason, "paypal": result}


@mcp.tool()
async def check_approval(approval_id: int) -> dict:
    """Check the status of a pending approval request (read-only)."""
    a = store.get_approval(approval_id)
    if a is None:
        return {"status": "not_found"}
    return {"status": a["status"], "reason": a["reason"]}


if __name__ == "__main__":
    mcp.run()
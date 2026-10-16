from mcp.server.fastmcp import FastMCP

from awg import paypal_client, store
from awg.explain import explain
from awg.policy import Verdict, describe_limits, evaluate, evaluate_refund

mcp = FastMCP("agent-wallet-guard")
store.init()


@mcp.tool()
async def create_invoice(email: str, description: str, amount: str) -> dict:
    """Create a PayPal invoice draft (sandbox), checked against the spending policy."""
    policy = store.load_policy()
    decision = evaluate(amount, email, store.spent_today("invoice"), policy)
    explanation = await explain(
        "invoice", decision.verdict.value, decision.reason, amount, describe_limits(policy)
    )

    if decision.verdict == Verdict.DENY:
        store.log("invoice", email, amount, "denied", decision.reason)
        return {"status": "denied", "reason": decision.reason, "explanation": explanation}

    if decision.verdict == Verdict.NEEDS_APPROVAL:
        approval_id = store.add_approval("invoice", email, description, amount, decision.reason)
        store.log("invoice", email, amount, "needs_approval", decision.reason)
        return {
            "status": "needs_approval", "approval_id": approval_id,
            "reason": decision.reason, "explanation": explanation,
        }

    result = await paypal_client.create_invoice_draft(email, description, amount)
    store.log("invoice", email, amount, "executed", decision.reason)
    return {"status": "executed", "explanation": explanation, "paypal": result}


@mcp.tool()
async def refund(capture_id: str, amount: str, reason: str = "") -> dict:
    """Refund part or all of a captured PayPal payment (sandbox), checked against the refund policy."""
    if not paypal_client.valid_capture_id(capture_id):
        return {"status": "denied", "reason": "Invalid capture id"}

    policy = store.load_policy()
    decision = evaluate_refund(amount, store.spent_today("refund"), policy)
    explanation = await explain(
        "refund", decision.verdict.value, decision.reason, amount, describe_limits(policy, "refund")
    )

    if decision.verdict == Verdict.DENY:
        store.log("refund", capture_id, amount, "denied", decision.reason)
        return {"status": "denied", "reason": decision.reason, "explanation": explanation}

    if decision.verdict == Verdict.NEEDS_APPROVAL:
        approval_id = store.add_approval("refund", capture_id, reason or "Refund", amount, decision.reason)
        store.log("refund", capture_id, amount, "needs_approval", decision.reason)
        return {
            "status": "needs_approval", "approval_id": approval_id,
            "reason": decision.reason, "explanation": explanation,
        }

    result = await paypal_client.refund_capture(capture_id, amount, note=reason)
    store.log("refund", capture_id, amount, "executed", decision.reason)
    return {"status": "executed", "explanation": explanation, "paypal": result}


@mcp.tool()
async def check_approval(approval_id: int) -> dict:
    """Check the status of a pending approval request (read-only)."""
    a = store.get_approval(approval_id)
    if a is None:
        return {"status": "not_found"}
    return {"status": a["status"], "reason": a["reason"]}


@mcp.tool()
async def get_policy() -> dict:
    """Show the active spending and refund limits (read-only; agents cannot change them)."""
    p = store.load_policy()
    return {
        "max_per_tx": str(p.max_per_tx),
        "daily_budget": str(p.daily_budget),
        "approval_threshold": str(p.approval_threshold),
        "max_refund": str(p.max_refund),
        "daily_refund_budget": str(p.daily_refund_budget),
        "refund_approval_threshold": str(p.refund_approval_threshold),
        "allowed_recipients": p.allowed_recipients,
    }


if __name__ == "__main__":
    mcp.run()
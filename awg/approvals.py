from awg import paypal_client, store
from awg.policy import DEFAULT_POLICY, Verdict, evaluate


async def resolve(approval_id: int, approve: bool) -> dict:
    a = store.get_approval(approval_id)
    if a is None:
        return {"status": "error", "reason": "Approval not found"}
    if a["status"] != "pending":
        return {"status": "error", "reason": f"Already {a['status']}"}

    if not approve:
        store.set_status(approval_id, "rejected", "Rejected by human")
        store.log("invoice", a["email"], a["amount"], "rejected", "Rejected by human")
        return {"status": "rejected"}

    # жёсткие лимиты перепроверяются в момент одобрения: "да" человека не обходит бюджет
    decision = evaluate(a["amount"], a["email"], store.spent_today(), DEFAULT_POLICY)
    if decision.verdict == Verdict.DENY:
        store.set_status(approval_id, "denied", decision.reason)
        store.log("invoice", a["email"], a["amount"], "denied", decision.reason)
        return {"status": "denied", "reason": decision.reason}

    result = await paypal_client.create_invoice_draft(a["email"], a["description"], a["amount"])
    store.set_status(approval_id, "approved", "Approved by human")
    store.log("invoice", a["email"], a["amount"], "executed", "Approved by human")
    return {"status": "executed", "paypal": result}
from awg import paypal_client, store
from awg.policy import Verdict, evaluate, evaluate_refund


async def resolve(approval_id: int, approve: bool) -> dict:
    a = store.get_approval(approval_id)
    if a is None:
        return {"status": "error", "reason": "Approval not found"}
    if a["status"] != "pending":
        return {"status": "error", "reason": f"Already {a['status']}"}

    kind = a["kind"]

    if not approve:
        store.set_status(approval_id, "rejected", "Rejected by human")
        store.log(kind, a["email"], a["amount"], "rejected", "Rejected by human")
        return {"status": "rejected"}

    # жёсткие лимиты перепроверяются в момент одобрения: "да" человека не обходит бюджет
    policy = store.load_policy()
    if kind == "refund":
        decision = evaluate_refund(a["amount"], store.spent_today("refund"), policy)
    else:
        decision = evaluate(a["amount"], a["email"], store.spent_today("invoice"), policy)

    if decision.verdict == Verdict.DENY:
        store.set_status(approval_id, "denied", decision.reason)
        store.log(kind, a["email"], a["amount"], "denied", decision.reason)
        return {"status": "denied", "reason": decision.reason}

    if kind == "refund":
        result = await paypal_client.refund_capture(
            a["email"], a["amount"], note=a["description"],
            request_id=f"awg-refund-approval-{approval_id}",
        )
    else:
        result = await paypal_client.create_invoice_draft(a["email"], a["description"], a["amount"])

    store.set_status(approval_id, "approved", "Approved by human")
    store.log(kind, a["email"], a["amount"], "executed", "Approved by human")
    return {"status": "executed", "paypal": result}
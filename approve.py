import asyncio
import sys

from awg import approvals, store
from awg.policy_nl import parse_policy


def show_policy(p) -> None:
    print(f"  max per transaction : {p.max_per_tx}")
    print(f"  daily budget        : {p.daily_budget}")
    print(f"  approval above      : {p.approval_threshold}")
    print(f"  allowed recipients  : {p.allowed_recipients or 'any'}")


async def set_policy(text: str) -> None:
    current = store.load_policy()
    new = await parse_policy(text, current)
    print("Parsed policy:")
    show_policy(new)
    if input("Save this policy? [y/N] ").strip().lower() == "y":
        store.save_policy(new)
        print("Saved.")
    else:
        print("Not saved.")


def main() -> None:
    store.init()
    args = sys.argv[1:]

    if not args or args[0] == "list":
        pending = store.list_pending()
        if not pending:
            print("No pending approvals.")
        for a in pending:
            print(f"#{a['id']}  {a['amount']}  to {a['email']}  ({a['description']})  - {a['reason']}")
    elif args[0] in ("approve", "reject") and len(args) == 2:
        print(asyncio.run(approvals.resolve(int(args[1]), args[0] == "approve")))
    elif args[0] == "policy" and len(args) == 1:
        show_policy(store.load_policy())
    elif args[0] == "policy" and len(args) == 2:
        asyncio.run(set_policy(args[1]))
    else:
        print('Usage: python approve.py [list | approve <id> | reject <id> | policy ["rule text"]]')


if __name__ == "__main__":
    main()
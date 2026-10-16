import asyncio
import sys

from awg import approvals, store


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
        result = asyncio.run(approvals.resolve(int(args[1]), args[0] == "approve"))
        print(result)
    else:
        print("Usage: python approve.py [list | approve <id> | reject <id>]")


if __name__ == "__main__":
    main()
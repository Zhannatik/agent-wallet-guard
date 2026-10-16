import asyncio

from awg import paypal_client


async def main() -> None:
    amount = input("Amount to charge the test buyer [100.00]: ").strip() or "100.00"
    order = await paypal_client.create_order(amount)
    print("\n1) Open this link, log in with a SANDBOX PERSONAL (buyer) account and approve:")
    print(order["approve_url"])
    input("\n2) After approving (the browser may land on example.com), press Enter here... ")
    cap = await paypal_client.capture_order(order["order_id"])
    print("\nCaptured:", cap)
    print(f'\nUse this capture id with the refund tool: {cap["capture_id"]}')


asyncio.run(main())
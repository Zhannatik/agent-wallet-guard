import asyncio

from awg import paypal_client


async def main():
    result = await paypal_client.create_invoice_draft(
        "tests@example.com", "Test item", "10.00"
    )
    print(result)


asyncio.run(main())
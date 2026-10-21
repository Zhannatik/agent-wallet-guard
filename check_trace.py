import asyncio
from dotenv import load_dotenv
load_dotenv()
from langfuse import get_client
from awg import llm

lf = get_client()
print("auth:", lf.auth_check())

with lf.start_as_current_observation(as_type="generation", name="smoke", model="test", input="ping") as g:
    g.update(output="pong")

print(asyncio.run(llm.generate("Reply with the single word OK", name="smoke-gemini")))
lf.flush()
print("done")
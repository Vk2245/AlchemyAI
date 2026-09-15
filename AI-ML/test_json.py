import sys
sys.stdout.reconfigure(encoding='utf-8')
from config.llm_client import get_structured_output
from pydantic import BaseModel

class A(BaseModel):
    name: str

print(get_structured_output('say my name is heisenberg', response_model=A, provider='groq'))

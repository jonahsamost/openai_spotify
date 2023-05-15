import cohere
import os
from loglib import logger
from typing import Dict, List, Union

coapi = os.getenv('COHERE_API_KEY')
assert coapi, 'No Cohere api key'

def get_assistant_message(
  messages: List[Dict[str, str]],
  temperature: int = .9,
  max_tokens=80,
  model: str = "command-light",
  number_id: str = '') -> str:

  prompt = [m['content'] for m in messages]
  prompt = '\n'.join(prompt)
  return get_assistant_message_with_str(
    prompt,
    temperature,
    max_tokens,
    model,
    number_id
  )

def get_assistant_message_with_str(
  prompt: str = '',
  temperature: int = .5,
  max_tokens=80,
  model: str = "command",
  number_id: str = '') -> str:

  co = cohere.Client(coapi)
  response = co.generate(
    prompt=prompt,
    model=model,
    temperature=temperature,
    max_tokens=max_tokens,
    k=0) 
  try:
    return response[0].text
  except Exception as e:
    logger.info('%s: Cohere exception: %s', number_id, e)
    return None

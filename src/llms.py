import environment as env
from pathlib import Path
import string
import backoff
import logging
import openai
import aiofiles
from .models import Completion
from typing import Any
import json

logging.getLogger('backoff').addHandler(logging.StreamHandler())
logging.getLogger('backoff').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

class LLMCall:
    
    async def ask_llm(self, **kwargs):
        pass


class GenericLLMCall(LLMCall):
    def __init__(self, client, root:str = None, model:str = "gpt-4o", temperature=0.042):
        if root:
            self.root = Path(root)
        else:
            self.root = Path(env.get("TEMPLATE_ROOT"))
        self.context = None
        self.client = client
        self.model = model
        self.temperature=temperature

 
    @backoff.on_exception(backoff.expo, [openai.RateLimitError])
    async def ask_llm(self, **kwargs):
        s = await self.read_prompt()
        u = await self.read_prompt(type="user", **kwargs)
        messages = [
            {"role": "system", "content": s},
            {"role": "user", "content": u}
        ]
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return completion.choices[0].message.content.strip()


    async def read_prompt(self, type="system", **kwargs):
        # TODO: maybe a caching read files could speed things up 🤔
        path = self.root/self.file_name()/f"{self.class_name()}.{type}"
        
        async with aiofiles.open(str(path), 'r') as file:
            # Read the template content
            template_content = await file.read()
            # Create a Template object
            template = string.Template(template_content)
            # Substitute variables
            result = template.substitute(**kwargs)
            return result


    def class_name(self):
        return self.__class__.__name__


    def file_name(self):
        return Path(__file__).stem


class PhonyLLMCall(GenericLLMCall):
    
    def __init__(self, phony_val:Any = None):
        self.v = phony_val
    
    async def ask_llm(self, **kwargs):
        return self.v


class ReviewSentiment(GenericLLMCall):
    
    async def ask_llm(self, **kwargs):
        text = await super().ask_llm(**kwargs)
        logger.info(f"{kwargs} : {text=}")
        return json.loads(text)

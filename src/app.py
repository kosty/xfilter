from quart import Quart, request, jsonify
from dotenv import load_dotenv
import json
from pathlib import Path
import asyncio
import asyncio
import logging
from typing import Dict, Any, List, Union, Optional
from pydantic import ValidationError
import openai
from imap_client import EmailMonitor, HEREmailMonitor, list_to_imap_search_criteria
import sys
from models import Email, Completion, HERLog
from smtp_client import send_followup, send_her_emails, send_reply
import environment as env
from llms import GenericLLMCall, ReviewSentiment
from store import SQLiteStore


load_dotenv()

        
app = Quart(__name__)
# To disable default access log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] [%(funcName)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.getLogger('hypercorn.access').disabled = True
# logging.getLogger("hypercorn.error").setLevel(logging.WARNING)
# logging.getLogger('quart.serving').setLevel(logging.ERROR)
# logging.getLogger('quart.app').setLevel(logging.ERROR)

store = SQLiteStore()

@app.route('/api/')
async def hello_world():
    app.logger.info("OLOLO")
    return jsonify({"message":"Hello, World!"}), 200


async def filter_via_llm(msg: Email):
    await store.add_email(msg)
    llm_client = openai.AsyncOpenAI()
    llm_call = GenericLLMCall(llm_client)
    answer = await llm_call.ask_llm(text=msg.body)
    completion = Completion(entity="email", entity_id=msg.id, llm_module=llm_call.class_name(), llm_completion=answer, )
    await store.add_completion(completion)
    app.logger.info("Reply recorded successfully!")
    ok = await init_her_cycle(msg, completion)
    
    # suggestion = msg.model_copy(update={"body":completion.llm_completion})
    # ok = await send_followup(suggestion)
    return True if ok else None


# Human Empowered Review
async def init_her_cycle(msg: Email, completion: Completion):
    try:
        reviewers = env.get_as_csv_list("HER_EMAIL_LIST")
        her_log = HERLog(entity='completion', entity_id=completion.id, outbound=reviewers, proposed=completion.llm_completion)
        await store.upsert_her_log(her_log)
        app.logger.info(f"{her_log} upserted")
        ok = await send_her_emails(msg, her_log)
        app.logger.info(f"HER outbound messages: {ok}")
        return True if ok else None
    except Exception:
        app.logger.exception("Failed sending outbound email. ")
        raise


# async def human_empowered_review_resolution(msg: Email, reply: str):
#     app.logger.info("Final stage - sending out HER-Resolved reply 🎉")
#     await send_reply(msg, reply)


@app.before_serving
async def startup():
    await store.initialize_db()
    user_email_monitor = EmailMonitor(task_factory=filter_via_llm, store=store)
    her_email_monitor = HEREmailMonitor(store=store, review_summarizer=ReviewSentiment(openai.AsyncOpenAI()))
    her_search_criteria =  list_to_imap_search_criteria(env.get_as_csv_list("HER_EMAIL_LIST"))

    app.email_monitors_task = asyncio.gather(
        asyncio.create_task(user_email_monitor.start(f'FROM "arsen@hosteasy.ai"'), name="EmailMonitor"),
        asyncio.create_task(her_email_monitor.start(f'{her_search_criteria}'), name="HERMonitor")
    )
    

@app.after_serving
async def shutdown():
    app.email_monitors_task.cancel()  # Or use a variable in the while loop


@app.route('/api', methods=['POST', 'GET', 'PUT'])
async def add_question():
    return jsonify({"error": "Not implemented yet"}), 500


async def main():
    await app.run_task()


if __name__ == '__main__':
    asyncio.run(main())

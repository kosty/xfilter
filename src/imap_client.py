import email.message
import aioimaplib
import asyncio
import email
import environment as env
import logging
import re
from typing import List, Optional
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime
from .models import Email, HERStatus, HERLog
from .store import BaseStore
from .llms import PhonyLLMCall, LLMCall
from .smtp_client import send_reply


# Configuration
SENDER_EMAIL = env.get("SENDER_EMAIL") 

logger = logging.getLogger(__name__)


def get_text_part(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                plain_text = part.get_payload(decode=True).decode('utf-8')
                logger.debug(f"Got plain text {plain_text}")
                return plain_text
        return None
    else:
        plain_single_part_text = msg.get_payload(decode=True).decode('utf-8')
        logger.debug(f"Got plain single part text {plain_single_part_text}")
        return plain_single_part_text


def extract_current_email_content(email_content:str) -> str:
    # Pattern to find the start of the quoted text
    pattern0 = re.compile(r"On .*,.* at .*<.*>")
    fwd_line = "---------- Forwarded message ----------"
    from_prefix = "From: "
    sprhmn_prefix = "Sent via Superhuman"
    
    lines = email_content.split('\r\n')
    email_lines = []
    for idx, line in enumerate(lines):    
        # Find the first occurrence of the pattern
        match = pattern0.search(line)
        if match:
            email_lines = lines[:idx]
            break
        elif fwd_line in line or line.startswith(from_prefix) or line.startswith(sprhmn_prefix):
            email_lines = lines[:idx]
            break
        
    content = '\r\n'.join(email_lines) if email_lines else email_content

    return content


def list_to_imap_search_criteria(emails: List[str] = None) -> str:
    if not emails:
        return ""  # Base case: if the list is empty, return None
    l = len(emails)
    if l == 2:
        return f"(OR FROM {emails[0]} FROM {emails[1]})"
    if l == 1:
        return f"FROM {emails[0]}"

    mid_index = len(emails) // 2  # Find the middle index
    # Create a tuple: (left subtree, root value, right subtree)
    l_subtree = list_to_imap_search_criteria(emails[:mid_index])
    r_subtree = list_to_imap_search_criteria(emails[mid_index:])
    return f"(OR {l_subtree} {r_subtree})"


aioimaplib_logger = logging.getLogger('aioimaplib.aioimaplib')
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s"))
aioimaplib_logger.addHandler(sh)


class EmailMonitor:
    def __init__(self, host:str=None, port:int=None, task_factory=None, user:str = None, password:str = None, store:BaseStore = None): 
        host = host if host else env.get("IMAP_HOST")
        port = port if port else env.get_int("IMAP_PORT")
        self.imap_client = aioimaplib.IMAP4_SSL(host=host, port=port)
        self.user = user if user else env.get("IMAP_USER")
        self.pwd =  password if password else env.get("IMAP_PASSWORD") 
        self.task_factory = task_factory
        self.store = store


    async def fetch_rfc822_email(self, email_id:str) -> Optional[Email]: # Optional[email.message.Message]:
        # Ensure email_id is a string
        logger.debug(f"Processing email ID: {email_id}") 
        # Fetch the email's subject
        result, data = await self.imap_client.fetch(email_id, 'RFC822')
        if result == 'OK':
            return self.data_to_email(data)
        logger.error(f"Got non-ok reply from server {result} : {data=}")
        return None

    def data_to_email(self, data) -> Email: # -> email.message.Message:
        msg = email.message_from_bytes(data[1])
        logger.info(f"Processing {msg['Subject']=}: {msg['Message-ID']} :  {msg.keys()}")
        txt = get_text_part(msg) # .split('\r\n')
        current_email = ""
        if txt:
            current_email = extract_current_email_content(txt)
        # f"{msg['To']=}\n{msg['From']=}\n{msg['Subject']=}\n{msg['Date']=}\n{msg['Message-ID']=}\n{msg['Sender']=}\n{msg['Reply-To']=}"
        datetime = parsedate_to_datetime(msg['Date'])
        recepients=[rec.strip() for rec in msg['To'].split(",")]
        cc=[rec.strip() for rec in msg['Cc'].split(",")] if 'Cc' in msg else None
        bcc=[rec.strip() for rec in msg['Bcc'].split(",")] if 'Bcc' in msg else None
        return Email(id=msg['Message-ID'], sender=msg['From'], recipients=recepients, subject=msg['Subject'], body=current_email, sent_at=datetime, reply_to=msg['In-Reply-To'], cc=cc, bcc=bcc, references=msg.get('References'), _msg=msg)

    async def fetch_subjects_emails(self, email_id_str):
        # Ensure email_id is a string
        print(f"Processing email ID: {email_id_str}") 
        # Fetch the email's subject
        result, data = await self.imap_client.fetch(email_id_str, '(BODY[HEADER.FIELDS (SUBJECT)])')
        if result == 'OK':
            subject = data[1].decode()
            print(f'Email ID {email_id_str}: {subject.strip()}')


    async def start(self, search_criteria=None):
        if not search_criteria:
            search_criteria=f'(FROM "{SENDER_EMAIL}")'

        await self.imap_client.wait_hello_from_server()

        # Login to the server
        await self.imap_client.login(self.user, self.pwd)

        # Select the inbox
        await self.imap_client.select('inbox')
        
        logger.info("EmailMonitor on duty 📧👨‍✈️")

        try:
            while True:
                try:
                    # Start IDLE mode
                    await self.imap_client.idle_start(timeout=10)  # Timeout after 300 seconds
                    # Wait for server responses
                    await self.imap_client.wait_server_push(timeout=600)

                    # Clean-up IDLE mode
                    self.imap_client.idle_done()

                    # Search for emails from a specific sender
                    logger.debug("EmailMonitor.imap_client.serach 🔍 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                    result, data = await self.imap_client.search(search_criteria)
                    if result != 'OK' or not data[0]:
                        logger.debug(f"EmailMonitor.imap_client.search {result=} : {data=}")
                        continue
                    
                    emailz = []
                    email_ids = data[0].split()
                    try:
                        # Apparently this part HAS to be sequential... is it protocol ?
                        for binary_email_id in email_ids:
                            email_id = binary_email_id.decode()
                            logger.info("EmailMonitor email id: 📧 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                            an_email = await self.fetch_rfc822_email(email_id)
                            if an_email:
                                if self.store:
                                    exists = await self.store.exists_email(an_email.id)
                                    if not exists:
                                        emailz.append(an_email)
                                    else:
                                        logger.debug(f"Email {email_id} (aka {an_email.id}) was responded to already, skipping")
                                else:
                                    logger.info("EmailMonitor.store is None, storing skipped, processing email ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                                    emailz.append(an_email)
                            else:
                                logger.info("EmailMonitor.fetch_rfc822_email returned None: 📧 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                    except Exception as e:
                        logger.exception(f"Something happened here! {e}")
                        raise
                    tasks = [ asyncio.create_task(self.task_factory(msg)) for msg in emailz ]
                    await asyncio.gather(*tasks)
                    logger.info("EmailMonitor loop ended: 📧 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑  
                except asyncio.TimeoutError:
                    logger.info("EmailMonitor IDLE timeout, restarting...")
                    self.imap_client.idle_done()           

        except asyncio.CancelledError:
            logger.info("EmailMonitor shutdown initiated...")
            # Perform any necessary cleanup here
            self.imap_client.idle_done()
            logger.info("Done ✅")
            return True
        except Exception as e:
            logger.exception(f"EmailMonitor.start 😖🤯 {e}")
            raise
        finally:
            await self.imap_client.logout()


def starts_with_uuid4(s):
    pattern = re.compile(r'^\[([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\]')

    match = pattern.match(s)
    if match:
        return True, match.group(1)
    return False, None


class HEREmailMonitor(EmailMonitor):
    
    def __init__(self, host:str=None, port:int=None, user:str = None, password:str = None, store:BaseStore = None, summarizer:LLMCall = None): 
        host = host if host else env.get("HER_IMAP_HOST")
        port = port if port else env.get_int("HER_IMAP_PORT")
        self.imap_client = aioimaplib.IMAP4_SSL(host=host, port=port)
        self.lookup_imap_client = aioimaplib.IMAP4_SSL(host=host, port=port)
        self.user = user if user else env.get("HER_IMAP_USER")
        self.pwd =  password if password else env.get("HER_IMAP_PASSWORD") 
        self.summarizer = summarizer if summarizer else PhonyLLMCall({"sentiment":"affirmative"})
        self.store = store


    async def cleanup(self):
        try:
            await self.imap_client.logout()
            await self.lookup_imap_client.logout()
            return True
        except asyncio.TimeoutError:
            return True


    async def lookup_sent(self, message_id: str) -> Optional[email.message.Message]:
        result, data = await self.lookup_imap_client.search(f"HEADER Message-ID {message_id}")
        if result == 'OK' and data[0]:
            email_ids = data[0].split()
            try:
                # Apparently this part HAS to be sequential... is it protocol ?
                for binary_email_id in email_ids:
                    email_id = binary_email_id.decode()
                    result, data = await self.lookup_imap_client.fetch(email_id, 'RFC822')
                    return email.message_from_bytes(data[1])
                    
            except Exception as e:
                print(f"Something happened here! {e}")
                return None
        return None
    
    async def imap_init(self):
        try:
            await self.imap_client.wait_hello_from_server()
            await self.lookup_imap_client.wait_hello_from_server()

            # Login to the server
            await self.imap_client.login(self.user, self.pwd)
            await self.lookup_imap_client.login(self.user, self.pwd)

            # Select the inbox
            result, data = await self.imap_client.select('inbox')
            if result != 'OK':
                logger.error(f"Failed to select mailbox {result} / {data}")
                await self.cleanup()
                return False
            
            result, data = await self.lookup_imap_client.select('ALL') #.select('"[Gmail]/Sent Mail"')
            if result != 'OK':
                logger.error(f"Failed to select mailbox {result} / {data}")
                await self.cleanup()
                return False
        except Exception as e:
            logger.exception(f"HEREmailMonitor.imap_init() {e}")
            return False
        
    def empty_line_idx(self, strings, offset=1):
        # Iterate over the list starting from the given index
        for i in range(offset+1, len(strings)):
            if strings[i] == "":
                return i
        # If no empty string is found, return the last index
        return len(strings) - 1


    def proposed_response(self, lines:list[str]) -> str:
        last_idx = self.empty_line_idx(lines)
        return "\r\n".join(lines[1:last_idx+1])

    async def human_amended_review(self, an_email: Email):
        logger.info(f"HEREmailMonitor.human_amended_review: 📧 : {an_email.id} : {an_email.sender} : {an_email.reply_to} : {an_email.subject}")
        original = await self.lookup_sent(an_email.references)
        her_log_id = None
        if original:
            her_log_id = original['X-Human-Empowered-Review-ID']
        else:
            ok, uuid4_str = starts_with_uuid4(an_email.subject)
            if ok:
                her_log_id = uuid4_str
            else:
                logger.warning(f"Couldn't locate original email sent to {an_email.recipients=} withh {an_email.id=} : {an_email.sender=} : {an_email.reply_to=} : {an_email.subject=} ")
                return None

        her_log = await self.store.get_her_log(her_log_id)
        if not her_log:
            logger.warning(f"Couldn't locate HER log record for {original['X-Human-Empowered-Review-ID']=}  as part of {original['Message-ID']=} from {original['From']=}")
            return None

        if her_log.status != HERStatus.OUTBOUND or her_log.inbound:
            logger.warning(f"HER review already resolved {her_log.status} {her_log.inbound}. Skipping email {an_email.id} from {an_email.sender}")
            return None

        # TODO we probably should convert outbound entries to "canonical" form
        #      i.e. a.a.a.a+bbbb@gmail.com -> aaaa@gmail.com
        if original['From'] not in her_log.outbound:
            logger.warning(f"HER review received from {original['From']=} which is not outbound list {her_log.outbound=}")

        entries = an_email.body.split("\r\n")
        her_response = await self.summarizer.ask_llm(text=entries[0])
        her_log.inbound = original['From']
        her_log.inbound_at = datetime.now()
        if "sentiment" in her_response and her_response["sentiment"] == "affirmative":
            her_log.status = HERStatus.APPROVED
        elif len(entries) > 1:
            her_log.status = HERStatus.AMENDED
            her_log.amended = self.proposed_response(entries)
        else:
            her_log.status = HERStatus.REJECTED

        self.store.upsert_her_log(her_log)
        return her_log


    async def send_out_approved_and_amended(self, updated_her_records: List[HERLog]):
        valid_her_records = [ her for her in updated_her_records if her and her.status in [HERStatus.APPROVED, HERStatus.AMENDED]]
        send_out_tasks = []
        for her in valid_her_records:
            if her.entity != 'completion':
                continue
            completion = await self.store.get_completion(her.entity_id)
            if not completion or completion.entity != "email":
                continue
            email = await self.store.get_email(completion.entity_id)
            if her.status == HERStatus.APPROVED:
                send_out_tasks.append(asyncio.create_task(send_reply(email, her.proposed)))
            elif her.status == HERStatus.AMENDED:
                send_out_tasks.append(asyncio.create_task(send_reply(email, her.amended)))
        await asyncio.gather(*send_out_tasks)


    async def start(self, search_criteria=None):
        # if not search_criteria:
        #     search_criteria=f'(FROM "{SENDER_EMAIL}")'

        try:
            await self.imap_client.wait_hello_from_server()
            await self.lookup_imap_client.wait_hello_from_server()

            # Login to the server
            await self.imap_client.login(self.user, self.pwd)
            await self.lookup_imap_client.login(self.user, self.pwd)

            # Select the inbox
            result, data = await self.imap_client.select('inbox')
            if result != 'OK':
                logger.error(f"Failed to select mailbox {result} / {data}")
                await self.cleanup()
                return False
            
            result, data = await self.lookup_imap_client.select('"[Gmail]/Sent Mail"')
            if result != 'OK':
                logger.error(f"Failed to select mailbox {result} / {data}")
                await self.cleanup()
                return False
            logger.info("HEREmailMonitor on duty 📧👨‍✈️")
            while True:
                try:
                    # Start IDLE mode
                    await self.imap_client.idle_start(timeout=10)  # Timeout after 300 seconds
                    
                    # Wait for server responses
                    await self.imap_client.wait_server_push(timeout=600)

                    # Clean-up IDLE mode
                    self.imap_client.idle_done()

                    # Search for emails from a specific sender
                    logger.info("HEREmailMonitor.imap_client.serach 🕵️📧 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                    result, data = await self.imap_client.search(search_criteria)
                    if result != 'OK':
                        logger.info(f"HEREmailMonitor.imap_client.serach [failed] {search_criteria} : {result=} {data=}")
                        continue
                    
                    if not data[0]:
                        logger.debug(f"HEREmailMonitor.imap_client.serach [empty resutl] {search_criteria} : {result=} {data=}")
                        continue
                
                    emailz = []
                    email_ids = data[0].split()
                    logger.info("HEREmailMonitor.fetch_rfc822_email [before]📧📝 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                    # Apparently this part HAS to be sequential... is it protocol ?
                    for binary_email_id in email_ids:
                        email_id = binary_email_id.decode()
                        an_email = await self.fetch_rfc822_email(email_id)
                        if not an_email:
                            logger.warning(f"Failed to fetch {email_id=}. Skipping.")
                            continue
                        if not an_email.body:
                            logger.warning(f"Email {an_email.id} body appears empty {email_id=}. Skipping.")
                        emailz.append(an_email)

                    logger.info("HEREmailMonitor.fetch_rfc822_email [after]📝 ") # on duty 📧s🔍🕵️🔎👀📝📝📄📄📜📃📑
                    updated_her_records = []
                    for msg in emailz:
                        her_log = await self.human_amended_review(msg)
                        if her_log:
                            updated_her_records.append(her_log)

                    # updated_her_records = await asyncio.gather(*filtering_tasks)
                    logger.info(f"HEREmailMonitor.start 👀📜 {updated_her_records=}")
                    await self.send_out_approved_and_amended(updated_her_records)
                except asyncio.TimeoutError:
                    logger.info("HER IDLE timeout, restarting...")
                    self.imap_client.idle_done()

        except asyncio.CancelledError:
            logger.info("HEREmailMonitor shutdown initiated...")
            # Perform any necessary cleanup here
            self.imap_client.idle_done()
            logger.info("Done ✅")
            return True
        except Exception as e:
            logger.exception(f"HEREmailMonitor.start 😖🤯 {e}")
            raise
        finally:
            await self.cleanup()

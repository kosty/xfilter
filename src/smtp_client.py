from aiosmtplib import SMTP
import aiosmtplib
import asyncio
import environment as env
from email.mime.text import MIMEText
from email.message import Message
from email.header import Header
from email.utils import formataddr
from .models import Email, HERLog
import logging
import backoff
from .store import BaseStore
from typing import Optional, Any

logger = logging.getLogger(__name__)

async def simply_print_out(msg: Email):
    try:
        # ('Reply-To', 'Arsen Kostenko <arsen@hosteasy.ai>'),
        # ('Sender', 'Google Calendar <calendar-notification@google.com>'),
        # ('Auto-Submitted', 'auto-generated'),
        # ('Message-ID', '<calendar-5398971c-86f4-42eb-88ef-291769d68e1e@google.com>'),
        # ('Date', 'Wed, 05 Jun 2024 20:02:35 +0000'),
        # ('Subject', 'Arsen Kostenko would like to view your calendar'),
        # ('From', 'Arsen Kostenko <arsen@hosteasy.ai>'),
        # ('To', 'arsen.kostenko@gmail.com'),
        logger.warning("inside simply_print_out")
        logger.warning(f"{msg.model_dump()}")
    except asyncio.CancelledError:
        logger.exception("I was cancel...")
    except Exception:
        logger.exception(f"Exception while processing {msg}...")
    finally:
        logger.info("finally closing the loop...")


logging.getLogger('backoff').addHandler(logging.StreamHandler())
logging.getLogger('backoff').setLevel(logging.ERROR)

@backoff.on_exception(backoff.expo, [aiosmtplib.errors.SMTPTimeoutError])
async def send_followup(msg: Email) -> Optional[Any]:
    #  to_email, from_email, from_email_password, subject, body, original_msg_id
    body = f"I want to warn you about\r\n\r\n{msg.body}\r\n\r\n👆have you seen that?"
    from_email = env.get("SMPT_USER")
    # Create MIMEText object for the email body
    # TODO there might be multiple recepients, and my email is just one of those
    #      need to check if `env.get("IMAP_USER")` is in `msg.recipients` ...
    #      or just hardcode IMAP_USER
    to_email = env.get("IMAP_USER") 
    message = MIMEText(body, 'plain', 'utf-8')
    sender = formataddr(("xFilter", from_email))
    message['From'] = sender
    message['To'] = to_email
    message['Subject'] = Header(msg.subject, 'utf-8')
    message['In-Reply-To'] = msg.id
    message['References'] = msg.id

    try:
        # TODO: for some reason without a dedicated session this call times out consistently
        result = await aiosmtplib.send(
            message.as_string(), 
            sender=sender, 
            recipients=[to_email],  
            hostname=env.get("SMPT_HOST"), 
            port=env.get_int("SMTP_POST"), # Use 465 for SSL and 587 for TLS
            username=env.get("SMPT_USER"), 
            password=env.get("SMPT_PASSWORD"), 
            timeout=60*3,
            use_tls=True
        )
        logger.debug(f"Success sending reply {result=}")
        return result
        # TODO: if you ever think of having a one SMPT session for bunch of outgoing emails try this
        # Create an SMTP client session
        # async with SMTP(hostname=env.get("SMPT_HOST"), port=smtp_port, username=env.get("IMAP_USER"), password=env.get("IMAP_PASSWORD"), use_tls=True) as smtp:
        #     # # Start TLS for security
        #     # await smtp.starttls()
        #     # Login to the SMTP server
        #     # await smtp.login(from_email, from_email_password)
        #     # Send the email
        #     await smtp.sendmail(from_email, [to_email], message.as_string())
        #     app.logger.info("Reply sent successfully!")
    except aiosmtplib.SMTPException as e:
        logger.exception(f"Failed sending email {e}")
        return None
    except asyncio.CancelledError:
        logger.exception("It was cancel...")
    except BaseException as e:
        logger.exception(f"Exception {e} while processing {msg}...")
        raise
    finally:
        logger.info("finally closing the loop...")


@backoff.on_exception(backoff.expo, [aiosmtplib.errors.SMTPTimeoutError])
async def send_reply(msg: Email, reply_text:str) -> Optional[Any]:
    '''Reply directly to sender of this email'''
    #  to_email, from_email, from_email_password, subject, body, original_msg_id
    from_email = env.get("SMPT_USER")
    # Create MIMEText object for the email body
    to_email = msg.sender
    message = MIMEText(reply_text, 'plain', 'utf-8')
    sender = formataddr(("xFilter", from_email))
    message['From'] = sender
    message['To'] = to_email
    message['Subject'] = Header(msg.subject, 'utf-8')
    message['In-Reply-To'] = msg.id
    message['References'] = msg.id

    try:
        # TODO: for some reason without a dedicated session this call times out consistently
        result = await aiosmtplib.send(
            message.as_string(), 
            sender=sender, 
            recipients=[to_email],  
            hostname=env.get("SMPT_HOST"), 
            port=env.get_int("SMTP_POST"), # Use 465 for SSL and 587 for TLS
            username=env.get("SMPT_USER"), 
            password=env.get("SMPT_PASSWORD"), 
            timeout=60*3,
            use_tls=True
        )
        logger.debug(f"Success sending reply {result=}")
        return result
        # TODO: if you ever think of having a one SMPT session for bunch of outgoing emails try this
        # Create an SMTP client session
        # async with SMTP(hostname=env.get("SMPT_HOST"), port=smtp_port, username=env.get("IMAP_USER"), password=env.get("IMAP_PASSWORD"), use_tls=True) as smtp:
        #     # # Start TLS for security
        #     # await smtp.starttls()
        #     # Login to the SMTP server
        #     # await smtp.login(from_email, from_email_password)
        #     # Send the email
        #     await smtp.sendmail(from_email, [to_email], message.as_string())
        #     app.logger.info("Reply sent successfully!")
    except aiosmtplib.SMTPException as e:
        logger.exception(f"Failed sending email {e}")
        return None
    except asyncio.CancelledError:
        logger.exception("It was cancel...")
    except BaseException as e:
        logger.exception(f"Exception {e} while processing {msg}...")
        raise
    finally:
        logger.info("finally closing the loop...")


@backoff.on_exception(backoff.expo, [aiosmtplib.errors.SMTPTimeoutError])
async def send_her_emails(msg: Email, her_log: HERLog) -> Optional[Any]:
    #  to_email, from_email, from_email_password, subject, body, original_msg_id
    body = f"Please accept or amend the following message 👇\r\nJust reply to this email with textual consent or denial. If you have a better wording add it at line #3 or your email.\r\n\r\n{her_log.proposed}\r\n\r\nThis was generated in response to\r\n\r\n{msg.body}"
    from_email = env.get("HER_SMPT_USER")
    # Create MIMEText object for the email body

    message = MIMEText(body, 'plain', 'utf-8')
    sender = formataddr(("xFilter review", from_email))
    message['From'] = sender
    message['To'] = ','.join(her_log.outbound)
    message['Subject'] = Header(f"[{her_log.id}] Please review the following communication", 'utf-8')
    message['X-Human-Empowered-Review-ID'] = her_log.id
    message['In-Reply-To'] = her_log.id
    message['References'] = her_log.id

    try:
        
        # TODO: for some reason without a dedicated session this call times out consistently
        result = await aiosmtplib.send(
            message.as_string(), 
            sender=sender, 
            recipients=her_log.outbound,  
            hostname=env.get("HER_SMPT_HOST"), 
            port=env.get_int("HER_SMTP_POST"), # Use 465 for SSL and 587 for TLS
            username=env.get("HER_SMPT_USER"), 
            password=env.get("HER_SMPT_PASSWORD"), 
            timeout=60*3,
            use_tls=True
        )
        logger.debug(f"Success sending reply {result=}")
        return result
        # TODO: if you ever think of having a one SMPT session for bunch of outgoing emails try this
        # Create an SMTP client session
        # async with SMTP(hostname=env.get("SMPT_HOST"), port=smtp_port, username=env.get("IMAP_USER"), password=env.get("IMAP_PASSWORD"), use_tls=True) as smtp:
        #     # # Start TLS for security
        #     # await smtp.starttls()
        #     # Login to the SMTP server
        #     # await smtp.login(from_email, from_email_password)
        #     # Send the email
        #     await smtp.sendmail(from_email, [to_email], message.as_string())
        #     app.logger.info("Reply sent successfully!")
    except aiosmtplib.SMTPException as e:
        logger.exception(f"Failed sending email {e}")
        return None
    except asyncio.CancelledError:
        logger.exception("It was cancel...")
        return None
    except BaseException as e:
        logger.exception(f"Exception {e} while processing {msg}...")
        raise
    finally:
        logger.info("finally clause")

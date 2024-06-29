# import pytest
# from imap_client import extract_current_email_content

# def test_extract_current_email_content():
#     content="""Please Approve/Reject the response from Alfred as shown below:-
# Guest Message: 
# Alfreds Response: It seems like you haven't asked a question yet. How can I assist you today?

# Reply "Yes" to APPROVE or "No" to REJECT
# """
#     assert extract_current_email_content(content) == content

import asyncio
import aioimaplib
import environment as env

HOST = env.get("HER_IMAP_HOST")
PORT = env.get_int("HER_IMAP_PORT")
USERNAME = env.get("HER_IMAP_USER")
PASSWORD = env.get("HER_IMAP_PASSWORD") 

# async def check_mailbox(client_id):
#     imap_client_0 = aioimaplib.IMAP4_SSL(host=HOST, port=993)
#     imap_client_1 = aioimaplib.IMAP4_SSL(host=HOST, port=993)
#     await imap_client_0.wait_hello_from_server()
#     await imap_client_1.wait_hello_from_server()

#     # Login to the server
#     await imap_client_0.login(USERNAME, PASSWORD)
#     print(f"Client {client_id}.0 logged in")
#     await imap_client_1.login(USERNAME, PASSWORD)
#     print(f"Client {client_id}.1 logged in")

#     # Select the inbox
#     await imap_client_0.select('INBOX')
#     print(f"Client {client_id}.0 selected INBOX")
#     await imap_client_1.select('INBOX')
#     print(f"Client {client_id}.1 selected INBOX")

#     # Start IDLE mode
#     await imap_client_0.idle_start(timeout=10)
#     print(f"Client {client_id}.0 started IDLE")
#     await imap_client_1.idle_start(timeout=10)
#     print(f"Client {client_id}.1 started IDLE")

#     # Wait for server responses
#     try:
#         responses0 = await imap_client_0.wait_server_push(timeout=600)
#         print(f"Client {client_id}.0 received server push: {responses0}")
#         responses1 = await imap_client_1.wait_server_push(timeout=600)
#         print(f"Client {client_id}.1 received server push: {responses1}")
#     except asyncio.TimeoutError as e:
#         print(f"Client  IDLE timeout {e}")

#     # End IDLE mode
#     imap_client_0.idle_done()
#     print(f"Client {client_id}.0 ended IDLE")
#     imap_client_1.idle_done()
#     print(f"Client {client_id}.1 ended IDLE")

#     # Logout
#     await imap_client_0.logout()
#     print(f"Client {client_id}.0 logged out")
#     await imap_client_1.logout()
#     print(f"Client {client_id}.1 logged out")

# async def main():
#     # Create multiple client instances
#     await asyncio.gather(
#         check_mailbox(client_id=1),
#         check_mailbox(client_id=2)
#     )

# if __name__ == '__main__':
#     asyncio.run(main())

SENDER_EMAIL="arsen@hosteasy.ai"

async def check_mailbox(client_id):
    imap_client = aioimaplib.IMAP4_SSL(host=HOST, port=993)
    await imap_client.wait_hello_from_server()

    # Login to the server
    await imap_client.login(USERNAME, PASSWORD)
    print(f"Client {client_id} logged in")

    # Select the inbox
    await imap_client.select('INBOX')
    print(f"Client {client_id} selected INBOX")

    try:
        while True:
            try:
                # Start IDLE mode
                await imap_client.idle_start(timeout=10)
                print(f"Client {client_id} started IDLE")

                # Wait for server responses
                responses = await imap_client.wait_server_push(timeout=600)
                print(f"Client {client_id} received server push: {responses}")

                # End IDLE mode
                imap_client.idle_done()
                print(f"Client {client_id} ended IDLE")

                # Search for emails from a specific sender
                result, data = await imap_client.search(f'(FROM "{SENDER_EMAIL}")')
                print(f"Client {client_id} found emails from {SENDER_EMAIL}: {result=} {data=}")
                if result == 'OK' and data[0]:
                    email_ids = data[0].split()
                    print(f"Client {client_id} found emails from {SENDER_EMAIL}: {email_ids}")

                    # Fetch and print the subject of each email
                    for email_id in email_ids:
                        email_id_str = email_id.decode()  # Ensure email_id is a string
                        result, data = await imap_client.fetch(email_id_str, '(BODY[HEADER.FIELDS (SUBJECT)])')
                        print(f"Client {client_id} fetched emails from {SENDER_EMAIL}: {result=}")
                        if result == 'OK':
                            subject = data[1]
                            print(f"Client {client_id} Email ID {email_id_str}: {subject.decode()=}")

            except asyncio.TimeoutError:
                print(f"Client {client_id} IDLE timeout, restarting...")
                await imap_client.idle_done()

    finally:
        await imap_client.logout()
        print(f"Client {client_id} logged out")

async def main():
    # Create multiple client instances
    await asyncio.gather(
        check_mailbox(client_id=1),
        check_mailbox(client_id=2)
    )

if __name__ == '__main__':
    asyncio.run(main())
# from imap_client import extract_current_email_content
from llms import GenericLLMCall
import environment as env
import asyncio
import openai
from store import SQLiteStore
from models import Email, HERLog
from pydantic import EmailStr
from smtp_client import send_her_emails
import datetime

emailz = [
    'Arsen, I will compromise with you again, the last time on this topic. I\r\npropose a revised schedule for the alternating weekends: pick up on\r\nThursday instead of Friday, and then the children can stay with you through\r\nSunday, with you bringing them back to school on Monday. This is fulfilling\r\nyour 30% request and is a further compromise from me.\r\n\r\nPlease let Valerie know your acceptance so she can update the stipulation\r\nand order, and we can sign prior to the next mediation, as you requested.\r\n\r\nBest regards,\r\nLana\r\n\r\nOn Wed, Jun 19, 2024 at 7:47\u202fAM Arsen Kostenko <arsen.kostenko@gmail.com>\r\nwrote:\r\n\r\n> Lana, what do you say?\r\n>\r\n> Arsen\r\n>\r\n> On Wed, Jun 19, 2024 at 06:30 valerie tarvin <vtarvin@mac.com> wrote:\r\n>\r\n>> When attorneys join, I have a different protocol where they talk to me\r\n>> first, then I meet with each partner and their attorney individually.\r\n>> Please give me the names of your attorneys.\r\n>> It takes more time to schedule 4 people because of the respective\r\n>> calendars but I certainly am not against it, especially when it helps us\r\n>> solve disputes.\r\n>>\r\n>>\r\n>>\r\n>> Valerie Tarvin\r\n>> 3015 Yucca Avenue\r\n>> <https://www.google.com/maps/search/3015+Yucca+Avenue+San+Jose,+CA+95124?entry=gmail&source=g>\r\n>> San Jose, CA 95124\r\n>> <https://www.google.com/maps/search/3015+Yucca+Avenue+San+Jose,+CA+95124?entry=gmail&source=g>\r\n>>\r\n>> (408)380-4410 | (408)440-0249\r\n>>\r\n>> On Jun 19, 2024, at 12:29 AM, Arsen Kostenko <arsen.kostenko@gmail.com>\r\n>> wrote:\r\n>>\r\n>> \ufeff\r\n>>\r\n>> Lana, as mentioned during our mediation, I am willing to have kids with\r\n>> me at least 30% of the time. Can we agree on this? If Wednesday overnight\r\n>> does not work, please propose a suitable schedule.\r\n>>\r\n>> I would really like to have this behind us before next mediation.\r\n>>\r\n>> Also, I sincerely believe things could move faster if we have attorneys\r\n>> speaking directly.\r\n>>\r\n>> Valerie, would you be open to having our representative join the call?\r\n>>\r\n>> Lana would you be open to having your attorney along with you for next\r\n>> mediation?\r\n>>\r\n>> Arsen\r\n>>\r\n>> On Tue, Jun 18, 2024 at 11:03\u202fAM Lana Kostenko <lankakos@gmail.com>\r\n>> wrote:\r\n>>\r\n>>> Arsen, I am trying to accommodate your request as much as possible.\r\n>>> Wednesday dinner just on its own is already something I compromised on as\r\n>>> it is disruptive, will prevent some of the extra curricular activities that\r\n>>> we would have to schedule for a different day. This is a compromise, I give\r\n>>> this to you. Do you want it?\r\n>>>\r\n>>> Also, anything can be agreed to in writing if we have good communication\r\n>>> between two of us which I hope we will get as yesterday’s mediation gave me\r\n>>> hope we can continue communicating and agreeing to things in a nice manner\r\n>>> as friends and co parents. I would like to keep this going!\r\n>>>\r\n>>> *Lana A*\r\n>>>\r\n>>> T: +1 (650) 283-0150\r\n>>>\r\n>>> On Tue, Jun 18 2024 at 09:46, Arsen Kostenko <arsen.kostenko@gmail.com>\r\n>>> wrote:\r\n>>>\r\n>>>> I kindly disagree. Especially with "other house" formulation. Generally\r\n>>>> let me remind you that you are the one who insisted on a 50/50 time split.\r\n>>>>\r\n>>>> Arsen\r\n>>>>\r\n>>>> On Tue, Jun 18, 2024 at 9:42\u202fAM Lana Kostenko <lankakos@gmail.com>\r\n>>>> wrote:\r\n>>>>\r\n>>>>> We can always agree to things in writing and make exceptions. But\r\n>>>>> having kids overnight at the other house in the middle of the school week\r\n>>>>> overnight will create logistical difficulties and will be disruptive to\r\n>>>>> children. I hope this makes sense.\r\n>>>>>\r\n>>>>> *Lana A*\r\n>>>>>\r\n>>>>> T: +1 (650) 283-0150\r\n>>>>>\r\n>>>>> On Tue, Jun 18 2024 at 09:16, Arsen Kostenko <arsen.kostenko@gmail.com>\r\n>>>>> wrote:\r\n>>>>>\r\n>>>>>> Dear Valerie,\r\n>>>>>> Dear Lana,\r\n>>>>>>\r\n>>>>>>\r\n>>>>>> Could Wednesday be an overnight visit? I ran this by my attorney and\r\n>>>>>> they mentioned it is under 30% previously agreed upon.\r\n>>>>>>\r\n>>>>>> Open to any other suggestions by Lana.\r\n>>>>>>\r\n>>>>>> Arsen\r\n>>>>>>\r\n>>>>>> On Tue, Jun 18, 2024 at 08:08 Lana <lankakos@gmail.com> wrote:\r\n>>>>>>\r\n>>>>>>> Signed by me\r\n>>>>>>>\r\n>>>>>>> Thanks both\r\n>>>>>>>\r\n>>>>>>> On Mon, Jun 17, 2024 at 4:44\u202fPM valerie tarvin <vtarvin@mac.com>\r\n>>>>>>> wrote:\r\n>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>>\r\n>>>>>>>> Valerie Tarvin\r\n>>>>>>>> 3015 Yucca Avenue\r\n>>>>>>>> <https://www.google.com/maps/search/3015+Yucca+Avenue+San+Jose,+CA+95124?entry=gmail&source=g>\r\n>>>>>>>> San Jose, CA 95124\r\n>>>>>>>> <https://www.google.com/maps/search/3015+Yucca+Avenue+San+Jose,+CA+95124?entry=gmail&source=g>\r\n>>>>>>>>\r\n>>>>>>>> (408)380-4410 | (408)440-0249\r\n>>>>>>>>\r\n>>>>>>>\r\n>>>>>>>\r\n>>>>>>> --\r\n>>>>>>>\r\n>>>>>>> *Lana A*\r\n>>>>>>>\r\n>>>>>>> T: +1 (650) 283-0150\r\n>>>>>>>\r\n>>>>>>\r\n\r\n-- \r\n\r\n*Lana A.*\r\n\r\nT: +1 (650) 283-0150\r\n\r\n<https://www.linkedin.com/in/lanaarseienko/>\r\n',
    "Thanks, Ryan! All clear now.\r\n\r\n*Lana Kostenko*\r\n\r\nT: +1 (650) 283-0150\r\n\r\nE: lankakos@gmail.com\r\n\r\nOn Sun, Jun 2 2024 at 17:04, Ryan James < rjames@ymcaeastbay.org > wrote:\r\n\r\n> \r\n> \r\n> \r\n> Hi Lana,\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> Sorry for the delay on that.\xa0 We’ve been hosting staff training the last\r\n> week and I am just now getting this out.\xa0 If you did not receive the email\r\n> I just sent please let me know.\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> Cheers!\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> *Ryan James*\r\n> \r\n> \r\n> \r\n> *Executive Director of Camping* **\r\n> \r\n> \r\n> \r\n> CAMP LOMA MAR\r\n> \r\n> \r\n> \r\n> YMCA OF THE EAST BAY\r\n> \r\n> \r\n> \r\n> 9900 Pescadero Creek Road, Loma Mar, CA 94021\r\n> \r\n> \r\n> \r\n> *P* 650.879.1856 *E* rjames@ymcaeastbay.org ( rjames@ymcaeastbay.org )\r\n> \r\n> \r\n> \r\n> *W* camplomamar.org\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> *To Empower Youth, Advance Health, and Strengthen Communities.*\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> *From:* Lana Kostenko <lankakos@gmail.com>\r\n> *Sent:* Sunday, June 2, 2024 3:37 PM\r\n> *To:* Ryan James <rjames@ymcaeastbay.org>\r\n> *Cc:* Cassie Brimmage <cbrimmage@ymcaeastbay.org>; Eli Cardenas\r\n> <ecardenas@ymcaeastbay.org>; Arsen Kostenko <arsen.kostenko@gmail.com>\r\n> *Subject:* Re: Camp Loma Mar February Update!\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> You don't often get email from lankakos@gmail.com. Learn why this is\r\n> important ( https://aka.ms/LearnAboutSenderIdentification )\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> *Caution:* This message is from outside our organization. Do not click on\r\n> links or open attachments unless you recognize the sender's email address\r\n> and know the content is safe.\r\n> \r\n> \r\n> \r\n> Hey Ryan and Cassie!\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> Hope you're doing well. I just wanted to reach out and check in about camp\r\n> details for week 1 of summer 2024. We haven't received any information\r\n> about the schedule or any instructions for that week. Could you please\r\n> fill us in on those details?\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> Also, we would like to know the ways to pay the remaining fee for camp. If\r\n> you could provide us with the necessary information, that would be great.\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> Thanks in advance for your help!\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> *Lana Kostenko*\r\n> \r\n> \r\n> \r\n> T: +1 (650) 283-0150\r\n> \r\n> \r\n> \r\n> E: lankakos@gmail.com\r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> \r\n> On Wed, Feb 7 2024 at 22:01, Ryan James < rjames@ymcaeastbay.org > wrote:\r\n> \r\n> \r\n>> \r\n>> \r\n>> Hello Camper Families!\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> We are so excited for summer camp 2024!\xa0 If you are included on this email\r\n>> that means you have a camper(s) registered for summer 2024.\xa0 Whether you\r\n>> are a returning family or new addition to Camp Loma Mar, we are ecstatic\r\n>> your camper is joining us.\xa0 The trust you put in our team here at camp\r\n>> means so much.\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> Summer 2024 is shaping up to be Camp Loma Mar’s largest summer on record\r\n>> with several of our programs already starting to fill up.\xa0 To meet the\r\n>> need of our growing camper population, we are actively recruiting and\r\n>> hiring the best camp counselors.\xa0 So far, we have 10 international camp\r\n>> counselors representing 6 countries and 30 American camp counselors\r\n>> representing 12 different states.\xa0 We are hoping to start introducing\r\n>> staff on our social media pages in the coming weeks.\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> A quick weather update… Much like the rest of California, camp saw some\r\n>> intense weather patterns to kick off February.\xa0 Luckily, none of our\r\n>> buildings at camp sustained any damage.\xa0 However, we did see a large oak\r\n>> tree fall over, the trail to Big Red wash out, and a lot of debris\r\n>> everywhere.\xa0 We’ve been running on backup generator power since Sunday and\r\n>> are anticipating power to be restored by Friday.\xa0 Check out our Instagram\r\n>> (@camplomamar) or Facebook (YMCA Camp Loma Mar) for pictures and\r\n>> additional updates.\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> As always, if you have any questions leading up to camp please feel free\r\n>> to reach out to myself or Cassie.\xa0 We are always happy to chat camp.\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> Cheers!\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> Ryan and Cassie\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> *Ryan James*\r\n>> \r\n>> \r\n>> \r\n>> *Executive Director of Camping*\r\n>> \r\n>> \r\n>> \r\n>> CAMP LOMA MAR\r\n>> \r\n>> \r\n>> \r\n>> YMCA OF THE EAST BAY\r\n>> \r\n>> \r\n>> \r\n>> 9900 Pescadero Creek Road, Loma Mar, CA 94021\r\n>> \r\n>> \r\n>> \r\n>> *P* 650.879.1856 *E* rjames@ymcaeastbay.org ( rjames@ymcaeastbay.org )\r\n>> \r\n>> \r\n>> \r\n>> *W* camplomamar.org\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> *To Empower Youth, Advance Health, and Strengthen Communities.*\r\n>> \r\n>> \r\n>> \r\n> \r\n>",
    "Hi Valerie, hi Arsen,\r\n\r\nValerie, I have just sent you my half of the payment - $3,140 - through Zelle.\r\n\r\nThanks both.\r\n\r\n*Lana Kostenko*\r\n\r\nT: +1 (650) 283-0150\r\n\r\nE: lankakos@gmail.com\r\n\r\nOn Mon, Jun 03, 2024 at 10:15 PM, Arsen Kostenko < arsen.kostenko@gmail.com > wrote:\r\n\r\n> \r\n> Dear Valerie,\r\n> \r\n> \r\n> I'm a bit confused. The previous invoice was for $5.800 and we have had at\r\n> least one mediation since.\r\n> \r\n> \r\n> Why is the amount lower this time around?\r\n> \r\n> \r\n> \r\n> Arsen\r\n> \r\n> \r\n> On Mon, Jun 3, 2024 at 11:14\u202fAM valerie tarvin < vtarvin@ mac. com (\r\n> vtarvin@mac.com ) > wrote:\r\n> \r\n> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> Valerie Tarvin\r\n>> 3015 Yucca Avenue\r\n>> San Jose, CA 95124\r\n>> (408)380-4410 | (408)440-0249\r\n>> \r\n>> Begin forwarded message:\r\n>> \r\n>> \r\n>> \r\n>>> *From:* tarv9790@ gmail. com ( tarv9790@gmail.com )\r\n>>> *Date:* June 3, 2024 at 11:12:36 AM PDT\r\n>>> *To:* Valerie Tarvin < vtarvin@ mac. com ( vtarvin@mac.com ) >\r\n>>> *Subject:* *Scanned from a Xerox multifunction device*\r\n>>> *Reply-To:* tarv9790@ gmail. com ( tarv9790@gmail.com )\r\n>>> \r\n>>> \r\n>>> \r\n>> \r\n>> \r\n>>> \ufeff\r\n>>> \r\n>>> Please open the attached document. It was sent to you using a Xerox\r\n>>> multifunction printer.\r\n>>> \r\n>>> Attachment File Type: pdf, Multi-Page\r\n>>> \r\n>>> Multifunction Printer Location:\r\n>>> Multifunction Printer Name: Xerox 7830\r\n>>> \r\n>>> \r\n>>> For more information on Xerox products and solutions, please visit http:/ /\r\n>>> www. xerox. com ( http://www.xerox.com )\r\n>>> \r\n>> \r\n>> \r\n> \r\n>",
    'Arsen, would 17th and 25th work for you?\r\n\r\n*Lana A*\r\n\r\nT: +1 (650) 283-0150\r\n\r\nOn Mon, Jun 10, 2024 at 10:43 AM, Lana < lankakos@gmail.com > wrote:\r\n\r\n> \r\n> June 17th works for me. What about you, Arsen?\r\n> \r\n> \r\n> Should we book both of them in?\r\n> \r\n> On Mon, Jun 10, 2024 at 9:54\u202fAM valerie tarvin < vtarvin@ mac. com (\r\n> vtarvin@mac.com ) > wrote:\r\n> \r\n> \r\n>> Good Morning,\r\n>> I have these dates available at this time, if these do not work, I’ll find\r\n>> more dates for you:\r\n>> 6/17 at 9 am\r\n>> 6/25 at 9 am.\r\n>> Valerie\r\n>> \r\n>> \r\n>> \r\n>> \r\n>> \r\n>> Valerie Tarvin\r\n>> 3015 Yucca Avenue\r\n>> San Jose, CA 95124\r\n>> (408)380-4410 | (408)440-0249\r\n>> \r\n> \r\n> \r\n> \r\n> \r\n> --\r\n> \r\n> \r\n> *Lana A*\r\n> \r\n> \r\n> \r\n> T: +1 (650) 283-0150\r\n> \r\n> \r\n>'
]

msg = Email(
    id="    id: str"+str(datetime.datetime.now()),
    sender="aaa@bbb.com",
    recipients=["bbb@ccc.com"],
    subject="subject",
    body="body",
    sent_at=datetime.datetime.now())
# async def send():
#     her_log = HERLog(entity="email", entity_id=msg.id, outbound=["arsen+her0@volia.fund", "arsen+her1@volia.fund"], proposed="some random text")
#     result = await send_her_emails(msg, her_log)
#     print(f"{result}")
#     print(f"{result[0]}, {result[1]}")

import aioimaplib
import email
msg_id = "<667da6c0.050a0220.1a7a6.59de@mx.google.com>"
async def lookup():
    
    IMAP_PORT = 993
    user = env.get("IMAP_USER")
    pwd = env.get("IMAP_PASSWORD") 
    imap_client = aioimaplib.IMAP4_SSL(host=env.get("IMAP_HOST") , port=IMAP_PORT)
    await imap_client.wait_hello_from_server()

    # Login to the server
    await imap_client.login(user, pwd)
    
    # Select the inbox
    result, data = await imap_client.select('"[Gmail]/Sent Mail"')
    if result != 'OK':
        print(f"Failed to select mailbox {result} / {data}")
        await imap_client.logout()
        return
    
    # # Wait for server responses
    # await imap_client.wait_server_push(timeout=60)
    
    # # List all folders
    # status, folders = await imap_client.list('""', '*')

    # if status == 'OK':
    #     print("Folders:")
    #     for folder in folders:
    #         print(folder.decode())
    # else:
    #     print("Failed to retrieve folders")


    # Search for emails from a specific sender
    result, data = await imap_client.search(f"HEADER Message-ID {msg_id}")
    emailz = []
    if result == 'OK' and data[0]:
        email_ids = data[0].split()
        try:
            # Apparently this part HAS to be sequential... is it protocol ?
            for binary_email_id in email_ids:
                email_id = binary_email_id.decode()
                result, data = await imap_client.fetch(email_id, 'RFC822')
                msg = email.message_from_bytes(data[1])
                print(msg)
        except Exception as e:
            print(f"Something happened here! {e}")
    await imap_client.logout()
    
    


# async def store():
#     store = SQLiteStore()
#     await store.initialize_db()
#     await store.add_email(msg)
#     res = await store.list_all()
#     for r in res:
#         print(r)


# async def ask():
#     for e in emailz:
#         llm_client = openai.AsyncOpenAI()
#         llm_call = GenericLLMCall(llm_client)
#         answer = await llm_call.ask_llm(text=e)
#         print(answer)
#         print("-----------------------------------\n\n")


if __name__ == "__main__":
    # asyncio.run(ask())
    asyncio.run(lookup())
    
import asyncio
import aioimaplib
import environment as env
from quart import Quart, request, jsonify


app = Quart(__name__)

HOST = env.get("IMAP_HOST")
IMAP_PORT = 993
USERNAME = env.get("IMAP_USER")
PASSWORD = env.get("IMAP_PASSWORD")
SENDER_EMAIL = 'arsen@hosteasy.ai'

@app.route('/api/')
async def hello_world():
    return jsonify({"message":"Hello, World!"}), 200


@app.before_serving
async def startup():
    app.background_task = asyncio.ensure_future(run_imap_client())


@app.after_serving
async def shutdown():
    app.background_task.cancel()  # Or use a variable in the while loop


async def run_imap_client():
    try:
        # Simulate a long-running email client task
        while True:
            print("IMAP client running...")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # print("IMAP client shutdown initiated.")
        # Perform any necessary cleanup here
        await asyncio.sleep(0.5)  # Simulate cleanup delay
        print("IMAP client has shut down.")


async def main():
    print("Before asyncio.gather")
    await app.run_task()


# Run the main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("__main__ | Shutting down...")
        # Cancel both tasks

        # Wait for both tasks to be cancelled
        print("__main__ | All tasks have been cancelled.")
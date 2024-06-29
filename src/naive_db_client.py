import environment as env
from store import SQLiteStore
import asyncio

S = SQLiteStore()

async def list_all(factory):
    l = await factory()
    for ent in l:
        print(f"{ent}")
    print("  =================  \n\n\n\n")

async def main():
    await list_all(S.list_all_emails)
        
    await list_all(S.list_all_her_logs)
        
    await list_all(S.list_all_completions)

if __name__ == "__main__":
    asyncio.run(main())
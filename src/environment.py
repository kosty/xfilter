from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv(".env"), override=True)

def get(key):
    return os.getenv(key)

def get_int(key):
    return int(get(key))

def get_as_csv_list(key: str) -> list[str]:
    val = os.getenv(key)
    if val and isinstance(val, str):
        return [ent.strip() for ent in val.split(",")]
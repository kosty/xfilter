import aiosqlite
import environment as env
from pathlib import Path
from .models import Email, Completion, HERLog, HERStatus
import json
from typing import List
import logging
from datetime import datetime
from pydantic import ValidationError
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

# aiosqlite performance and locking
# https://stackoverflow.com/questions/53908615/reusing-aiosqlite-connection

# copied from https://sqldocs.org/sqlite/aiosqlite-python/
#### data type converters
# import aiosqlite

# def converter(value):
#     # Convert from SQLite types to Python types
#     ...

# converter_func = aiosqlite.register_converter("CUSTOM", converter)

# db.set_type_translation(aiosqlite.PARSE_DECLTYPES)
# db.register_converter("CUSTOM", converter_func)

#### native data types
# import json
# import aiosqlite

# TABLE_DEF = """
# CREATE TABLE events (
#   id INTEGER PRIMARY KEY,
#   user_id TEXT,
#   name TEXT, 
#   properties BLOB,
#   timestamp DATETIME 
# )
# """

# async def insert_event(db, event_data):
#     """Insert a new event into the events table"""
#     sql = """INSERT INTO events 
#               (user_id, name, properties, timestamp)  
#               VALUES (?, ?, ?, ?)"""

#     await db.execute(sql, (
#        event_data['userId'],
#        event_data['name'],
#        json.dumps(event_data['properties']),
#        event_data['timestamp']
#     ))
#     await db.commit()
    
    
# async def main():  
#     async with aiosqlite.connect('analytics.db') as db:
#         await db.execute(TABLE_DEF)
        
#         event_data = {
#            'userId': '1234',
#            'name': 'search',
#            'properties': {'query': 'python'},    
#            'timestamp': '2023-01-01T12:00:00', 
#         }
        
#         await insert_event(db, event_data)


class BaseStore:
    
    async def initialize_db(self):
        pass
    
    async def add_email(self, value: Email):
        pass
    
    async def exists_email(self, id: str) -> bool:
        pass
    
    async def get_email(self, id: str) -> Optional[Email]:
        pass
    
    async def get_her_log(self, log_id: str) -> Optional[HERLog]:
        pass
    
    async def upsert_her_log(self, log: HERLog):
        pass
    
    async def add_completion(self, completion: Completion):
        pass
    
    async def get_completion(self, completion_id: str) -> Optional[Completion]:
        pass


class SQLiteStore(BaseStore):
    
    def __init__(self, db_path: str = None):
        str_path = db_path if db_path else env.get("DB_FILE_PATH")
        self.db_path = Path(str_path)
        self.lock = asyncio.Lock()
        self.initialized = False

    async def initialize_db(self):
       async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        CREATE TABLE IF NOT EXISTS emails (
                            id TEXT PRIMARY KEY,
                            sender TEXT,
                            subject TEXT,
                            recipients TEXT,
                            sent_at DATETIME,
                            body TEXT
                        )
                    ''')
                    await db.execute('''
                        CREATE TABLE IF NOT EXISTS completions (
                            id TEXT PRIMARY KEY,
                            entity TEXT,
                            entity_id TEXT,
                            llm_module TEXT,
                            created_at DATETIME,
                            llm_completion TEXT
                        )
                    ''')
                    await db.execute('''
                        CREATE TABLE IF NOT EXISTS her_logs (
                            id TEXT PRIMARY KEY,
                            entity TEXT,
                            entity_id TEXT,
                            outbound TEXT,
                            inbound TEXT,
                            status TEXT,
                            proposed TEXT,
                            amended TEXT,
                            created_at DATETIME,
                            inbound_at DATETIME
                        )
                    ''')
                    await db.commit()
                    self.initialized = True
                except aiosqlite.Error as e:
                    logger.exception(f"Failed to initialize db: {e}")
                    raise
                except Exception:
                    logger.exception(f"Failed to initialize db")
                    raise

    async def add_email(self, value: Email):
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        INSERT INTO emails (id, sender, subject, recipients, sent_at, body) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (value.id, value.sender, value.subject, ','.join(value.recipients), value.sent_at, value.body))
                    await db.commit()
                except aiosqlite.Error as e:
                    logger.exception(f"Failed to add email {value.model_dump()}: {e}")
                    raise
                except Exception:
                    logger.exception(f"Failed to add email {value.model_dump()}")
                    raise
                return True


    async def list_all_emails(self) -> List[Email]:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    async with db.execute('''SELECT * FROM emails''') as cursor:
                        # TODO: could this me a 
                        #       async for row in cursor.fetchall()
                        #           yield row ?
                        rows = await cursor.fetchall()
                        res = []
                        for row in rows:
                            res.append(Email(
                                id = row[0],
                                sender = row[1],
                                subject = row[2],
                                recipients = row[3].split(','),
                                sent_at = row[4],
                                body  = row[5]
                            ))
                        return res
                except aiosqlite.Error as e:
                    logger.exception(f"Failed to read all entries: {e}")
                    raise
                except Exception:
                    logger.exception(f"Failed to read all entries")
                    raise

            
    async def _do_exists(self, db, id) -> bool:
            async with db.execute('SELECT 1 FROM emails WHERE id = ?', (id,)) as cursor:
                return await cursor.fetchone() is not None

    async def exists_email(self, id: str) -> bool:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    return await self._do_exists(db, id)
                except aiosqlite.Error as e:
                    logger.exception(f"Failed check if {id} exists {e}")
                    raise
                except Exception:
                    logger.exception(f"Failed check if {id} exists")
                    raise


    async def _get_email(self, message_id: str) -> Email:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM emails WHERE id = ?', (message_id,))
                row = await cursor.fetchone()
                if row:
                    return Email(
                        id = row[0],
                        sender = row[1],
                        subject = row[2],
                        recipients = row[3].split(','),
                        sent_at = row[4],
                        body  = row[5]
                    )
                return None

     
    async def get_email(self, message_id: str) -> Optional[Email]:
        try:
            return await self._get_email(message_id)
        except aiosqlite.Error as e:
            logger.exception("Failed to read HERLog:", str(e))
            return None

    ##################### HERLog ########################
    async def _upsert_her_log(self, log: HERLog):
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
INSERT INTO her_logs (
    id, entity, entity_id, outbound, inbound, status, proposed,
    amended, created_at, inbound_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    entity=excluded.entity,
    entity_id=excluded.entity_id,
    outbound=excluded.outbound,
    inbound=excluded.inbound,
    status=excluded.status,
    proposed=excluded.proposed,
    amended=excluded.amended,
    created_at=excluded.created_at,
    inbound_at=excluded.inbound_at
                ''', (
                    log.id, log.entity, log.entity_id, 
                    json.dumps(log.outbound) if log.outbound else None, 
                    log.inbound, log.status.value, log.proposed,  log.amended, log.created_at.isoformat(), 
                    log.inbound_at.isoformat() if log.inbound_at else None
                ))
                await db.commit()


    async def upsert_her_log(self, log: HERLog):
        try:
            await self._upsert_her_log(log)
        except ValidationError as e:
            logger.exception(f"Validation error: {e.json()} ")
            raise
        except aiosqlite.Error as e:
            logger.exception("Database error:", str(e))
            raise


    async def _get_her_log(self, log_id: str) -> Optional[HERLog]:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM her_logs WHERE id = ?', (log_id,))
                row = await cursor.fetchone()
                if row:
                    return HERLog(
                        id=row[0],
                        entity=row[1],
                        entity_id=row[2],
                        outbound=json.loads(row[3]) if row[3] else None,
                        inbound=row[4],
                        status=HERStatus(row[5]),
                        proposed=row[6],
                        amended=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        inbound_at=datetime.fromisoformat(row[9]) if row[9] else None
                    )
                return None


    async def get_her_log(self, log_id: str) -> Optional[HERLog]:
        try:
            return await self._get_her_log(log_id)
        except aiosqlite.Error as e:
            logger.exception("Failed to read HERLog:", str(e))
            return None
        
    async def _list_all_her_logs(self) -> List[HERLog]:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM her_logs')
                rows = await cursor.fetchall()
                rez = []
                for row in rows:
                    rez.append(HERLog(
                        id=row[0],
                        entity=row[1],
                        entity_id=row[2],
                        outbound=json.loads(row[3]) if row[3] else None,
                        inbound=row[4],
                        status=HERStatus(row[5]),
                        proposed=row[6],
                        amended=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        inbound_at=datetime.fromisoformat(row[9]) if row[9] else None
                    ))
                return rez


    async def list_all_her_logs(self) -> List[HERLog]:
        try:
            return await self._list_all_her_logs()
        except aiosqlite.Error as e:
            logger.exception("Failed to list HERLogs:", str(e))
            return None

    ##################### Completion ########################
    async def _add_completion(self, completion: Completion):
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO completions (
                        id, entity, entity_id, llm_module, created_at, llm_completion
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    completion.id, completion.entity, completion.entity_id, 
                    completion.llm_module, completion.created_at.isoformat(), 
                    completion.llm_completion
                ))
                await db.commit()

    async def _get_completion(self, completion_id: str) -> Optional[Completion]:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM completions WHERE id = ?', 
                                        (completion_id,))
                row = await cursor.fetchone()
                if row:
                    return Completion(
                        id=row[0],
                        entity=row[1],
                        entity_id=row[2],
                        llm_module=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        llm_completion=row[5]
                    )
                return None

    async def add_completion(self, completion: Completion):
        try:
            await self._add_completion(completion)
        except ValidationError as e:
            logger.exception("Validation error:", e.json())
        except aiosqlite.Error as e:
            logger.exception("Database error:", str(e))

    async def get_completion(self, completion_id: str) -> Optional[Completion]:
        try:
            return await self._get_completion(completion_id)
        except aiosqlite.Error as e:
            logger.exception("Database error:", str(e))
            return None


    async def _list_all_completions(self) -> List[Completion]:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM completions')
                rows = await cursor.fetchall()
                rez = []
                for row in rows:
                    rez.append(Completion(
                        id=row[0],
                        entity=row[1],
                        entity_id=row[2],
                        llm_module=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        llm_completion=row[5]
                    ))
                return rez


    async def list_all_completions(self) -> List[HERLog]:
        try:
            return await self._list_all_completions()
        except aiosqlite.Error as e:
            logger.exception("Failed to list Completions:", str(e))
            return None

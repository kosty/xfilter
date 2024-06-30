from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from enum import Enum
from uuid import uuid4
from email.message import Message


class Email(BaseModel):
    id: str
    sender: EmailStr
    recipients: List[EmailStr]
    subject: str
    body: str
    sent_at: datetime
    reply_to: Optional[str] = None
    references: Optional[str] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    _msg: Optional[Message] = None #  TODO: for backporting old code only, remove at earliest convenience


class Completion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    llm_module: str
    created_at: datetime = Field(default_factory=datetime.now)
    llm_completion: str
    entity: Optional[str] = None
    entity_id: Optional[str] = None


class HERStatus(Enum):
    UNDEFINED = 'UNDEFINED'
    OUTBOUND = 'OUTBOUND'
    APPROVED = 'APPROVED'
    AMENDED = 'AMENDED'
    REJECTED = 'REJECTED'

             
class HERLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    entity: str
    entity_id: str
    outbound: Optional[List[str]] = None
    inbound: Optional[str] = None
    status: HERStatus = HERStatus.OUTBOUND
    proposed: str
    amended: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    inbound_at: Optional[datetime] = None
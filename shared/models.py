from typing import List, Optional
from uagents import Model


class Breach(Model):
    name: str
    domain: str = ""
    breach_date: str = ""
    data_classes: List[str] = []
    pwn_count: int = 0
    is_sensitive: bool = False


class ScanRequest(Model):
    request_id: str
    email: str


class BreachReport(Model):
    request_id: str
    email: str
    breaches: List[Breach] = []
    error: Optional[str] = None


class Account(Model):
    service: str
    domain: str = ""
    source: str = "breach"
    breach: Optional[Breach] = None


class TriageRequest(Model):
    request_id: str
    accounts: List[Account]


class TriagedAccount(Model):
    service: str
    domain: str = ""
    verdict: str
    reason: str
    score: int = 0


class TriageResult(Model):
    request_id: str
    items: List[TriagedAccount] = []
    error: Optional[str] = None


class EraseRequest(Model):
    request_id: str
    user_name: str
    user_email: str
    accounts: List[TriagedAccount]
    send: bool = False


class EraseAction(Model):
    service: str
    domain: str = ""
    method: str = "unknown"
    deletion_url: str = ""
    privacy_email: str = ""
    difficulty: str = ""
    note: str = ""
    letter: str = ""
    sent: bool = False
    error: str = ""


class EraseResult(Model):
    request_id: str
    actions: List[EraseAction] = []
    error: Optional[str] = None


class FollowUpTask(Model):
    request_id: str
    user_email: str
    user_name: str
    service: str
    contact: str
    sent_on: str
    due_on: str


class FollowUpAck(Model):
    request_id: str
    tracked: int

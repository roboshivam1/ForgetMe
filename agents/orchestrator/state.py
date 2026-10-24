import copy
import json

from shared.agentkit import new_id

EMPTY = {
    "state": "idle",
    "email": "",
    "name": "",
    "request_id": "",
    "breaches": [],
    "items": [],
    "selected": [],
    "actions": [],
}


def to_dict(model):
    dump = getattr(model, "model_dump", None)
    return dump() if dump else model.dict()


class Sessions:
    def __init__(self, storage):
        self.storage = storage

    def get(self, user):
        raw = self.storage.get(f"s:{user}")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = None
        session = copy.deepcopy(EMPTY)
        if isinstance(raw, dict):
            session.update(raw)
        return session

    def save(self, user, session):
        self.storage.set(f"s:{user}", session)

    def reset(self, user, keep_name=True):
        name = self.get(user).get("name", "") if keep_name else ""
        session = copy.deepcopy(EMPTY)
        session["name"] = name
        self.save(user, session)
        return session

    def start_request(self, user, session, state):
        request_id = new_id()
        session["request_id"] = request_id
        session["state"] = state
        self.save(user, session)
        self.storage.set(f"r:{request_id}", user)
        return request_id

    def user_for(self, request_id):
        return self.storage.get(f"r:{request_id}")

    def is_current(self, session, request_id):
        return session.get("request_id") == request_id

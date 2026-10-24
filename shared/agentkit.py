import uuid
from uagents import Agent
from shared.config import seed_for, port_for


def make_agent(key, name):
    return Agent(
        name=name,
        seed=seed_for(key),
        port=port_for(key),
        mailbox=True,
        publish_agent_details=True,
    )


def new_id():
    return uuid.uuid4().hex[:12]

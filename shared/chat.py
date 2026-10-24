from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
)


def text_message(text, end=False):
    content = [TextContent(type="text", text=text)]
    if end:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(content=content)


def ack_for(msg):
    return ChatAcknowledgement(acknowledged_msg_id=msg.msg_id)


def extract_text(msg):
    parts = [item.text for item in msg.content if isinstance(item, TextContent)]
    return " ".join(parts).strip()


def is_session_start(msg):
    return any(isinstance(item, StartSessionContent) for item in msg.content)

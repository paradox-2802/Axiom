from pydantic import BaseModel


class ChatCreate(BaseModel):
    chatId: str
    title: str | None = "New Chat"


class ChatMessageRequest(BaseModel):
    chatId: str
    message: str

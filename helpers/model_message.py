from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    username: str
    language_code: str


class Chat(BaseModel):
    id: int
    type: str


class Location(BaseModel):
    latitude: float
    longitude: float


# class Entity(BaseModel):
#     offset: int
#     length: int
#     type: str

class Message(BaseModel):
    message_id: int
    from_user: User
    chat: Chat
    date: int
    text: str
    location: Optional[Location] = None

#
#
# class UpdateMessage(BaseModel):
#     update_id: int
#     message: Message

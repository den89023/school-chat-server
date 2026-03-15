from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# Наше хранилище сообщений в оперативной памяти
chat_history = []

# Описываем твой JSON (твой уникальный формат)
class Message(BaseModel):
    d: str           # Уникальный ID
    nickname: str
    user_class: str
    text: str
    room: str
    is_premium: bool

@app.get("/")
def home():
    return {"status": "Server is running"}

# Деталь для отправки
@app.post("/send")
def send_message(msg: Message):
    data = msg.dict()
    data["time"] = datetime.now().strftime("%H:%M:%S")
    chat_history.append(data)
    
    # Чтобы сервер не тормозил, храним последние 20 сообщений
    if len(chat_history) > 20:
        chat_history.pop(0)
    
    return {"status": "ok"}

# Деталь для получения
@app.get("/get_messages")
def get_messages(room: str):
    # Возвращаем сообщения только для конкретной комнаты (класса)
    return [m for m in chat_history if m["room"] == room]
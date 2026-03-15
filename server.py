from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(
    title="School Chat Server",
    description="Backend for school chat application",
    version="1.0"
)

# CORS - разрешаем запросы с любых источников для приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация из переменных окружения
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "serrdtcxdxr%H^")
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "100"))

ICONS_DIR = os.path.join(UPLOAD_DIR, "icons")
MEDIA_DIR = os.path.join(UPLOAD_DIR, "media")

# Создаем директории если их нет
os.makedirs(ICONS_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# Хранилище сообщений в памяти
chat_history = []

# Модель сообщений
class Message(BaseModel):
    d: str           # Уникальный ID пользователя
    nickname: str
    user_class: str
    text: str
    room: str = "general"
    is_premium: bool = False

@app.get("/")
def home():
    return {"status": "Server is running", "version": "1.0"}

# ============================================
# ЧАТЫ И СООБЩЕНИЯ
# ============================================

@app.post("/send")
def send_message(msg: Message):
    """Отправить сообщение в чат"""
    data = msg.dict()
    data["time"] = datetime.now().strftime("%H:%M:%S")
    data["date"] = datetime.now().strftime("%d.%m.%Y")
    chat_history.append(data)
    
    # Храним последние N сообщений
    if len(chat_history) > MAX_MESSAGES:
        chat_history.pop(0)
    
    return {"status": "ok", "message_id": len(chat_history)}

@app.get("/get_messages")
def get_messages(room: str = "general"):
    """Получить все сообщения комнаты"""
    return [m for m in chat_history if m.get("room") == room]

@app.delete("/clear_messages")
def clear_messages(room: str = "general", password: str = None):
    """Очистить сообщения комнаты (нужен пароль админа)"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    global chat_history
    chat_history = [m for m in chat_history if m.get("room") != room]
    return {"status": "ok", "message": f"Комната {room} очищена"}

@app.delete("/clear_all_messages")
def clear_all_messages(password: str = None):
    """Полностью очистить все сообщения"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    global chat_history
    chat_history = []
    return {"status": "ok", "message": "Все сообщения удалены"}

# ============================================
# ЗАГРУЗКА ИКОНОК (аватарки профиля)
# ============================================

@app.post("/upload_icon")
async def upload_icon(user_id: str, file: UploadFile = File(...)):
    """Загрузить иконку профиля"""
    allowed_extensions = [".png", ".jpg", ".jpeg", ".ico", ".gif"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Поддерживаемые форматы: PNG, JPG, JPEG, ICO, GIF")
    
    try:
        filename = f"{user_id}{file_ext}"
        filepath = os.path.join(ICONS_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"status": "ok", "url": f"/icons/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")

@app.get("/icons/{filename}")
def get_icon(filename: str):
    """Получить иконку профиля"""
    filepath = os.path.join(ICONS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Иконка не найдена")
    
    return FileResponse(filepath)

@app.get("/default_icon")
def get_default_icon():
    """Получить базовую иконку (baza.ico)"""
    # Предполагаем, что baza.ico находится в корне сервера
    default_icon_path = "baza.ico"
    
    if os.path.exists(default_icon_path):
        return FileResponse(default_icon_path)
    else:
        return {"message": "Используйте встроенную иконку"}

# ============================================
# ЗАГРУЗКА МЕДИА (видео, аудио, фото)
# ============================================

@app.post("/upload_media")
async def upload_media(room: str, message_id: str, file: UploadFile = File(...)):
    """Загрузить медиа-файл в чат"""
    allowed_extensions = [".mp4", ".mp3", ".png", ".jpg", ".jpeg", ".gif", ".avi", ".mov", ".wav"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Поддерживаемые форматы: MP4, MP3, PNG, JPG, GIF, AVI, MOV, WAV")
    
    try:
        # Создаем подпапку для комнаты
        room_dir = os.path.join(MEDIA_DIR, room)
        os.makedirs(room_dir, exist_ok=True)
        
        # Сгенерируем уникальное имя
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{message_id}_{timestamp}{file_ext}"
        filepath = os.path.join(room_dir, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "ok",
            "url": f"/media/{room}/{filename}",
            "type": "video" if file_ext in [".mp4", ".avi", ".mov"] else ("audio" if file_ext in [".mp3", ".wav"] else "image")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")

@app.get("/media/{room}/{filename}")
def get_media(room: str, filename: str):
    """Получить медиа-файл"""
    filepath = os.path.join(MEDIA_DIR, room, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(filepath)

@app.get("/media_list")
def get_media_list(room: str):
    """Получить список всех медиа-файлов комнаты"""
    room_dir = os.path.join(MEDIA_DIR, room)
    
    if not os.path.exists(room_dir):
        return {"media": []}
    
    files = os.listdir(room_dir)
    return {"media": files, "room": room}

# ============================================
# СТАТИСТИКА
# ============================================

@app.get("/stats")
def get_stats():
    """Получить статистику сервера"""
    return {
        "total_messages": len(chat_history),
        "rooms": list(set([m.get("room") for m in chat_history])),
        "uploaded_icons": len(os.listdir(ICONS_DIR)) if os.path.exists(ICONS_DIR) else 0,
        "uploaded_media": len(os.listdir(MEDIA_DIR)) if os.path.exists(MEDIA_DIR) else 0,
    }

# ============================================
# УДАЛЕНИЕ ФАЙЛОВ
# ============================================

@app.delete("/delete_icon")
def delete_icon(user_id: str, password: str = None):
    """Удалить иконку пользователя"""
    # Пользователь может удалить только свою иконку или админ удалить любую
    # В реальном приложении здесь нужна проверка токена
    
    try:
        # Ищем файл иконки пользователя
        for file in os.listdir(ICONS_DIR):
            if file.startswith(user_id):
                filepath = os.path.join(ICONS_DIR, file)
                os.remove(filepath)
                return {"status": "ok", "message": "Иконка удалена"}
        
        return {"status": "not_found", "message": "Иконка не найдена"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления: {str(e)}")

@app.delete("/delete_media")
def delete_media(room: str, filename: str, password: str = None):
    """Удалить медиа-файл (только админ)"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    try:
        filepath = os.path.join(MEDIA_DIR, room, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"status": "ok", "message": "Файл удален"}
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления: {str(e)}")

# ============================================
# ЗДОРОВЬЕ СЕРВЕРА
# ============================================

@app.get("/health")
def health_check():
    """Проверка здоровья сервера"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message_count": len(chat_history)
    }

if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Запуск сервера на {SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"Директория загрузок: {UPLOAD_DIR}")
    logger.info(f"Максимум сообщений в памяти: {MAX_MESSAGES}")
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info"
    )

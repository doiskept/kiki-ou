import asyncio
import os
import logging
import threading
from flask import Flask, render_template_string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Імпорт вашого генератора (припускаємо, що файл називається image_utils.py)
import image_utils as pdf_utils

# Завантаження змінних
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBSITE = os.getenv("WEBSITE")

if not TOKEN:
    raise ValueError("BOT_TOKEN не встановлено! Перевірте змінні середовища.")

# Якщо змінна ADMIN_IDS не задана або порожня, краще додати обробку помилок
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip().isdigit()] if admin_ids_str else []

if not ADMIN_IDS:
    logging.warning("ADMIN_IDS не встановлено! Бот буде доступний всім.")

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER (FLASK) ---
app = Flask(__name__)

# HTML шаблон для головної сторінки
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Bot - Квитки</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .status {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            margin: 20px 0;
        }
        .status.active {
            background: #10b981;
            color: white;
        }
        .status.inactive {
            background: #ef4444;
            color: white;
        }
        p {
            color: #666;
            line-height: 1.6;
            margin: 15px 0;
        }
        .bot-link {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .bot-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎫 Telegram Bot</h1>
        <div class="status active">● Активний</div>
        <p>Бот для створення квитків працює у фоновому режимі.</p>
        <p>Використовуйте Telegram для взаємодії з ботом.</p>
        <a href="https://t.me/{{ bot_username }}" class="bot-link" target="_blank">
            Відкрити бота в Telegram
        </a>
        <div class="footer">
            <p>Сервер працює на Render</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Головна сторінка"""
    # Отримуємо username бота з токену або змінної середовища
    bot_username = os.getenv('BOT_USERNAME', 'your_bot')
    return render_template_string(HTML_TEMPLATE, bot_username=bot_username)

@app.route('/health')
def health():
    """Health check endpoint для Render"""
    return {'status': 'ok', 'bot': 'running'}, 200

@app.route('/ping')
def ping():
    """Ping endpoint для підтримки активності"""
    return {'status': 'pong'}, 200

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# --- ПАМ'ЯТЬ ДЛЯ PINNED MESSAGE (Тимчасова, в оперативці) ---
# Зберігає ID користувачів, які вже отримали закріплене повідомлення.
# При перезапуску бота список очиститься. Для постійного зберігання треба базу даних.
users_with_pinned_msg = set()

# Визначення станів
class TicketForm(StatesGroup):
    waiting_for_section = State()
    waiting_for_row = State()
    waiting_for_seat = State()
    confirmation = State()

# Дані про ціни та секції
SECTIONS_INFO = {
    "DANCE FLOOR": {"price": "459", "has_seat": False}, # Ціни краще числом або строкою без валюти, якщо генератор додає її сам
    "FAN ZONE": {"price": "504", "has_seat": False},
    "SECTOR 115": {"price": "351", "has_seat": True},
    "SECTOR 28": {"price": "351", "has_seat": True},
    "SECTOR 136": {"price": "351", "has_seat": True},
    "SECTOR 54": {"price": "351", "has_seat": True},
    "SECTOR 97": {"price": "351", "has_seat": True},
}

# --- МІДЛВАР (ПЕРЕВІРКА ДОСТУПУ) ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- КЛАВІАТУРИ ---
def get_main_menu():
    kb = [
        [KeyboardButton(text="🎫 Створити квиток")],
        [KeyboardButton(text="📂 Переглянути всі квитки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_sections_keyboard():
    buttons = []
    for section in SECTIONS_INFO.keys():
        buttons.append([InlineKeyboardButton(text=section, callback_data=f"sec_{section}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_admin(message.from_user.id):
        return 
    
    await message.answer("Привіт! Я бот для генерації квитків.", reply_markup=get_main_menu())
     # --- ЛОГІКА ЗАКРІПЛЕННЯ ПОВІДОМЛЕННЯ ---
            # Перевіряємо, чи ми вже надсилали цьому юзеру інструкцію
    if message.from_user.id not in users_with_pinned_msg:
        try:
                    sent_msg = await message.answer(
                        f"НЕ ПРАЦЮЄ? ПЕРЕЙДИ ЗА ПОСИЛАННЯМ - {WEBSITE}", 
                        disable_web_page_preview=True
                    )
                    
                    # Закріплюємо повідомлення
                    await bot.pin_chat_message(chat_id=message.from_user.id, message_id=sent_msg.message_id)
                    
                    # Додаємо юзера в список "оброблених"
                    users_with_pinned_msg.add(message.from_user.id)
                    
        except Exception as pin_error:
                    logging.error(f"Не вдалося закріпити повідомлення: {pin_error}")


@dp.message(F.text == "🎫 Створити квиток")
async def start_creation(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    
    await message.answer("Обери секцію:", reply_markup=get_sections_keyboard())
    await state.set_state(TicketForm.waiting_for_section)

@dp.callback_query(TicketForm.waiting_for_section, F.data.startswith("sec_"))
async def process_section(callback: types.CallbackQuery, state: FSMContext):
    section_name = callback.data.split("sec_")[1]
    sec_info = SECTIONS_INFO[section_name]
    
    # Зберігаємо вибрану секцію та автоматично ціну
    await state.update_data(section=section_name, price=sec_info['price'], has_seat=sec_info['has_seat'])
    
    if sec_info['has_seat']:
        await callback.message.answer(f"Вибрано: {section_name}. Ціна: {sec_info['price']}.\nВведіть РЯД (ROW):")
        await state.set_state(TicketForm.waiting_for_row)
    else:
        # Для фан-зони та танцполу пропускаємо ряд/місце
        await state.update_data(row=None, seat=None)
        await confirm_creation(callback.message, state)
    
    await callback.answer()

@dp.message(TicketForm.waiting_for_row)
async def process_row(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(row=message.text)
    await message.answer("Введіть МІСЦЕ (SEAT):")
    await state.set_state(TicketForm.waiting_for_seat)

@dp.message(TicketForm.waiting_for_seat)
async def process_seat(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(seat=message.text)
    await confirm_creation(message, state)

async def confirm_creation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = message.chat.id
    
    info_text = (
        f"🎟 <b>Перевірка даних:</b>\n"
        f"Секція: {data['section']}\n"
        f"Ціна: {data['price']}\n"
    )
    if data['row']:
        info_text += f"Ряд: {data['row']}\nМісце: {data['seat']}\n"
    
    info_text += "\nГенерую PDF..."
    await message.answer(info_text, parse_mode="HTML")
    
    # Виклик генератора
    try:
        # Припускаємо, що pdf_utils.edit_ticket_pdf повертає (шлях, номер)
        pdf_path, ticket_num = pdf_utils.edit_ticket_pdf(data)
        
        if pdf_path:
            ticket_file = FSInputFile(pdf_path)
            await message.answer_document(ticket_file, caption=f"Готово! Номер: {ticket_num}")
            
        else:
            await message.answer("Помилка: Не вдалося створити PDF (повернувся None).")
            
    except Exception as e:
        await message.answer(f"Сталася помилка при генерації: {e}")
        logging.error(e)

    await state.clear()
    await message.answer("Можемо створити ще один.", reply_markup=get_main_menu())

@dp.message(F.text == "📂 Переглянути всі квитки")
async def list_tickets(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    output_dir = "output"
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        await message.answer("Папка пуста.")
        return

    files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
    if not files:
        await message.answer("Квитків ще немає.")
        return

    await message.answer(f"Знайдено квитків: {len(files)}. Надсилаю останні 5...")
    
    # Сортуємо файли за часом створення (щоб точно брати останні)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)))

    # Надсилаємо останні 5 файлів
    for file_name in files[-5:]:
        file_path = os.path.join(output_dir, file_name)
        await message.answer_document(FSInputFile(file_path))

async def main():
    """Головна функція запуску бота"""
    try:
        logging.info("Бот запускається...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"Помилка при запуску бота: {e}", exc_info=True)
        raise

# Експортуємо для використання в web_server.py
__all__ = ['bot', 'dp', 'main']

if __name__ == "__main__":
    try:
        # Запускаємо веб-сервер у окремому потоці
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logging.info("Веб-сервер запущено у фоновому режимі")

        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот зупинено користувачем")
    except Exception as e:
        logging.error(f"Критична помилка: {e}", exc_info=True)
        raise

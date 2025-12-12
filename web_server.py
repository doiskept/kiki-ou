"""
Простий веб-сервер для запуску бота на Render Web Service
"""
from flask import Flask, render_template_string
import threading
import asyncio
import os
import logging

# Імпортуємо бота
from main import bot, dp, main as bot_main

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
        <a href="https://t.me/{bot_username}" class="bot-link" target="_blank">
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
    return render_template_string(HTML_TEMPLATE.format(bot_username=bot_username))

@app.route('/health')
def health():
    """Health check endpoint для Render"""
    return {'status': 'ok', 'bot': 'running'}, 200

@app.route('/ping')
def ping():
    """Ping endpoint для підтримки активності"""
    return {'status': 'pong'}, 200

def run_bot():
    """Запуск бота в окремому потоці"""
    if bot_main is None:
        logging.error("Бот не може бути імпортований!")
        return
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_main())
    except Exception as e:
        logging.error(f"Помилка запуску бота: {e}", exc_info=True)

if __name__ == '__main__':
    # Налаштування логування
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if bot_main is not None:
        # Запускаємо бота в окремому потоці
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logging.info("Бот запущено в фоновому режимі")
    else:
        logging.warning("Бот не запущено через помилки імпорту!")
    
    logging.info("Веб-сервер запускається...")
    
    # Запускаємо Flask сервер
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


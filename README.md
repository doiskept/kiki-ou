# Telegram Bot для створення квитків

Telegram бот для автоматичного створення та редагування PDF квитків з QR кодами.

## Деплой на Render

### Крок 1: Підготовка репозиторію
1. Завантажте код на GitHub/GitLab/Bitbucket
2. Переконайтеся, що всі файли включені в репозиторій

### Крок 2: Створення сервісу на Render
1. Зайдіть на [render.com](https://render.com)
2. Створіть новий "Background Worker"
3. Підключіть ваш репозиторій

### Крок 3: Налаштування
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Environment**: `Python 3`

### Крок 4: Змінні середовища
Додайте в налаштуваннях сервісу:
- `BOT_TOKEN` - токен вашого Telegram бота
- `ADMIN_IDS` - ID адмінів через кому (наприклад: `123456789,987654321`)

### Крок 5: Деплой
Натисніть "Deploy" і дочекайтеся завершення збірки.

## Локальний запуск

1. Встановіть залежності:
```bash
pip install -r requirements.txt
```

2. Створіть файл `.env`:
```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
```

3. Запустіть бота:
```bash
python main.py
```

## Структура проєкту

```
1/
├── .env                  # Токен та ID адмінів (не в git)
├── main.py              # Головний файл запуску
├── image_utils.py       # Логіка редагування PDF та QR
├── requirements.txt     # Залежності Python
├── render.yaml          # Конфігурація для Render
├── Procfile             # Команда запуску для Render
├── runtime.txt          # Версія Python
├── templates/           # Папка з шаблонами PDF
│   └── ticket_template.pdf
└── output/              # Папка куди зберігаються готові квитки
```

## Примітки

- Бот працює тільки для користувачів, вказаних в `ADMIN_IDS`
- Всі створені квитки зберігаються в директорії `output/`
- Номер квитка генерується випадково: 7264.0724.XXXX


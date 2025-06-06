# Tasks Telegram Bot

This bot helps Telegram channel administrators keep track of content tasks. It is built with **aiogram 3** and **SQLite** and is compatible with **Python 3.11**.

## Features

- Captures text posts from a channel (bot must be an administrator).
- Add tasks manually through a button based conversation.
- Assign workers and task type with inline buttons.
- View all tasks or only unassigned ones.
- Monthly statistics of completed tasks per worker.

## Installation

1. Install Python 3.11 and the dependencies:

```bash
pip install -r requirements.txt
```

2. Set the bot token as an environment variable:

```bash
export BOT_TOKEN=<your_bot_token>
```

(Optional) specify a different database file using the `DB_PATH` environment variable.

## Running

```bash
python bot.py
```

Add the bot to your channel as an administrator so it can read posts. Send `/start` in a private chat with the bot to open the menu. Use the buttons:

- **Add task** – create a new task by selecting its type and entering worker and title.
- **Unassigned** – list channel posts that are not yet assigned and quickly assign them.
- **Tasks** – show all stored tasks.
- **Stats** – enter a month (`YYYY-MM`) to see each worker's contribution.

# Tasks Telegram Bot

This repository contains a simple Telegram bot built with **aiogram** and
**SQLite** for managing tasks posted in a Telegram channel. It allows
administrators to keep track of posts, assign responsible workers and view
monthly statistics.

## Features

- Automatic capture of text posts from a channel where the bot is an admin.
- Manual task creation via command.
- Assign workers and task type to captured posts.
- Filter tasks by type, worker or month.
- Monthly statistics of completed tasks per worker.

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set the bot token as an environment variable:

```bash
export BOT_TOKEN=<your_bot_token>
```

Optional: change the database file location using `DB_PATH` environment
variable.

## Running

```bash
python bot.py
```

The bot must be added to your channel as an administrator to capture posts.
Use `/help` inside Telegram to list available commands.

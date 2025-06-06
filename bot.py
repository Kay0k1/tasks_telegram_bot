import os
import logging
from aiogram import Bot, Dispatcher, executor, types
import asyncio
from db import Database

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DB_PATH = os.getenv("DB_PATH", "bot.db")
db = Database(DB_PATH)

TASK_TYPES = ["news", "meme", "selection", "longread"]


async def on_startup(dp):
    await db.connect()


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply(
        "Task Manager Bot. Use /add_task, /unassigned, /assign, /tasks, /stats"
    )


@dp.channel_post_handler(content_types=types.ContentType.TEXT)
async def on_channel_post(message: types.Message):
    title = message.text.strip()
    await db.add_task(title=title, message_id=message.message_id, chat_id=message.chat.id)


@dp.message_handler(commands=["add_worker"])
async def cmd_add_worker(message: types.Message):
    parts = message.get_args().split()
    if not parts:
        await message.reply("Usage: /add_worker <name>")
        return
    worker_name = " ".join(parts)
    worker_id = await db.add_worker(worker_name)
    await message.reply(f"Worker {worker_name} has id {worker_id}")


@dp.message_handler(commands=["add_task"])
async def cmd_add_task(message: types.Message):
    args = message.get_args().split()
    if len(args) < 3:
        await message.reply("Usage: /add_task <type> <worker> <title>")
        return
    task_type, worker_name = args[0], args[1]
    title = " ".join(args[2:])
    if task_type not in TASK_TYPES:
        await message.reply(f"Unknown type. Available: {', '.join(TASK_TYPES)}")
        return
    task_id = await db.add_task(title, task_type, worker_name)
    await message.reply(f"Task #{task_id} added")


@dp.message_handler(commands=["unassigned"])
async def cmd_unassigned(message: types.Message):
    rows = await db.get_unassigned_tasks()
    if not rows:
        await message.reply("No unassigned posts")
        return
    text = "Unassigned posts:\n" + "\n".join(f"{r[0]}: {r[1][:40]}" for r in rows)
    await message.reply(text)


@dp.message_handler(commands=["assign"])
async def cmd_assign(message: types.Message):
    args = message.get_args().split()
    if len(args) < 3:
        await message.reply("Usage: /assign <task_id> <worker> <type>")
        return
    task_id = int(args[0])
    worker = args[1]
    task_type = args[2]
    if task_type not in TASK_TYPES:
        await message.reply(f"Type must be one of: {', '.join(TASK_TYPES)}")
        return
    await db.assign_task(task_id, worker, task_type)
    await message.reply("Assigned")


@dp.message_handler(commands=["tasks"])
async def cmd_tasks(message: types.Message):
    params = message.get_args().split()
    kwargs = {}
    for p in params:
        if p.startswith("type="):
            kwargs["task_type"] = p.split("=", 1)[1]
        elif p.startswith("worker="):
            kwargs["worker_name"] = p.split("=", 1)[1]
        elif p.startswith("month="):
            kwargs["month"] = p.split("=", 1)[1]
    rows = await db.get_tasks(**kwargs)
    if not rows:
        await message.reply("No tasks found")
        return
    lines = []
    for r in rows:
        task_id, title, ttype, worker, created = r
        lines.append(f"{task_id}. [{ttype or '-'}] {title} - {worker or 'unassigned'}")
    await message.reply("\n".join(lines))


@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    month = message.get_args().strip()
    if not month:
        await message.reply("Usage: /stats <YYYY-MM>")
        return
    rows = await db.worker_stats(month)
    if not rows:
        await message.reply("No data for this month")
        return
    text = "Stats for " + month + "\n"
    text += "\n".join(f"{name}: {count}" for name, count in rows)
    await message.reply(text)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(db.connect())
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

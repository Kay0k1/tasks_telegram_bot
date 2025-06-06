import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import Database

API_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

db = Database(DB_PATH)

TASK_TYPES = ["news", "meme", "selection", "longread"]

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add task")],
        [KeyboardButton(text="Unassigned"), KeyboardButton(text="Tasks")],
        [KeyboardButton(text="Stats")],
    ],
    resize_keyboard=True,
)


class AddTask(StatesGroup):
    type = State()
    worker = State()
    title = State()


class AssignTask(StatesGroup):
    task_id = State()
    worker = State()
    type = State()


class StatsQuery(StatesGroup):
    month = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Task Manager Bot", reply_markup=main_kb)


@router.channel_post(F.content_type == types.ContentType.TEXT)
async def on_channel_post(message: types.Message):
    title = message.text.strip()
    await db.add_task(title=title, message_id=message.message_id, chat_id=message.chat.id)


@router.message(F.text.casefold() == "add task")
async def start_add_task(message: types.Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text=t.capitalize(), callback_data=f"atype:{t}") for t in TASK_TYPES]
    ]
    await message.answer("Select task type", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AddTask.type)


@router.callback_query(AddTask.type, F.data.startswith("atype:"))
async def add_task_type(callback: types.CallbackQuery, state: FSMContext):
    task_type = callback.data.split(":", 1)[1]
    await state.update_data(type=task_type)
    await callback.message.answer("Enter worker name")
    await state.set_state(AddTask.worker)
    await callback.answer()


@router.message(AddTask.worker)
async def add_task_worker(message: types.Message, state: FSMContext):
    await state.update_data(worker=message.text.strip())
    await message.answer("Enter task title")
    await state.set_state(AddTask.title)


@router.message(AddTask.title)
async def add_task_title(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_type = data.get("type")
    worker = data.get("worker")
    title = message.text.strip()
    task_id = await db.add_task(title, task_type, worker)
    await message.answer(f"Task #{task_id} added", reply_markup=main_kb)
    await state.clear()


@router.message(F.text.casefold() == "unassigned")
async def list_unassigned(message: types.Message):
    rows = await db.get_unassigned_tasks()
    if not rows:
        await message.answer("No unassigned posts")
        return
    for task_id, title in rows:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Assign", callback_data=f"assign:{task_id}")]]
        )
        await message.answer(f"{task_id}: {title[:40]}", reply_markup=kb)


@router.callback_query(F.data.startswith("assign:"))
async def assign_start(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":", 1)[1])
    await state.update_data(task_id=task_id)
    await callback.message.answer("Enter worker name")
    await state.set_state(AssignTask.worker)
    await callback.answer()


@router.message(AssignTask.worker)
async def assign_worker(message: types.Message, state: FSMContext):
    await state.update_data(worker=message.text.strip())
    buttons = [
        [InlineKeyboardButton(text=t.capitalize(), callback_data=f"astype:{t}") for t in TASK_TYPES]
    ]
    await message.answer("Select task type", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AssignTask.type)


@router.callback_query(AssignTask.type, F.data.startswith("astype:"))
async def assign_type(callback: types.CallbackQuery, state: FSMContext):
    task_type = callback.data.split(":", 1)[1]
    data = await state.get_data()
    task_id = data.get("task_id")
    worker = data.get("worker")
    await db.assign_task(task_id, worker, task_type)
    await callback.message.answer("Assigned", reply_markup=main_kb)
    await state.clear()
    await callback.answer()


@router.message(F.text.casefold() == "tasks")
async def list_tasks(message: types.Message):
    rows = await db.get_tasks()
    if not rows:
        await message.answer("No tasks found")
        return
    lines: List[str] = []
    for task_id, title, ttype, worker, created in rows:
        lines.append(f"{task_id}. [{ttype or '-'}] {title} - {worker or 'unassigned'}")
    await message.answer("\n".join(lines))


@router.message(F.text.casefold() == "stats")
async def stats_request(message: types.Message, state: FSMContext):
    await message.answer("Enter month as YYYY-MM")
    await state.set_state(StatsQuery.month)


@router.message(StatsQuery.month)
async def show_stats(message: types.Message, state: FSMContext):
    month = message.text.strip()
    rows = await db.worker_stats(month)
    if not rows:
        await message.answer("No data for this month", reply_markup=main_kb)
    else:
        text = "Stats for " + month + "\n" + "\n".join(f"{name}: {count}" for name, count in rows)
        await message.answer(text, reply_markup=main_kb)
    await state.clear()


async def main() -> None:
    await db.connect()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

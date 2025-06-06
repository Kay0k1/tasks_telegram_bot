import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
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


class AddTask(StatesGroup):
    type = State()
    worker = State()
    title = State()


class AssignTask(StatesGroup):
    task_id = State()
    worker = State()
    type = State()


class AddWorkerState(StatesGroup):
    name = State()


def main_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="\u270F\ufe0f \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0443", callback_data="add")],
            [types.InlineKeyboardButton(text="\u041d\u0435\u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044b\u0435", callback_data="unassigned")],
            [types.InlineKeyboardButton(text="\u0417\u0430\u0434\u0430\u0447\u0438", callback_data="tasks:0")],
            [types.InlineKeyboardButton(text="\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430", callback_data="stats")],
            [types.InlineKeyboardButton(text="\u0420\u0430\u0431\u043e\u0442\u043d\u0438\u043a\u0438", callback_data="workers")],
        ]
    )


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    text = (
        "\u041f\u0440\u0438\u0432\u0435\u0442! \u042d\u0442\u043e \u0431\u043e\u0442 \u0434\u043b\u044f \u0443\u0447\u0435\u0442\u0430 \u0437\u0430\u0434\u0430\u0447 \u0432\u0430\u0448\u0435\u0433\u043e \u043f\u0430\u0431\u043b\u0438\u043a\u0430."
        " \u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0438 \u043d\u0438\u0436\u0435 \u0434\u043b\u044f \u0440\u0430\u0431\u043e\u0442\u044b."
    )
    await message.answer(text, reply_markup=main_keyboard())


def cancel_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="\u041e\u0442\u043c\u0435\u043d\u0430", callback_data="cancel")]]
    )


@router.callback_query(F.data == "cancel")
async def cancel_state(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u043e", reply_markup=main_keyboard())
    await callback.answer()


@router.channel_post(F.content_type == types.ContentType.TEXT)
async def on_channel_post(message: types.Message) -> None:
    title = message.text.strip()
    await db.add_task(title=title, message_id=message.message_id, chat_id=message.chat.id)


def types_keyboard(prefix: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=t.capitalize(), callback_data=f"{prefix}:{t}") for t in TASK_TYPES],
            [types.InlineKeyboardButton(text="\u041e\u0442\u043c\u0435\u043d\u0430", callback_data="cancel")],
        ]
    )


async def workers_keyboard(prefix: str) -> types.InlineKeyboardMarkup:
    names = await db.list_workers()
    buttons = [[types.InlineKeyboardButton(text=n, callback_data=f"{prefix}:{n}") for n in names]] if names else []
    buttons.append([types.InlineKeyboardButton(text="\u041e\u0442\u043c\u0435\u043d\u0430", callback_data="cancel")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "add")
async def add_task_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u0437\u0430\u0434\u0430\u0447\u0438", reply_markup=types_keyboard("atype"))
    await state.set_state(AddTask.type)
    await callback.answer()


@router.callback_query(AddTask.type, F.data.startswith("atype:"))
async def add_task_type(callback: types.CallbackQuery, state: FSMContext) -> None:
    task_type = callback.data.split(":", 1)[1]
    await state.update_data(type=task_type)
    kb = await workers_keyboard("aworker")
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0438\u043b\u0438 \u043d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u0438\u043c\u044f \u0440\u0430\u0431\u043e\u0442\u043d\u0438\u043a\u0430", reply_markup=kb)
    await state.set_state(AddTask.worker)
    await callback.answer()


@router.message(AddTask.worker)
async def add_task_worker_msg(message: types.Message, state: FSMContext) -> None:
    await state.update_data(worker=message.text.strip())
    await message.answer("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438", reply_markup=cancel_keyboard())
    await state.set_state(AddTask.title)


@router.callback_query(AddTask.worker, F.data.startswith("aworker:"))
async def add_task_worker_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    worker = callback.data.split(":", 1)[1]
    await state.update_data(worker=worker)
    await callback.message.edit_text("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438", reply_markup=cancel_keyboard())
    await state.set_state(AddTask.title)
    await callback.answer()


@router.message(AddTask.title)
async def add_task_title(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    task_type = data.get("type")
    worker = data.get("worker")
    title = message.text.strip()
    task_id = await db.add_task(title, task_type, worker)
    await message.answer(f"\u0417\u0430\u0434\u0430\u0447\u0430 #{task_id} \u0441\u043e\u0437\u0434\u0430\u043d\u0430", reply_markup=main_keyboard())
    await state.clear()


@router.callback_query(F.data == "unassigned")
async def list_unassigned(callback: types.CallbackQuery) -> None:
    rows = await db.get_unassigned_tasks()
    if not rows:
        await callback.message.edit_text("\u041d\u0435\u0442 \u043d\u0435\u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044b\u0445 \u043f\u043e\u0441\u0442\u043e\u0432", reply_markup=main_keyboard())
        await callback.answer()
        return
    for task_id, title in rows:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="\u041d\u0430\u0437\u043d\u0430\u0447\u0438\u0442\u044c", callback_data=f"assign:{task_id}")]
            ]
        )
        await callback.message.answer(f"{task_id}: {title[:40]}", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("assign:"))
async def assign_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    task_id = int(callback.data.split(":", 1)[1])
    await state.update_data(task_id=task_id)
    kb = await workers_keyboard("asworker")
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0440\u0430\u0431\u043e\u0442\u043d\u0438\u043a\u0430", reply_markup=kb)
    await state.set_state(AssignTask.worker)
    await callback.answer()


@router.callback_query(AssignTask.worker, F.data.startswith("asworker:"))
async def assign_worker_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    worker = callback.data.split(":", 1)[1]
    await state.update_data(worker=worker)
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f", reply_markup=types_keyboard("astype"))
    await state.set_state(AssignTask.type)
    await callback.answer()


@router.message(AssignTask.worker)
async def assign_worker_msg(message: types.Message, state: FSMContext) -> None:
    await state.update_data(worker=message.text.strip())
    await message.answer("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f", reply_markup=types_keyboard("astype"))
    await state.set_state(AssignTask.type)


@router.callback_query(AssignTask.type, F.data.startswith("astype:"))
async def assign_type(callback: types.CallbackQuery, state: FSMContext) -> None:
    task_type = callback.data.split(":", 1)[1]
    data = await state.get_data()
    task_id = data.get("task_id")
    worker = data.get("worker")
    await db.assign_task(task_id, worker, task_type)
    await callback.message.edit_text("\u0417\u0430\u0434\u0430\u0447\u0430 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0430", reply_markup=main_keyboard())
    await state.clear()
    await callback.answer()




@router.callback_query(F.data.startswith("tasks:"))
async def tasks_page(callback: types.CallbackQuery) -> None:
    page = int(callback.data.split(":", 1)[1])
    rows = await db.get_tasks_page(page * db.PAGE_SIZE, db.PAGE_SIZE)
    if not rows and page == 0:
        await callback.message.edit_text("\u0417\u0430\u0434\u0430\u0447 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e", reply_markup=main_keyboard())
        await callback.answer()
        return
    lines = []
    for tid, title, ttype, worker, created in rows:
        lines.append(f"{tid}. [{ttype or '-'}] {title} - {worker or '---'}")
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="\u25c0\ufe0f", callback_data=f"tasks:{page-1}"))
    if len(rows) == db.PAGE_SIZE:
        nav.append(types.InlineKeyboardButton(text="\u25b6\ufe0f", callback_data=f"tasks:{page+1}"))
    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([types.InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data="start")])
    await callback.message.edit_text("\n".join(lines), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "stats")
async def stats_menu(callback: types.CallbackQuery) -> None:
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="7 \u0434\u043d\u0435\u0439", callback_data="statp:7"),
                types.InlineKeyboardButton(text="30 \u0434\u043d\u0435\u0439", callback_data="statp:30"),
            ],
            [types.InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data="start")],
        ]
    )
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0435\u0440\u0438\u043e\u0434", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("statp:"))
async def stats_period(callback: types.CallbackQuery) -> None:
    days = int(callback.data.split(":", 1)[1])
    rows = await db.worker_stats_period(days)
    if not rows:
        text = "\u0414\u0430\u043d\u043d\u044b\u0445 \u043d\u0435\u0442"
    else:
        text = "\n".join(f"{name}: {cnt}" for name, cnt in rows)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data="start")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "workers")
async def workers_menu(callback: types.CallbackQuery) -> None:
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c", callback_data="worker_add")],
            [types.InlineKeyboardButton(text="\u0423\u0434\u0430\u043b\u0438\u0442\u044c", callback_data="worker_del")],
            [types.InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data="start")],
        ]
    )
    await callback.message.edit_text("\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0431\u043e\u0442\u043d\u0438\u043a\u0430\u043c\u0438", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "worker_add")
async def worker_add_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddWorkerState.name)
    await callback.message.edit_text("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0438\u043c\u044f \u0440\u0430\u0431\u043e\u0442\u043d\u0438\u043a\u0430", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddWorkerState.name)
async def worker_add_finish(message: types.Message, state: FSMContext) -> None:
    name = message.text.strip()
    await db.add_worker(name)
    await message.answer("\u0420\u0430\u0431\u043e\u0442\u043d\u0438\u043a \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d", reply_markup=main_keyboard())
    await state.clear()


@router.callback_query(F.data == "worker_del")
async def worker_del_start(callback: types.CallbackQuery) -> None:
    names = await db.list_workers()
    if not names:
        await callback.message.edit_text("\u0421\u043f\u0438\u0441\u043e\u043a \u043f\u0443\u0441\u0442", reply_markup=main_keyboard())
        await callback.answer()
        return
    keyboard = [[types.InlineKeyboardButton(text=n, callback_data=f"wdel:{n}") for n in names]]
    keyboard.append([types.InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data="start")])
    await callback.message.edit_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043a\u043e\u0433\u043e \u0443\u0434\u0430\u043b\u0438\u0442\u044c", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data.startswith("wdel:"))
async def worker_del_finish(callback: types.CallbackQuery) -> None:
    name = callback.data.split(":", 1)[1]
    await db.delete_worker(name)
    await callback.message.edit_text("\u0423\u0434\u0430\u043b\u0435\u043d\u043e", reply_markup=main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "start")
async def back_to_start(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", reply_markup=main_keyboard()
    )
    await callback.answer()


async def main() -> None:
    await db.connect()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


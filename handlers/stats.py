from telegram import Update
from telegram.ext import ContextTypes
from database import get_full_stats
from config import PRIORITY_LABELS
from handlers.main_menu import main_menu_keyboard


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    base, by_cat, by_pri = get_full_stats(user_id)

    total = base.get("total", 0)

    if total == 0:
        await query.edit_message_text(
            "Пока нет задач! Добавь первую.",
            reply_markup=main_menu_keyboard()
        )
        return

    done = base.get("done", 0) or 0
    open_count = base.get("open_count", 0) or 0
    overdue = base.get("overdue", 0) or 0

    pct = round(done / total * 100) if total else 0
    filled = pct // 10
    bar = "🟩" * filled + "⬜" * (10 - filled)

    text = "📊 <b>Дашборд</b>\n\n"
    text += "<b>Общий прогресс:</b>\n"
    text += f"{bar} <b>{pct}%</b> выполнено\n"
    text += f"Всего задач: <b>{total}</b>\n\n"

    text += "<b>✅ Выполненные задачи:</b>\n"
    text += f"Количество: <b>{done}</b>\n\n"

    text += "<b>📌 Невыполненные задачи:</b>\n"
    text += f"Количество: <b>{open_count}</b>\n"
    if overdue > 0:
        text += f"🔴 Просрочено: <b>{overdue}</b>\n"
    text += "\n"

    if by_cat:
        text += "<b>📁 По категориям:</b>\n"
        for row in by_cat:
            name = row["name"] or "Без категории"
            cnt = row["cnt"] or 0
            done_cnt = row["done_cnt"] or 0
            open_cnt_cat = cnt - done_cnt
            text += (
                f"{name}\n"
                f"   ✅ Выполнено: {done_cnt}\n"
                f"   ☐ Невыполнено: {open_cnt_cat}\n"
            )
        text += "\n"

    if by_pri:
        text += "<b>⚡ По приоритетам:</b>\n"
        for row in by_pri:
            label = PRIORITY_LABELS.get(row["priority"], "Неизвестно")
            text += f"{label}: {row['cnt']} задач\n"

    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import ensure_default_categories


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Новая задача", callback_data="new_task"),
            InlineKeyboardButton("📋 Мои задачи", callback_data="my_tasks"),
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("⚙️ Категории", callback_data="categories"),
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_default_categories(user_id)

    await update.message.reply_text(
        "Привет! Я твой личный планировщик задач.\n\nВыбери действие:",
        reply_markup=main_menu_keyboard()
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        'Выбери действие:',
        reply_markup=main_menu_keyboard()
    )
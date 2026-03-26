from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import BadRequest

from database import (
    get_categories,
    add_tasks,
    get_tasks,
    complete_task,
    delete_task,
    update_task_priority,
    get_all_tasks,
    add_category,
    update_category,
    delete_category,
    get_category_by_id,
    category_exists,
)
from config import PRIORITY_LABELS
from datetime import datetime, date
from handlers.main_menu import main_menu_keyboard

TITLE, DESCRIPTION, CATEGORY, PRIORITY, DEADLINE, CAT_ADD, CAT_EDIT = range(7)


# =========================
# СОЗДАНИЕ НОВОЙ ЗАДАЧИ
# =========================
async def start_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Введите название задачи:")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Пропустить", callback_data="skip_desc")]
    ])
    await update.message.reply_text(
        "Добавь описание (или пропусти):",
        reply_markup=kb
    )
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data["description"] = None
        msg = update.callback_query.message
        user_id = update.effective_user.id
    else:
        context.user_data["description"] = update.message.text
        msg = update.message
        user_id = update.effective_user.id

    cats = get_categories(user_id)

    if not cats:
        await msg.reply_text(
            "Категории не найдены. Сначала создай категорию.",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(c["name"], callback_data=f'cat_{c["id"]}')]
        for c in cats
    ])
    await msg.reply_text("Выбери категорию:", reply_markup=kb)
    return CATEGORY


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["category_id"] = int(query.data.split("_")[1])

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(label, callback_data=f"pri_{num}")
        for num, label in PRIORITY_LABELS.items()
    ]])

    await query.edit_message_text("Выбери приоритет:", reply_markup=kb)
    return PRIORITY


async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["priority"] = int(query.data.split("_")[1])

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Без дедлайна", callback_data="skip_deadline")]
    ])

    await query.edit_message_text(
        "Введи дедлайн в формате ДД.ММ.ГГГГ или пропусти:",
        reply_markup=kb
    )
    return DEADLINE


async def get_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if update.message:
        try:
            task_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
            today = date.today()

            if task_date < today:
                await update.message.reply_text(
                    "Нельзя указывать дедлайн в прошлом. Введи сегодняшнюю дату или позже."
                )
                return DEADLINE

            deadline = task_date.strftime("%Y-%m-%d")

        except ValueError:
            await update.message.reply_text(
                "Неверный формат. Введи ДД.ММ.ГГГГ или нажми «Без дедлайна»"
            )
            return DEADLINE

        d = context.user_data
        add_tasks(
            user_id,
            d["title"],
            d.get("description"),
            d["category_id"],
            d["priority"],
            deadline
        )

        text = (
            f'Задача создана!\n\n'
            f'{d["title"]}\n'
            f'Приоритет: {PRIORITY_LABELS[d["priority"]]}\n'
            f'Дедлайн: {update.message.text}'
        )

        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    else:
        await update.callback_query.answer()
        d = context.user_data

        add_tasks(
            user_id,
            d["title"],
            d.get("description"),
            d["category_id"],
            d["priority"],
            None
        )

        text = (
            f'Задача создана!\n\n'
            f'{d["title"]}\n'
            f'Приоритет: {PRIORITY_LABELS[d["priority"]]}'
        )

        await update.callback_query.message.reply_text(
            text,
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END


new_task_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_new_task, pattern="^new_task$")],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
            CallbackQueryHandler(get_description, pattern="^skip_desc$")
        ],
        CATEGORY: [CallbackQueryHandler(get_category, pattern="^cat_")],
        PRIORITY: [CallbackQueryHandler(get_priority, pattern="^pri_")],
        DEADLINE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_deadline),
            CallbackQueryHandler(get_deadline, pattern="^skip_deadline$")
        ],
    },
    fallbacks=[],
    per_message=False
)


# =========================
# ФОРМАТИРОВАНИЕ ЗАДАЧИ
# =========================
def format_task(t):
    pri = PRIORITY_LABELS.get(t["priority"], "")
    cat = t["cat_name"] or "Без категории"

    text = f"{pri} <b>{t['title']}</b>\n"
    text += f"📁 {cat}"

    if t["deadline"]:
        dl = date.fromisoformat(t["deadline"])
        diff = (dl - date.today()).days

        if diff < 0:
            icon = "🔴"
        elif diff <= 2:
            icon = "🟡"
        else:
            icon = "🟢"

        text += f"\n{icon} Дедлайн: {dl.strftime('%d.%m.%Y')}"

        if diff < 0:
            text += " (просрочено!)"
        elif diff == 0:
            text += " (сегодня!)"

    return text


# =========================
# МОИ ЗАДАЧИ -> РАЗДЕЛЫ
# =========================
async def show_task_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("☐ Невыполнено", callback_data="tasks_open"),
            InlineKeyboardButton("✅ Выполнено", callback_data="tasks_done"),
        ],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
    ])

    await query.edit_message_text(
        "Выбери раздел задач:",
        reply_markup=kb
    )


async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0, status="open"):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cat_filter = context.user_data.get("filter_cat")
    pri_filter = context.user_data.get("filter_pri")

    context.user_data["tasks_status"] = status
    tasks = get_tasks(user_id, status=status, category_id=cat_filter, priority=pri_filter)

    title = "Невыполненные задачи" if status == "open" else "Выполненные задачи"

    if not tasks:
        try:
            await query.edit_message_text(
                f"📋 <b>{title}</b>\n\nСписок пуст.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="my_tasks")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
                ]),
                parse_mode="HTML"
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        return

    per_page = 5
    total_pages = (len(tasks) + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))
    chunk = tasks[page * per_page:(page + 1) * per_page]

    context.user_data["tasks_page"] = page

    text = f"📋 <b>{title}</b> (стр. {page + 1}/{total_pages})\n\n"
    buttons = []

    start_index = page * per_page
    number_buttons = []

    for i, t in enumerate(chunk, start=start_index + 1):
        mark = "☐" if t["status"] == "open" else "✅"
        text += f"{mark} <b>{i}.</b>\n"
        text += format_task(t)
        text += "\n\n"

        number_buttons.append(
            InlineKeyboardButton(str(i), callback_data=f"task_{t['id']}")
        )

    for j in range(0, len(number_buttons), 3):
        buttons.append(number_buttons[j:j + 3])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="my_tasks")])
    buttons.append([InlineKeyboardButton("🏠 Меню", callback_data="menu")])

    kb = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        raise


async def show_open_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tasks(update, context, page=0, status="open")


async def show_done_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tasks(update, context, page=0, status="done")


async def paginate_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    page = int(query.data.split("_")[1])
    status = context.user_data.get("tasks_status", "open")
    await show_tasks(update, context, page=page, status=status)


# =========================
# КАРТОЧКА ЗАДАЧИ
# =========================
async def show_task_actions_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    user_id = update.effective_user.id

    tasks = get_all_tasks(user_id)
    current_task = None

    for t in tasks:
        if t["id"] == task_id:
            current_task = t
            break

    if current_task is None:
        try:
            await query.edit_message_text(
                "Задача не найдена.",
                reply_markup=main_menu_keyboard()
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        return

    text = "📌 <b>Карточка задачи</b>\n\n"
    text += format_task(current_task)

    buttons = []

    if current_task["status"] != "done":
        buttons.append([InlineKeyboardButton("✅ Выполнить", callback_data=f"done_{task_id}")])

    buttons.append([InlineKeyboardButton("❌ Удалить", callback_data=f"del_{task_id}")])

    if current_task["status"] != "done":
        buttons.append([
            InlineKeyboardButton("🔺 Повысить приоритет", callback_data=f"uppri_{task_id}"),
            InlineKeyboardButton("🔻 Понизить приоритет", callback_data=f"downpri_{task_id}")
        ])

    buttons.append([InlineKeyboardButton("◀️ Назад к списку", callback_data=f"page_{context.user_data.get('tasks_page', 0)}")])
    buttons.append([InlineKeyboardButton("🏠 Меню", callback_data="menu")])

    kb = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        raise


async def show_task_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])
    await show_task_actions_by_id(update, context, task_id)


# =========================
# ДЕЙСТВИЯ С ЗАДАЧЕЙ
# =========================
async def complete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id

    complete_task(task_id, user_id)

    page = context.user_data.get("tasks_page", 0)
    status = context.user_data.get("tasks_status", "open")
    await show_tasks(update, context, page, status)


async def delete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id

    delete_task(task_id, user_id)

    page = context.user_data.get("tasks_page", 0)
    status = context.user_data.get("tasks_status", "open")
    await show_tasks(update, context, page, status)


async def change_priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    task_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id

    tasks = get_all_tasks(user_id)
    current_task = None

    for t in tasks:
        if t["id"] == task_id:
            current_task = t
            break

    if current_task is None:
        await query.answer("Задача не найдена", show_alert=True)
        return

    if current_task["status"] == "done":
        await query.answer("Нельзя менять приоритет выполненной задачи", show_alert=True)
        return

    current_priority = current_task["priority"]

    if current_priority <= 1:
        await query.answer(
            "Вы достигли самого высокого значения в приоритете!",
            show_alert=True
        )
        return

    new_priority = current_priority - 1
    update_task_priority(task_id, user_id, new_priority)

    await query.answer("Приоритет повышен")
    await show_task_actions_by_id(update, context, task_id)


async def lower_priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    task_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id

    tasks = get_all_tasks(user_id)
    current_task = None

    for t in tasks:
        if t["id"] == task_id:
            current_task = t
            break

    if current_task is None:
        await query.answer("Задача не найдена", show_alert=True)
        return

    if current_task["status"] == "done":
        await query.answer("Нельзя менять приоритет выполненной задачи", show_alert=True)
        return

    current_priority = current_task["priority"]

    if current_priority >= 3:
        await query.answer(
            "Вы достигли самого минимального значения в приоритете!",
            show_alert=True
        )
        return

    new_priority = current_priority + 1
    update_task_priority(task_id, user_id, new_priority)

    await query.answer("Приоритет понижен")
    await show_task_actions_by_id(update, context, task_id)


# =========================
# КАТЕГОРИИ
# =========================
def categories_menu_keyboard(user_id):
    cats = get_categories(user_id)

    buttons = [
        [InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")]
    ]

    for c in cats:
        buttons.append([
            InlineKeyboardButton(f"✏️ {c['name']}", callback_data=f"cat_edit_{c['id']}"),
            InlineKeyboardButton(f"🗑 {c['name']}", callback_data=f"cat_del_{c['id']}")
        ])

    buttons.append([InlineKeyboardButton("🏠 Меню", callback_data="menu")])

    return InlineKeyboardMarkup(buttons)


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cats = get_categories(user_id)

    if not cats:
        text = "⚙️ <b>Категории</b>\n\nКатегорий пока нет."
    else:
        text = "⚙️ <b>Категории</b>\n\n"
        for i, c in enumerate(cats, start=1):
            text += f"{i}. {c['name']}\n"

    await query.edit_message_text(
        text,
        reply_markup=categories_menu_keyboard(user_id),
        parse_mode="HTML"
    )


async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Введи название новой категории:")
    return CAT_ADD


async def save_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("Название не должно быть пустым.")
        return CAT_ADD

    if category_exists(user_id, name):
        await update.message.reply_text("Такая категория уже есть. Введи другое название.")
        return CAT_ADD

    add_category(user_id, name)

    await update.message.reply_text(
        f"Категория «{name}» добавлена.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


async def start_edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id

    row = get_category_by_id(user_id, category_id)
    if row is None:
        await query.answer("Категория не найдена", show_alert=True)
        return ConversationHandler.END

    context.user_data["edit_category_id"] = category_id

    await query.edit_message_text(
        f"Текущее название: {row['name']}\n\nВведи новое название:"
    )
    return CAT_EDIT


async def save_edited_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_name = update.message.text.strip()
    category_id = context.user_data.get("edit_category_id")

    if not category_id:
        await update.message.reply_text("Не удалось определить категорию.")
        return ConversationHandler.END

    if not new_name:
        await update.message.reply_text("Название не должно быть пустым.")
        return CAT_EDIT

    if category_exists(user_id, new_name):
        await update.message.reply_text("Такая категория уже есть. Введи другое название.")
        return CAT_EDIT

    update_category(user_id, category_id, new_name)

    await update.message.reply_text(
        f"Категория переименована в «{new_name}».",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


async def remove_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[2])
    user_id = update.effective_user.id

    row = get_category_by_id(user_id, category_id)
    if row is None:
        await query.answer("Категория не найдена", show_alert=True)
        return

    delete_category(user_id, category_id)

    await query.edit_message_text(
        f"Категория «{row['name']}» удалена.",
        reply_markup=main_menu_keyboard()
    )


category_manage_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_add_category, pattern="^cat_add$"),
        CallbackQueryHandler(start_edit_category, pattern="^cat_edit_"),
    ],
    states={
        CAT_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_category)],
        CAT_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_category)],
    },
    fallbacks=[],
    per_message=False
)


# =========================
# МЕНЮ / УВЕДОМЛЕНИЯ
# =========================
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.edit_message_text(
            "Выбери действие:",
            reply_markup=main_menu_keyboard()
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        raise


async def hide_notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.delete_message()
    except BadRequest:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
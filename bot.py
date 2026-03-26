from scheduler import start_scheduler
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers.main_menu import start
from handlers.tasks import (
    new_task_handler,
    category_manage_handler,
    show_task_sections,
    show_open_tasks,
    show_done_tasks,
    paginate_tasks,
    show_task_actions,
    complete_task_handler,
    delete_task_handler,
    change_priority_handler,
    lower_priority_handler,
    show_categories,
    remove_category_handler,
    back_to_menu,
    hide_notice,
)
from handlers.stats import show_stats


async def post_init(app):
    await app.bot.delete_webhook(drop_pending_updates=True)
    start_scheduler(app.bot)
    print("Bot and scheduler started!")


def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(new_task_handler)

    app.add_handler(CallbackQueryHandler(show_task_sections, pattern="^my_tasks$"))
    app.add_handler(CallbackQueryHandler(show_open_tasks, pattern="^tasks_open$"))
    app.add_handler(CallbackQueryHandler(show_done_tasks, pattern="^tasks_done$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_categories, pattern="^categories$"))
    app.add_handler(CallbackQueryHandler(paginate_tasks, pattern="^page_"))
    app.add_handler(CallbackQueryHandler(show_task_actions, pattern="^task_"))
    app.add_handler(CallbackQueryHandler(complete_task_handler, pattern="^done_"))
    app.add_handler(CallbackQueryHandler(delete_task_handler, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(change_priority_handler, pattern="^uppri_"))
    app.add_handler(CallbackQueryHandler(lower_priority_handler, pattern="^downpri_"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(hide_notice, pattern="^hide_notice$"))
    app.add_handler(category_manage_handler)
    app.add_handler(CallbackQueryHandler(show_task_sections, pattern="^my_tasks$"))
    app.add_handler(CallbackQueryHandler(show_open_tasks, pattern="^tasks_open$"))
    app.add_handler(CallbackQueryHandler(show_done_tasks, pattern="^tasks_done$"))
    app.add_handler(CallbackQueryHandler(show_categories, pattern="^categories$"))
    app.add_handler(CallbackQueryHandler(remove_category_handler, pattern="^cat_del_"))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
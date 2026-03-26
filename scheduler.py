from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import PRIORITY_LABELS
from database import get_tasks_to_remind, mark_reminded_today

scheduler = AsyncIOScheduler()


def notification_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Меню", callback_data="menu")],
        [InlineKeyboardButton("❌ Скрыть", callback_data="hide_notice")]
    ])


async def check_reminders(bot):
    tasks = get_tasks_to_remind()
    today = date.today()

    for t in tasks:
        dl = date.fromisoformat(t["deadline"])
        diff = (dl - today).days
        pri = PRIORITY_LABELS.get(t["priority"], "")

        if diff > 1:
            if diff % 10 == 1 and diff % 100 != 11:
                day_word = "день"
            elif diff % 10 in [2, 3, 4] and diff % 100 not in [12, 13, 14]:
                day_word = "дня"
            else:
                day_word = "дней"

            deadline_text = f"⏳ До дедлайна осталось: {diff} {day_word}"
        elif diff == 1:
            deadline_text = "⚠️ ДО ДЕДЛАЙНА 1 ДЕНЬ! ПОТОРОПИСЬ"
        elif diff == 0:
            deadline_text = "🚨 ДЕДЛАЙН СЕГОДНЯ!"
        else:
            deadline_text = "🔴 ЗАДАЧА ПРОСРОЧЕНА!"

        text = (
            f"⏰ <b>Напоминание о задаче</b>\n\n"
            f"{pri} <b>{t['title']}</b>\n"
            f"📁 {t['cat_name'] or 'Без категории'}\n"
            f"📅 Дедлайн: {dl.strftime('%d.%m.%Y')}\n\n"
            f"{deadline_text}"
        )

        try:
            await bot.send_message(
                chat_id=t["user_id"],
                text=text,
                parse_mode="HTML",
                reply_markup=notification_keyboard()
            )
            mark_reminded_today(t["id"])
        except Exception as e:
            print(f"Reminder error for user {t['user_id']}: {e}")


def start_scheduler(bot):
    scheduler.add_job(
        check_reminders,
        trigger=CronTrigger(hour=9, minute=0, timezone="Europe/Amsterdam"),
        args=[bot],
        id="reminder_job",
        replace_existing=True,
    )
    scheduler.start()
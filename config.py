import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

PRIORITY_LABELS = {
    1: '🔴Высокий',
    2: '🟡Средний',
    3: '🟢 Низкий'
}
STATUS_OPEN = 'open'
STATUS_DONE = 'done'
DEFAULT_CATEGORIES = [
    'Учёба',
    'Работа',
    'Личное'
]

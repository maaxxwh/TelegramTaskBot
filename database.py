import sqlite3
from datetime import date
from config import DEFAULT_CATEGORIES

DB_PATH = "tasks.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def column_exists(table, column, conn):
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def init_db():
    conn = get_conn()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
        priority INTEGER DEFAULT 2,
        status TEXT DEFAULT 'open',
        deadline TEXT,
        remind_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    if not column_exists("tasks", "last_reminded_at", conn):
        conn.execute("ALTER TABLE tasks ADD COLUMN last_reminded_at TEXT")

    conn.commit()
    conn.close()


def ensure_default_categories(user_id):
    conn = get_conn()

    existing_rows = conn.execute(
        "SELECT name FROM categories WHERE user_id = ?",
        (user_id,)
    ).fetchall()

    existing_names = {row["name"] for row in existing_rows}

    for name in DEFAULT_CATEGORIES:
        if name not in existing_names:
            conn.execute(
                "INSERT INTO categories (user_id, name) VALUES (?, ?)",
                (user_id, name)
            )

    conn.commit()
    conn.close()


def get_categories(user_id):
    conn = get_conn()
    cats = conn.execute(
        "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,)
    ).fetchall()
    conn.close()
    return cats


def add_tasks(user_id, title, description, category_id, priority, deadline=None, remind_at=None):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO tasks (user_id, title, description, category_id, priority, deadline, remind_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, description, category_id, priority, deadline, remind_at)
    )
    conn.commit()
    conn.close()


def get_tasks(user_id, status="open", category_id=None, priority=None):
    conn = get_conn()
    query = """
    SELECT t.*, c.name as cat_name
    FROM tasks t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.user_id = ? AND t.status = ?
    """
    params = [user_id, status]

    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)

    if priority:
        query += " AND t.priority = ?"
        params.append(priority)

    query += " ORDER BY t.priority ASC, t.deadline ASC"

    tasks = conn.execute(query, params).fetchall()
    conn.close()
    return tasks


def get_all_tasks(user_id, category_id=None, priority=None):
    conn = get_conn()
    query = """
    SELECT t.*, c.name as cat_name
    FROM tasks t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.user_id = ?
    """
    params = [user_id]

    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)

    if priority:
        query += " AND t.priority = ?"
        params.append(priority)

    query += " ORDER BY t.status ASC, t.priority ASC, t.deadline ASC"

    tasks = conn.execute(query, params).fetchall()
    conn.close()
    return tasks


def complete_task(task_id, user_id):
    conn = get_conn()
    conn.execute(
        "UPDATE tasks SET status = 'done' WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_task(task_id, user_id):
    conn = get_conn()
    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    conn.close()


def update_task_priority(task_id, user_id, priority):
    conn = get_conn()
    conn.execute(
        "UPDATE tasks SET priority = ? WHERE id = ? AND user_id = ?",
        (priority, task_id, user_id)
    )
    conn.commit()
    conn.close()


def get_overdue_tasks(user_id):
    conn = get_conn()
    today = date.today().isoformat()

    tasks = conn.execute(
        """
        SELECT t.*, c.name as cat_name
        FROM tasks t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
          AND t.status = 'open'
          AND t.deadline IS NOT NULL
          AND t.deadline < ?
        ORDER BY t.deadline ASC
        """,
        (user_id, today)
    ).fetchall()

    conn.close()
    return tasks


def get_tasks_to_remind():
    conn = get_conn()
    today = date.today().isoformat()

    tasks = conn.execute(
        """
        SELECT t.*, c.name as cat_name
        FROM tasks t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.status = 'open'
          AND t.deadline IS NOT NULL
          AND (t.last_reminded_at IS NULL OR t.last_reminded_at < ?)
        ORDER BY t.deadline ASC
        """,
        (today,)
    ).fetchall()

    conn.close()
    return tasks


def mark_reminded_today(task_id):
    conn = get_conn()
    today = date.today().isoformat()

    conn.execute(
        "UPDATE tasks SET last_reminded_at = ? WHERE id = ?",
        (today, task_id)
    )
    conn.commit()
    conn.close()


def get_full_stats(user_id):
    conn = get_conn()
    today = date.today().isoformat()

    base_row = conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count,
            SUM(CASE
                    WHEN status = 'open'
                     AND deadline IS NOT NULL
                     AND deadline < ?
                    THEN 1 ELSE 0
                END) as overdue
        FROM tasks
        WHERE user_id = ?
        """,
        (today, user_id)
    ).fetchone()

    by_cat = conn.execute(
        """
        SELECT
            c.name as name,
            COUNT(t.id) as cnt,
            SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done_cnt
        FROM tasks t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        GROUP BY c.name
        ORDER BY cnt DESC, name ASC
        """,
        (user_id,)
    ).fetchall()

    by_pri = conn.execute(
        """
        SELECT
            priority,
            COUNT(*) as cnt
        FROM tasks
        WHERE user_id = ?
        GROUP BY priority
        ORDER BY priority ASC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    base = {
        "total": base_row["total"] or 0,
        "done": base_row["done"] or 0,
        "open_count": base_row["open_count"] or 0,
        "overdue": base_row["overdue"] or 0,
    }

    return base, by_cat, by_pri
def add_category(user_id, name):
    conn = get_conn()
    conn.execute(
        "INSERT INTO categories (user_id, name) VALUES (?, ?)",
        (user_id, name)
    )
    conn.commit()
    conn.close()


def update_category(user_id, category_id, new_name):
    conn = get_conn()
    conn.execute(
        "UPDATE categories SET name = ? WHERE id = ? AND user_id = ?",
        (new_name, category_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_category(user_id, category_id):
    conn = get_conn()

    conn.execute(
        "UPDATE tasks SET category_id = NULL WHERE user_id = ? AND category_id = ?",
        (user_id, category_id)
    )

    conn.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id)
    )

    conn.commit()
    conn.close()


def get_category_by_id(user_id, category_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id)
    ).fetchone()
    conn.close()
    return row


def category_exists(user_id, name):
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM categories WHERE user_id = ? AND lower(name) = lower(?)",
        (user_id, name)
    ).fetchone()
    conn.close()
    return row is not None
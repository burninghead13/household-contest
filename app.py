from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from datetime import datetime, date
import sqlite3
import os
from translations import TRANSLATIONS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-please')

DB_PATH = os.environ.get('DB_PATH', '/data/haushalt.db')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'haushalt')
DEFAULT_LANG = os.environ.get('DEFAULT_LANG', 'de')

# ── i18n ──────────────────────────────────────────────────────────────────────

def get_lang():
    return session.get('lang', DEFAULT_LANG)

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

app.jinja_env.globals['t'] = t
app.jinja_env.globals['get_lang'] = get_lang

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#4f46e5'
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 1,
            icon TEXT DEFAULT '🏠',
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            month TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
    ''')

    c.execute('SELECT COUNT(*) FROM players')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO players (name, color) VALUES ('Player 1', '#4f46e5')")
        c.execute("INSERT INTO players (name, color) VALUES ('Player 2', '#e11d48')")

    c.execute('SELECT COUNT(*) FROM tasks')
    if c.fetchone()[0] == 0:
        defaults = [
            ('Vacuuming', 3, '🧹'),
            ('Mopping', 4, '🪣'),
            ('Dishes', 2, '🍽️'),
            ('Grocery shopping', 3, '🛒'),
            ('Doing laundry', 3, '👕'),
            ('Hanging laundry', 2, '📎'),
            ('Taking out trash', 2, '🗑️'),
            ('Cleaning bathroom', 4, '🚿'),
            ('Cooking', 3, '🍳'),
        ]
        c.executemany("INSERT INTO tasks (name, points, icon) VALUES (?,?,?)", defaults)

    conn.commit()
    conn.close()

def current_month():
    return date.today().strftime('%Y-%m')

# ── Auth decorators ───────────────────────────────────────────────────────────

def require_login(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash(t('admin_required'), 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['is_admin'] = True
            return redirect(url_for('index'))
        elif pw == APP_PASSWORD:
            session['logged_in'] = True
            session['is_admin'] = False
            return redirect(url_for('index'))
        else:
            flash(t('login_wrong_password'), 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    lang = session.get('lang')
    session.clear()
    if lang:
        session['lang'] = lang
    return redirect(url_for('login'))

# ── Main ──────────────────────────────────────────────────────────────────────

@app.route('/')
@require_login
def index():
    conn = get_db()
    month = current_month()
    players = conn.execute('SELECT * FROM players').fetchall()
    tasks = conn.execute('SELECT * FROM tasks WHERE active=1 ORDER BY name').fetchall()

    scores = {}
    for p in players:
        row = conn.execute(
            'SELECT COALESCE(SUM(points),0) as total FROM entries WHERE player_id=? AND month=?',
            (p['id'], month)
        ).fetchone()
        scores[p['id']] = row['total']

    recent = conn.execute('''
        SELECT e.id, e.created_at, e.points, e.note,
               p.name as player_name, p.color as player_color,
               t.name as task_name, t.icon as task_icon
        FROM entries e
        JOIN players p ON e.player_id = p.id
        JOIN tasks t ON e.task_id = t.id
        WHERE e.month = ?
        ORDER BY e.created_at DESC
        LIMIT 20
    ''', (month,)).fetchall()

    conn.close()
    month_label = datetime.strptime(month, '%Y-%m').strftime('%B %Y')
    return render_template('index.html',
        players=players, tasks=tasks, scores=scores,
        recent=recent, month_label=month_label, is_admin=session.get('is_admin'))

@app.route('/add_entry', methods=['POST'])
@require_login
def add_entry():
    player_id = request.form.get('player_id', type=int)
    task_id = request.form.get('task_id', type=int)
    note = request.form.get('note', '').strip()
    conn = get_db()
    task = conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if task:
        conn.execute(
            'INSERT INTO entries (player_id, task_id, points, note, created_at, month) VALUES (?,?,?,?,?,?)',
            (player_id, task_id, task['points'], note or None,
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_month())
        )
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
@require_login
def delete_entry(entry_id):
    if not session.get('is_admin'):
        flash(t('admin_only'), 'error')
        return redirect(url_for('index'))
    conn = get_db()
    conn.execute('DELETE FROM entries WHERE id=?', (entry_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ── History ───────────────────────────────────────────────────────────────────

@app.route('/history')
@require_login
def history():
    conn = get_db()
    months = conn.execute('SELECT DISTINCT month FROM entries ORDER BY month DESC').fetchall()
    players = conn.execute('SELECT * FROM players').fetchall()
    archive = []
    for m in months:
        mo = m['month']
        scores = {}
        for p in players:
            row = conn.execute(
                'SELECT COALESCE(SUM(points),0) as total FROM entries WHERE player_id=? AND month=?',
                (p['id'], mo)
            ).fetchone()
            scores[p['id']] = row['total']
        label = datetime.strptime(mo, '%Y-%m').strftime('%B %Y')
        archive.append({'month': mo, 'label': label, 'scores': scores})
    conn.close()
    return render_template('history.html', archive=archive, players=players, is_admin=session.get('is_admin'))

@app.route('/history/<month>')
@require_login
def history_detail(month):
    conn = get_db()
    players = conn.execute('SELECT * FROM players').fetchall()
    entries = conn.execute('''
        SELECT e.created_at, e.points, e.note,
               p.name as player_name, p.color as player_color,
               t.name as task_name, t.icon as task_icon
        FROM entries e
        JOIN players p ON e.player_id = p.id
        JOIN tasks t ON e.task_id = t.id
        WHERE e.month = ?
        ORDER BY e.created_at DESC
    ''', (month,)).fetchall()
    scores = {}
    for p in players:
        row = conn.execute(
            'SELECT COALESCE(SUM(points),0) as total FROM entries WHERE player_id=? AND month=?',
            (p['id'], month)
        ).fetchone()
        scores[p['id']] = row['total']
    conn.close()
    label = datetime.strptime(month, '%Y-%m').strftime('%B %Y')
    return render_template('history_detail.html', entries=entries, players=players,
                           scores=scores, label=label, is_admin=session.get('is_admin'))

# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@require_login
@require_admin
def admin():
    conn = get_db()
    tasks = conn.execute('SELECT * FROM tasks ORDER BY active DESC, name').fetchall()
    players = conn.execute('SELECT * FROM players').fetchall()
    conn.close()
    return render_template('admin.html', tasks=tasks, players=players, is_admin=True)

@app.route('/admin/task/add', methods=['POST'])
@require_login
@require_admin
def add_task():
    name = request.form.get('name', '').strip()
    points = request.form.get('points', type=int, default=1)
    icon = request.form.get('icon', '🏠').strip()
    if name:
        conn = get_db()
        conn.execute('INSERT INTO tasks (name, points, icon) VALUES (?,?,?)', (name, points, icon))
        conn.commit()
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/task/edit/<int:task_id>', methods=['POST'])
@require_login
@require_admin
def edit_task(task_id):
    name = request.form.get('name', '').strip()
    points = request.form.get('points', type=int, default=1)
    icon = request.form.get('icon', '🏠').strip()
    active = 1 if request.form.get('active') else 0
    conn = get_db()
    conn.execute('UPDATE tasks SET name=?, points=?, icon=?, active=? WHERE id=?',
                 (name, points, icon, active, task_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/task/delete/<int:task_id>', methods=['POST'])
@require_login
@require_admin
def delete_task(task_id):
    conn = get_db()
    conn.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/player/edit/<int:player_id>', methods=['POST'])
@require_login
@require_admin
def edit_player(player_id):
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#4f46e5')
    if name:
        conn = get_db()
        conn.execute('UPDATE players SET name=?, color=? WHERE id=?', (name, color, player_id))
        conn.commit()
        conn.close()
    return redirect(url_for('admin'))

# ── Startup ───────────────────────────────────────────────────────────────────

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

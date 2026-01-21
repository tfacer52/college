import sqlite3 # импорт sqlite3,flask и других необходимых модулей
from flask import Flask, render_template, request, redirect, session, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash # Для хеширования паролей
from functools import wraps # Для декораторов
from datetime import datetime # Для даты и времени

# flask приложение
app = Flask(__name__)
app.secret_key = "secret123" # Секретный ключ для работы с сессиями

# Функция подключения к базе данных
def db_connect():
    conn = sqlite3.connect("college.db") # Подключение к Базе Данных
    conn.row_factory = sqlite3.Row # Доступ к колонкам по имени,а не по индексу
    return conn

# СОЗДАНИЕ ТАБЛИЦ

with db_connect() as db:

    # Таблица пользователей

    # если нет таблицы users,то создаем ее

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'student'
        )
    """)

    # Таблица новостей

    # если нет таблицы news,то создаем ее

    db.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

# СОЗДАНИЕ АДМИНА

with db_connect() as db:
    # Проверка наличия администратора
    admin = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if not admin:
        # Если нет — создаём
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )
        db.commit()

# ДЕКОРАТОРЫ

# Проверка авторизации
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login")) # если не был авторизован или нет сессии,то перенаправляем на страницу логина
        return f(*args, **kwargs)
    return wrapper

# Проверка прав администратора
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403) # если это не админ,то выдается ошибка 403
        return f(*args, **kwargs)
    return wrapper

# МАРШРУТЫ

# @app.route - связан с ссылкой на приложение Flask и определяет, какая функция будет вызвана при обращении к этой ссылке

# Главная страница
@app.route("/")
def index():
    return render_template("index.html")

# Регистрация
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        with db_connect() as db:
            try:
                # Добавление нового пользователя
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (
                        request.form["username"],
                        generate_password_hash(request.form["password"])
                    )
                )
                db.commit()
            except:
                return "Пользователь уже существует"

        return redirect(url_for("login"))

    return render_template("register.html")

# Авторизация
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with db_connect() as db:
            # Поиск пользователя
            user = db.execute(
                "SELECT * FROM users WHERE username=?",
                (request.form["username"],)
            ).fetchone()

        # Проверка пароля
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user"] = user["username"] # Сохраняем имя пользователя
            session["role"] = user["role"]   # Сохраняем роль
            session["user_id"] = user["id"]  # Сохраняем ID
            return redirect(url_for("index"))

        return render_template("login.html", error="Неверные данные")

    return render_template("login.html")

# Выход из аккаунта
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# АДМИН-ПАНЕЛЬ

@app.route("/admin")
@login_required # Проверка авторизации, требуется логин
@admin_required # Проверка прав администратора, требуется роль админа
def admin_panel():
    with db_connect() as db:
        users = db.execute("SELECT id, username, role FROM users").fetchall()
        news = db.execute("SELECT * FROM news ORDER BY id DESC").fetchall()

    return render_template("admin.html", users=users, news=news)

# Изменение роли пользователя
@app.route("/admin/set_role/<int:user_id>/<role>")
@login_required
@admin_required
def set_role(user_id, role):
    if role not in ["admin", "student"]:
        abort(400)

    with db_connect() as db:
        db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        db.commit()

    return redirect("/admin")

# Удаление пользователя
@app.route("/admin/delete_user/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    if session.get("user_id") == user_id:
        return "Нельзя удалить самого себя"

    with db_connect() as db:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()

    return redirect("/admin")

# Удаление новости (из админки)
@app.route("/admin/delete_news/<int:news_id>")
@login_required
@admin_required
def admin_delete_news(news_id):
    with db_connect() as db:
        db.execute("DELETE FROM news WHERE id=?", (news_id,))
        db.commit()

    return redirect("/admin")

# НОВОСТИ

@app.route("/news", methods=["GET", "POST"])
def news():
    with db_connect() as db:
        if request.method == "POST":
            if "user" not in session:
                return redirect("/login")

            # Добавление новости
            db.execute(
                "INSERT INTO news (title, content, created_at) VALUES (?, ?, ?)",
                (
                    request.form["title"],
                    request.form["content"],
                    datetime.now().strftime("%d.%m.%Y %H:%M")
                )
            )
            db.commit()

        # Получение всех новостей
        news_list = db.execute(
            "SELECT * FROM news ORDER BY id DESC"
        ).fetchall()

    return render_template("news.html", news=news_list)

# Удаление новости
@app.route("/news/delete/<int:id>")
@login_required
@admin_required
def delete_news(id):
    with db_connect() as db:
        db.execute("DELETE FROM news WHERE id=?", (id,))
        db.commit()
    return redirect("/news")

# Другие страницы

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/specialties")
def specialties():
    return render_template("specialties.html")

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

# Запуск приложения
if __name__== "__main__":
    app.run(host="0.0.0.0")
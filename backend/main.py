from __future__ import annotations

import hashlib
import secrets
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.getenv("YHDET_DB_PATH", str(DATA_DIR / "community.db")))
SEED_USER_PASSWORD = os.getenv("YHDET_SEED_USER_PASSWORD", "change-me")

app = FastAPI(title="易聊社区", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_AVATAR = "https://yhdet.top/static/avatars/avatar_1.png"
BANNERS = [
    {"tag": "HOT", "content": "欢迎加入易聊社区，结识更多有趣的人！", "color": "cyan"},
    {"tag": "NEW", "content": "投递广告申请请发送邮件至 F17376088816@163.COM", "color": "cyan"},
    {"tag": "NEW", "content": "AI 智能助手现已上线，快来体验对话！", "color": "pink"},
    {"tag": "EVENT", "content": "周末辩论赛进行中，等你来挑战！", "color": "yellow"},
    {"tag": "GAME", "content": "扫雷、俄罗斯方块、乒乓球...小游戏专区开放！", "color": "green"},
    {"tag": "SKIN", "content": "MINECRAFT 皮肤站上线，上传你的专属皮肤！", "color": "purple"},
]

SEED_POSTS = [
    (17, "您好 世界", "我是咩咩咩，不明不白的来到这个世界！！", "2026-06-28 13:44:06"),
    (2, "📢 【周末辩论赛】 ", "📢 【周末辩论赛】\n刚看到一个帖子问“Tab键和空格键哪个好？”，我突然很好奇咱们频道的纯度。\n\n我先自曝：我用空格，因为我觉得对齐是一种艺术。（手动狗头）\n\n你们是 Tab 党还是 空格党？或者有更邪门的（比如混用）？👇评论区扣1（Tab）或扣2（空格），让我看看谁的势力大！", "2026-06-28 12:09:45"),
    (2, "《战场风云·donk》", "虚拟战场风云起，<br>\ndonk执枪似闪电。<br>\n耳畔指令声声急，<br>\n指尖鼠标舞翩跹。<br>\n一发精准定乾坤，<br>\n团队核心稳如山。<br>\n胜利曙光映前路，<br>\n他自悠然笑开颜。", "2025-11-18 08:57:01"),
    (2, "《月下小猫》", "夜色沉沉静无声，<br>\n月光如水洒窗棂。<br>\n忽见墙角黑影动，<br>\n原是猫儿步轻盈。<br>\n眸似琉璃闪微光，<br>\n尾如墨笔绘晚风。<br>\n不惊飞鸟不扰虫，<br>\n只伴月色共从容。", "2025-11-18 08:52:22"),
    (2, "服了某些人了", "666某些人天天去飘唱，信不信给你们卖银场所扬了<br>\n!666(https://ts1.tc.mm.bing.net/th/id/OIP-C.2Ng0It4O5pyU9pDpE3EVwgHaFk?w=187&h=128&c=8&rs=1&qlt=90&o=6&cb=12&pid=3.1&rm=", "2025-10-07 16:16:46"),
    (6, "假期能不能不要离开我", "作业可以滚啦，假期留下陪我。一笔未动这让我开学怎么办？跟老师卖萌嘛？", "2025-10-07 14:56:10"),
    (2, "台风怎么还没走啊", "怎么这次的台风这么大，搞得我都没法出去玩了，气死", "2025-10-05 23:49:41"),
    (2, "禁止恶意注册账户", "禁止恶意大量注册账户，违反规定的账户将会永久封禁", "2025-10-05 08:32:50"),
    (9, "2", "2", "2025-10-05 05:57:06"),
    (8, "无标题", "我是水的主人", "2025-10-05 05:30:09"),
    (7, "2025.10.5", "到此一游", "2025-10-05 04:47:27"),
    (4, "古风小生", "小生悠哉悠哉～", "2025-10-04 16:35:43"),
    (5, "2025.10.4", "到此一游二游三游……", "2025-10-04 15:14:37"),
    (2, "社区基准守则", "一，社区守则简洁版 <br>\n 1.请勿发布违规信息（如：色情内容，赌博内容，暴力内容等） <br>\n 2.发布违规信息将封禁账户<br>\n 3.禁止发布虚假宣传广告  <br>\n二，账户规定 <br>\n 1.注册账户需填入正确的邮箱信息，管理组织将不定时对任意账户进行邮箱存在性确认", "2025-10-04 06:36:07"),
]

SEED_USERS = [
    (2, "水鱼PyLab", "admin", "超管", "论坛主", "https://ts1.tc.mm.bing.net/th/id/OIP-C.X8xHnmyg-OoNXUamtI2u_QHaHa?w=186&h=211&c=8&rs=1&qlt=90&o=6&cb=12&pid=3.1&rm=2"),
    (17, "MIE", "user", "", "", "https://yhdet.top/static/avatars/avatar_17_e1d64d9c.jpg"),
    (6, "猪妞萱", "user", "", "", "https://i.imgs.ovh/2025/10/05/7sYhhO.jpeg"),
    (9, "das", "user", "", "", "https://www.baidu.com/robots.txt"),
    (8, "水の主人", "user", "", "", "https://yhdet.top/static/avatars/avatar_5.png"),
    (7, "a", "user", "", "", DEFAULT_AVATAR),
    (4, "Sun", "user", "", "", "https://i.imgs.ovh/2025/10/04/7sPzfa.jpeg"),
    (5, "杏仁饼", "user", "", "", "https://youke1.picui.cn/s1/2025/10/01/68dd402387fe3.jpg"),
]


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == digest


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                role_label TEXT DEFAULT '',
                custom_title TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions(
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS comments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS announcements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS donors(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount TEXT NOT NULL,
                donated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS site_stats(
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            for uid, username, role, role_label, custom_title, avatar in SEED_USERS:
                conn.execute(
                    "INSERT INTO users(id, username, email, password_hash, role, role_label, custom_title, avatar, bio, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (uid, username, f"user{uid}@example.com", hash_password(SEED_USER_PASSWORD), role, role_label, custom_title, avatar, "", now()),
                )
            for user_id, title, content, created in SEED_POSTS:
                conn.execute(
                    "INSERT INTO posts(user_id,title,content,views,pinned,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (user_id, title, content, 0, 1 if title in ("社区基准守则", "禁止恶意注册账户") else 0, created, created),
                )
            conn.execute("INSERT INTO comments(post_id,user_id,content,created_at) VALUES(?,?,?,?)", (2, 17, "我选空格，缩进看着舒服。", "2026-06-28 13:00:00"))
            conn.execute("INSERT INTO announcements(user_id,content,created_at) VALUES(?,?,?)", (2, "本站于2026/6/28再次开放   祝贺！！！", "2026-06-28 11:32:13"))
            conn.execute("INSERT INTO donors(name,amount,donated_at) VALUES(?,?,?)", ("起司", "3元", "2025.10.7"))
            conn.execute("INSERT OR REPLACE INTO site_stats(key,value) VALUES('visits', 562)")


def post_row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "title": r["title"],
        "content": r["content"],
        "preview": r["content"],
        "time": r["created_at"],
        "views": r["views"],
        "comments": r["comment_count"],
        "user_id": r["user_id"],
        "author": r["username"],
        "avatar": r["avatar"] or DEFAULT_AVATAR,
        "role": r["role_label"] or ("超管" if r["role"] == "admin" else ""),
        "custom_title": r["custom_title"] or ("论坛主" if r["role"] == "admin" else ""),
        "pinned": bool(r["pinned"]),
    }


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    with db() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
            (token,),
        ).fetchone()


def require_user(user: sqlite3.Row | None) -> sqlite3.Row:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(user: sqlite3.Row | None) -> sqlite3.Row:
    user = require_user(user)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    email: str | None = None
    password: str = Field(min_length=4, max_length=128)
    email_code: str | None = None
    captcha: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str
    captcha: str | None = None


class EmailCodeIn(BaseModel):
    email: str


class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10000)


class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AdminUserIn(BaseModel):
    role: str | None = None
    role_label: str | None = None
    custom_title: str | None = None
    avatar: str | None = None
    bio: str | None = None


class AdminPostIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    pinned: bool | None = None


class AdminAnnouncementIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class AdminDonorIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: str = Field(min_length=1, max_length=80)
    donated_at: str = Field(min_length=1, max_length=40)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "db": DB_PATH.exists()}


@app.post("/api/captcha")
def captcha():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return {"code": "".join(secrets.choice(alphabet) for _ in range(5))}


@app.post("/api/send_email_code")
def send_email_code(payload: EmailCodeIn):
    if not payload.email.strip():
        return {"success": False, "message": "请先输入邮箱地址"}
    # 复刻原站交互：演示环境不实际发送邮件，验证码字段用于前台流程展示，不阻塞注册。
    return {"success": True, "message": "验证码已发送，请查收邮箱"}


def get_chrome_data(conn: sqlite3.Connection) -> dict[str, Any]:
    visits = conn.execute("SELECT value FROM site_stats WHERE key='visits'").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    donor_rows = conn.execute("SELECT * FROM donors ORDER BY id DESC LIMIT 10").fetchall()
    notice = conn.execute("SELECT a.*, u.username FROM announcements a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 1").fetchone()
    return {
        "stats": {"visits": visits, "users": users, "posts": posts},
        "banners": BANNERS,
        "donors": [{"name": d["name"], "amount": d["amount"], "date": d["donated_at"]} for d in donor_rows],
        "notice": {"text": notice["content"], "author": notice["username"], "time": notice["created_at"]} if notice else {"text": "", "author": "", "time": ""},
    }


@app.get("/api/chrome")
def chrome():
    init_db()
    with db() as conn:
        return get_chrome_data(conn)


@app.get("/api/home")
def home():
    init_db()
    with db() as conn:
        conn.execute("UPDATE site_stats SET value=value+1 WHERE key='visits'")
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            ORDER BY p.created_at DESC
            LIMIT 30
            """
        ).fetchall()
        payload = get_chrome_data(conn)
    payload["posts"] = [post_row_to_dict(r) for r in rows]
    return payload


@app.post("/api/register")
def register(payload: RegisterIn):
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(username,email,password_hash,role,avatar,bio,created_at) VALUES(?,?,?,?,?,?,?)",
                (payload.username.strip(), payload.email, hash_password(payload.password), "user", DEFAULT_AVATAR, "", now()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, cur.lastrowid, now()))
        user = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"token": token, "user": public_user(user)}


@app.post("/api/login")
def login(payload: LoginIn):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=? OR email=?", (payload.username, payload.username)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, user["id"], now()))
    return {"token": token, "user": public_user(user)}


@app.get("/api/me", response_model=None)
def me(authorization: str | None = Header(default=None)):
    found = current_user(authorization)
    return {"user": public_user(found) if found else None}


def public_user(user: sqlite3.Row | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "role_label": user["role_label"] or ("超管" if user["role"] == "admin" else ""),
        "custom_title": user["custom_title"],
        "avatar": user["avatar"] or DEFAULT_AVATAR,
        "bio": user["bio"],
        "created_at": user["created_at"],
    }


@app.get("/api/posts")
def list_posts(q: str = ""):
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            WHERE ?='' OR p.title LIKE ? OR p.content LIKE ? OR u.username LIKE ?
            ORDER BY p.pinned DESC, p.created_at DESC
            """,
            (q.strip(), like, like, like),
        ).fetchall()
    return {"items": [post_row_to_dict(r) for r in rows]}


@app.post("/api/posts")
def create_post(payload: PostIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO posts(user_id,title,content,views,pinned,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (user["id"], payload.title.strip(), payload.content.strip(), 0, 0, now(), now()),
        )
    return {"id": cur.lastrowid}


@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    with db() as conn:
        conn.execute("UPDATE posts SET views=views+1 WHERE id=?", (post_id,))
        row = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?
            """,
            (post_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="帖子不存在")
        comments = conn.execute(
            "SELECT c.*, u.username, u.avatar, u.role, u.role_label FROM comments c JOIN users u ON u.id=c.user_id WHERE c.post_id=? ORDER BY c.id ASC",
            (post_id,),
        ).fetchall()
    return {"post": post_row_to_dict(row), "comments": [{"id": c["id"], "user_id": c["user_id"], "content": c["content"], "time": c["created_at"], "author": c["username"], "avatar": c["avatar"] or DEFAULT_AVATAR, "role": c["role_label"] or ("超管" if c["role"] == "admin" else "")} for c in comments]}


@app.post("/api/posts/{post_id}/comments")
def add_comment(post_id: int, payload: CommentIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        exists = conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="帖子不存在")
        cur = conn.execute("INSERT INTO comments(post_id,user_id,content,created_at) VALUES(?,?,?,?)", (post_id, user["id"], payload.content.strip(), now()))
    return {"id": cur.lastrowid}


@app.get("/api/users")
def users(q: str = ""):
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute("SELECT * FROM users WHERE ?='' OR username LIKE ? ORDER BY id ASC", (q.strip(), like)).fetchall()
    return {"items": [public_user(u) for u in rows]}


@app.get("/api/users/{user_id}")
def user_detail(user_id: int):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id WHERE p.user_id=? ORDER BY p.created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return {"user": public_user(user), "posts": [post_row_to_dict(r) for r in rows]}


@app.get("/api/search")
def search(q: str = "", type: str = "posts"):
    if type == "users":
        return users(q)
    return list_posts(q)


def admin_comment_to_dict(c: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": c["id"],
        "post_id": c["post_id"],
        "post_title": c["post_title"],
        "user_id": c["user_id"],
        "author": c["username"],
        "content": c["content"],
        "created_at": c["created_at"],
    }


def admin_announcement_to_dict(a: sqlite3.Row) -> dict[str, Any]:
    return {"id": a["id"], "content": a["content"], "author": a["username"], "created_at": a["created_at"]}


def admin_donor_to_dict(d: sqlite3.Row) -> dict[str, Any]:
    return {"id": d["id"], "name": d["name"], "amount": d["amount"], "donated_at": d["donated_at"]}


@app.get("/api/admin/overview")
def admin_overview(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        stats = get_chrome_data(conn)["stats"]
        stats["comments"] = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        recent_posts = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            ORDER BY p.id DESC LIMIT 8
            """
        ).fetchall()
        recent_users = conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 8").fetchall()
    return {"stats": stats, "recent_posts": [post_row_to_dict(r) for r in recent_posts], "recent_users": [public_user(u) for u in recent_users]}


@app.get("/api/admin/users")
def admin_users(q: str = "", authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT u.*,
                   (SELECT COUNT(*) FROM posts p WHERE p.user_id=u.id) AS post_count,
                   (SELECT COUNT(*) FROM comments c WHERE c.user_id=u.id) AS comment_count
            FROM users u
            WHERE ?='' OR u.username LIKE ? OR COALESCE(u.email,'') LIKE ?
            ORDER BY u.id ASC
            """,
            (q.strip(), like, like),
        ).fetchall()
    items = []
    for u in rows:
        d = public_user(u)
        d.update({"email": u["email"], "post_count": u["post_count"], "comment_count": u["comment_count"]})
        items.append(d)
    return {"items": items}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, payload: AdminUserIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    allowed_roles = {"user", "admin"}
    updates: list[str] = []
    values: list[Any] = []
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in allowed_roles:
        raise HTTPException(status_code=400, detail="角色只能是 user 或 admin")
    for key in ("role", "role_label", "custom_title", "avatar", "bio"):
        if key in data:
            updates.append(f"{key}=?")
            values.append((data[key] or "").strip() if isinstance(data[key], str) else data[key])
    if not updates:
        return {"ok": True}
    values.append(user_id)
    with db() as conn:
        cur = conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", values)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True}


@app.get("/api/admin/posts")
def admin_posts(q: str = "", authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            WHERE ?='' OR p.title LIKE ? OR p.content LIKE ? OR u.username LIKE ?
            ORDER BY p.pinned DESC, p.id DESC
            LIMIT 100
            """,
            (q.strip(), like, like, like),
        ).fetchall()
    return {"items": [post_row_to_dict(r) for r in rows]}


@app.patch("/api/admin/posts/{post_id}")
def admin_update_post(post_id: int, payload: AdminPostIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    updates: list[str] = []
    values: list[Any] = []
    data = payload.model_dump(exclude_unset=True)
    for key in ("title", "content"):
        if key in data:
            updates.append(f"{key}=?")
            values.append(data[key].strip())
    if "pinned" in data:
        updates.append("pinned=?")
        values.append(1 if data["pinned"] else 0)
    if updates:
        updates.append("updated_at=?")
        values.append(now())
        values.append(post_id)
        with db() as conn:
            cur = conn.execute(f"UPDATE posts SET {', '.join(updates)} WHERE id=?", values)
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="帖子不存在")
    return {"ok": True}


@app.delete("/api/admin/posts/{post_id}")
def admin_delete_post(post_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        conn.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        cur = conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="帖子不存在")
    return {"ok": True}


@app.get("/api/admin/comments")
def admin_comments(q: str = "", authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT c.*, u.username, p.title AS post_title
            FROM comments c JOIN users u ON u.id=c.user_id JOIN posts p ON p.id=c.post_id
            WHERE ?='' OR c.content LIKE ? OR u.username LIKE ? OR p.title LIKE ?
            ORDER BY c.id DESC LIMIT 100
            """,
            (q.strip(), like, like, like),
        ).fetchall()
    return {"items": [admin_comment_to_dict(c) for c in rows]}


@app.delete("/api/admin/comments/{comment_id}")
def admin_delete_comment(comment_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="评论不存在")
    return {"ok": True}


@app.get("/api/admin/announcements")
def admin_announcements(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        rows = conn.execute("SELECT a.*, u.username FROM announcements a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 50").fetchall()
    return {"items": [admin_announcement_to_dict(a) for a in rows]}


@app.post("/api/admin/announcements")
def admin_create_announcement(payload: AdminAnnouncementIn, authorization: str | None = Header(default=None)):
    admin = require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("INSERT INTO announcements(user_id,content,created_at) VALUES(?,?,?)", (admin["id"], payload.content.strip(), now()))
    return {"id": cur.lastrowid}


@app.patch("/api/admin/announcements/{announcement_id}")
def admin_update_announcement(announcement_id: int, payload: AdminAnnouncementIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("UPDATE announcements SET content=? WHERE id=?", (payload.content.strip(), announcement_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="公告不存在")
    return {"ok": True}


@app.delete("/api/admin/announcements/{announcement_id}")
def admin_delete_announcement(announcement_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("DELETE FROM announcements WHERE id=?", (announcement_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="公告不存在")
    return {"ok": True}


@app.get("/api/admin/donors")
def admin_donors(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        rows = conn.execute("SELECT * FROM donors ORDER BY id DESC LIMIT 100").fetchall()
    return {"items": [admin_donor_to_dict(d) for d in rows]}


@app.post("/api/admin/donors")
def admin_create_donor(payload: AdminDonorIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("INSERT INTO donors(name,amount,donated_at) VALUES(?,?,?)", (payload.name.strip(), payload.amount.strip(), payload.donated_at.strip()))
    return {"id": cur.lastrowid}


@app.patch("/api/admin/donors/{donor_id}")
def admin_update_donor(donor_id: int, payload: AdminDonorIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("UPDATE donors SET name=?, amount=?, donated_at=? WHERE id=?", (payload.name.strip(), payload.amount.strip(), payload.donated_at.strip(), donor_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="捐赠记录不存在")
    return {"ok": True}


@app.delete("/api/admin/donors/{donor_id}")
def admin_delete_donor(donor_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("DELETE FROM donors WHERE id=?", (donor_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="捐赠记录不存在")
    return {"ok": True}


@app.get("/api/games")
def games():
    return {"items": ["扫雷", "俄罗斯方块", "乒乓球", "贪吃蛇"], "message": "小游戏专区开放中"}


@app.get("/api/music")
def music():
    return {"items": ["社区歌单", "随机播放", "音乐留言"], "message": "音乐专区开放中"}


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    assets = frontend_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.middleware("http")
    async def cache_static_assets(request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @app.get("/{full_path:path}")
    def spa(full_path: str, request: Request):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        index = frontend_dist / "index.html"
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

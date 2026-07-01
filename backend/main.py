from __future__ import annotations

import re
import hashlib
import secrets
import os
import json
import sqlite3
import smtplib
import urllib.error
import urllib.request
import asyncio
import time
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path
from enum import Enum
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
import io

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.getenv("YHDET_DB_PATH", str(DATA_DIR / "community.db")))
SEED_USER_PASSWORD = os.getenv("YHDET_SEED_USER_PASSWORD", "change-me")
SITE_STARTED_AT = datetime.now()

app = FastAPI(title="泓聊社区", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.middleware("http")
async def block_banned_ip(request: Request, call_next):
    if request.url.path.startswith(("/assets", "/static", "/uploads", "/favicon")):
        return await call_next(request)
    ip = client_ip(request)
    if ip:
        try:
            with db() as conn:
                if conn.execute("SELECT 1 FROM banned_identities WHERE ip<>'' AND ip=?", (ip,)).fetchone():
                    return Response("当前网络地址已被禁止访问", status_code=403, media_type="text/plain; charset=utf-8")
        except Exception:
            pass
    return await call_next(request)

DEFAULT_AVATAR = "/static/avatar.svg"
BANNERS = [
    {"tag": "HOT", "content": "欢迎加入泓聊社区，结识更多有趣的人！", "color": "cyan"},
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
    (17, "MIE", "user", "", "", DEFAULT_AVATAR),
    (6, "猪妞萱", "user", "", "", "https://i.imgs.ovh/2025/10/05/7sYhhO.jpeg"),
    (9, "das", "user", "", "", "https://www.baidu.com/robots.txt"),
    (8, "水の主人", "user", "", "", DEFAULT_AVATAR),
    (7, "a", "user", "", "", DEFAULT_AVATAR),
    (4, "Sun", "user", "", "", "https://i.imgs.ovh/2025/10/04/7sPzfa.jpeg"),
    (5, "杏仁饼", "user", "", "", "https://youke1.picui.cn/s1/2025/10/01/68dd402387fe3.jpg"),
]


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ProductCategory(str, Enum):
    MEMBER_BENEFIT = "MEMBER_BENEFIT"
    THEME_DRESSUP = "THEME_DRESSUP"
    RARE_PERK = "RARE_PERK"
    GIFT_GENERAL = "GIFT_GENERAL"
    COUPON_TICKET = "COUPON_TICKET"
    GAME_ITEM = "GAME_ITEM"
    COFFEE_SPONSOR = "COFFEE_SPONSOR"
    PERIPHERAL_PHYSICAL = "PERIPHERAL_PHYSICAL"


class FulfillmentMethod(str, Enum):
    DIRECT_EFFECT = "DIRECT_EFFECT"
    CARD_KEY = "CARD_KEY"
    MANUAL_PROCESS = "MANUAL_PROCESS"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PENDING_AUDIT = "PENDING_AUDIT"
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


AUDIT_MARKET_TITLES = {"改名卡": "rename", "头衔申请券": "title", "自定义头衔卡": "title"}
USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
DEFAULT_AVATAR_BORDER_STYLE = "#FFFFFF"
AVATAR_BORDER_PRODUCTS = {
    "avatar_border_green": {"title": "头像颜色卡·绿色", "tier": "初级", "price": 20, "style": "#34D399", "icon": "fa-circle", "desc": "绿色头像外环，清爽初级身份标识。"},
    "avatar_border_blue": {"title": "头像颜色卡·蓝色", "tier": "标准", "price": 40, "style": "#60A5FA", "icon": "fa-circle", "desc": "蓝色头像外环，标准活跃成员标识。"},
    "avatar_border_purple": {"title": "头像颜色卡·紫色", "tier": "高级", "price": 80, "style": "#A78BFA", "icon": "fa-circle", "desc": "紫色头像外环，高级个性身份标识。"},
    "avatar_border_pink": {"title": "头像颜色卡·粉色", "tier": "幻彩", "price": 150, "style": "#F472B6", "icon": "fa-circle", "desc": "粉色头像外环，幻彩醒目身份标识。"},
    "avatar_border_gold": {"title": "头像颜色卡·金色", "tier": "至尊", "price": 300, "style": "#FBBF24", "icon": "fa-crown", "desc": "金色头像外环，至尊成员身份标识。"},
    "avatar_border_google": {"title": "谷歌至尊四色环", "tier": "神话级", "price": 500, "style": "conic-gradient(#4285F4, #EA4335, #FBBC05, #34A853, #4285F4)", "icon": "fa-gem", "desc": "谷歌官方四色渐变头像环，神话级尊贵标识。"},
}

DIRECT_EFFECT_CATEGORIES = {ProductCategory.MEMBER_BENEFIT.value, ProductCategory.THEME_DRESSUP.value, ProductCategory.RARE_PERK.value}
CARD_KEY_CATEGORIES = {ProductCategory.GIFT_GENERAL.value, ProductCategory.COUPON_TICKET.value, ProductCategory.GAME_ITEM.value}
MANUAL_PROCESS_CATEGORIES = {ProductCategory.COFFEE_SPONSOR.value, ProductCategory.PERIPHERAL_PHYSICAL.value}
ALL_PRODUCT_CATEGORIES = DIRECT_EFFECT_CATEGORIES | CARD_KEY_CATEGORIES | MANUAL_PROCESS_CATEGORIES
CATEGORY_METHOD = {**{c: FulfillmentMethod.DIRECT_EFFECT.value for c in DIRECT_EFFECT_CATEGORIES}, **{c: FulfillmentMethod.CARD_KEY.value for c in CARD_KEY_CATEGORIES}, **{c: FulfillmentMethod.MANUAL_PROCESS.value for c in MANUAL_PROCESS_CATEGORIES}}
LEGACY_CATEGORY_MAP = {
    "virtual": ProductCategory.GIFT_GENERAL.value,
    "profile": ProductCategory.MEMBER_BENEFIT.value,
    "content": ProductCategory.RARE_PERK.value,
}


def normalize_market_category(category: str | None) -> str:
    raw = (category or "").strip()
    category = LEGACY_CATEGORY_MAP.get(raw, raw or ProductCategory.GIFT_GENERAL.value)
    if category not in ALL_PRODUCT_CATEGORIES:
        raise HTTPException(status_code=400, detail="商品分类不合法")
    return category


def fulfillment_method(category: str | None) -> str:
    return CATEGORY_METHOD[normalize_market_category(category)]


def market_item_fulfillment_method(item: sqlite3.Row | dict[str, Any]) -> str:
    category = normalize_market_category(item["category"] if isinstance(item, dict) else item["category"])
    title = (item.get("title") if isinstance(item, dict) else item["title"] if "title" in item.keys() else "") or ""
    if category == ProductCategory.MEMBER_BENEFIT.value and title in AUDIT_MARKET_TITLES:
        return FulfillmentMethod.MANUAL_PROCESS.value
    return fulfillment_method(category)


def market_order_to_dict(o: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": o["id"],
        "item_id": o["item_id"],
        "title": o["title"] if "title" in o.keys() else o["item_title"],
        "item_title": o["title"] if "title" in o.keys() else o["item_title"],
        "price": o["price"],
        "cost_points": o["cost_points"],
        "status": o["status"],
        "category": o["category"],
        "shipping_info": o["shipping_info"],
        "payload": o["payload"] if "payload" in o.keys() else "",
        "delivered_content": o["delivered_content"],
        "created_at": o["created_at"],
        "fulfilled_at": o["fulfilled_at"],
        "cover_icon": o["cover_icon"] if "cover_icon" in o.keys() else "fa-gift",
    }


def human_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}天{hours}小时"
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"


def days_between(start: str | None, end: datetime | None = None) -> int | None:
    if not start:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(start[:19], fmt)
            return max(0, ((end or datetime.now()) - dt).days)
        except Exception:
            continue
    return None


def default_settings() -> dict[str, str]:
    return {
        "site_name": "泓聊社区",
        "site_logo": "",
        "default_avatar": DEFAULT_AVATAR,
        "email_enabled": "0",
        "smtp_host": "",
        "smtp_port": "465",
        "smtp_user": "",
        "smtp_password": "",
        "smtp_from": "",
        "comment_email_limit_24h": "8",
        "banners_json": json.dumps(BANNERS, ensure_ascii=False),
    }


def get_settings(conn: sqlite3.Connection, include_secret: bool = False) -> dict[str, Any]:
    data = default_settings()
    try:
        rows = conn.execute("SELECT key,value FROM site_settings").fetchall()
        for r in rows:
            data[r["key"]] = r["value"]
    except sqlite3.OperationalError:
        pass
    if not include_secret and data.get("smtp_password"):
        data["smtp_password"] = "***"
    data["email_enabled"] = str(data.get("email_enabled", "0")) in {"1", "true", "True", "yes"}
    try:
        data["comment_email_limit_24h"] = int(data.get("comment_email_limit_24h") or 8)
    except Exception:
        data["comment_email_limit_24h"] = 8
    return data


def get_banners_from_settings(settings: dict[str, Any]) -> list[dict[str, str]]:
    raw = settings.get("banners_json") or ""
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            cleaned = []
            for item in items[:12]:
                if not isinstance(item, dict):
                    continue
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                cleaned.append({
                    "tag": str(item.get("tag") or "公告").strip()[:12],
                    "content": content[:180],
                    "color": str(item.get("color") or "cyan").strip()[:20],
                })
            if cleaned:
                return cleaned
    except Exception:
        pass
    return BANNERS


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute("INSERT OR REPLACE INTO site_settings(key,value) VALUES(?,?)", (key, str(value or "")))


def current_default_avatar(conn: sqlite3.Connection) -> str:
    return str(get_settings(conn).get("default_avatar") or DEFAULT_AVATAR)


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
                avatar_border_style TEXT DEFAULT '#FFFFFF',
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
            CREATE TABLE IF NOT EXISTS channels(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'manual',
                enabled INTEGER NOT NULL DEFAULT 1,
                source_type TEXT DEFAULT '',
                endpoint_url TEXT DEFAULT '',
                auth_type TEXT DEFAULT 'none',
                auth_secret_ref TEXT DEFAULT '',
                mapping_json TEXT DEFAULT '{}',
                last_sync_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS channel_posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_name TEXT DEFAULT '管理员',
                external_id TEXT DEFAULT '',
                external_url TEXT DEFAULT '',
                source_payload_json TEXT DEFAULT '{}',
                views INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(channel_id, external_id),
                FOREIGN KEY(channel_id) REFERENCES channels(id)
            );
            CREATE TABLE IF NOT EXISTS channel_comments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(channel_post_id) REFERENCES channel_posts(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS site_settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS comment_notifications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                comment_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                read_at TEXT DEFAULT '',
                email_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(actor_id) REFERENCES users(id),
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(comment_id) REFERENCES comments(id)
            );
            CREATE TABLE IF NOT EXISTS email_notification_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                comment_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS email_verification_codes(
                email TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS banned_identities(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT DEFAULT '',
                email TEXT DEFAULT '',
                ip TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                banned_at TEXT NOT NULL,
                banned_by INTEGER,
                data_json TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS market_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price INTEGER NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT -1,
                category TEXT DEFAULT 'virtual',
                cover_icon TEXT DEFAULT 'fa-gift',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS point_ledger(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                ref_type TEXT DEFAULT '',
                ref_id INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, reason, ref_type, ref_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS market_orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                price INTEGER NOT NULL,
                category TEXT NOT NULL DEFAULT 'GIFT_GENERAL',
                cost_points INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                shipping_info TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL DEFAULT '',
                delivered_content TEXT NOT NULL DEFAULT '',
                fulfilled_at TEXT DEFAULT '',
                fulfilled_by INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(item_id) REFERENCES market_items(id),
                FOREIGN KEY(fulfilled_by) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS user_points(
                user_id INTEGER PRIMARY KEY,
                available_points INTEGER NOT NULL DEFAULT 0,
                total_earned INTEGER NOT NULL DEFAULT 0,
                current_streak INTEGER NOT NULL DEFAULT 0,
                last_checkin_date TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS product_card_keys(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                key_content TEXT NOT NULL,
                is_used INTEGER NOT NULL DEFAULT 0,
                order_id INTEGER,
                used_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(product_id, key_content),
                FOREIGN KEY(product_id) REFERENCES market_items(id),
                FOREIGN KEY(order_id) REFERENCES market_orders(id)
            );
            CREATE INDEX IF NOT EXISTS idx_market_items_category_active ON market_items(category, enabled, id);
            CREATE INDEX IF NOT EXISTS idx_market_orders_user_created ON market_orders(user_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_market_orders_status_created ON market_orders(status, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_card_keys_product_used ON product_card_keys(product_id, is_used, id);
            CREATE INDEX IF NOT EXISTS idx_point_ledger_user_created ON point_ledger(user_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_user_points_available ON user_points(available_points);
            CREATE INDEX IF NOT EXISTS idx_posts_pinned_created_id ON posts(pinned DESC, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_user_created ON posts(user_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_title ON posts(title);
            CREATE INDEX IF NOT EXISTS idx_posts_content ON posts(content);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
            CREATE INDEX IF NOT EXISTS idx_channel_posts_channel_created ON channel_posts(channel_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON comment_notifications(user_id, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_email_log_post_user_created ON email_notification_log(user_id, post_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_verification_codes(expires_at);
            """
        )
        for ddl in (
            "ALTER TABLE comments ADD COLUMN reply_to_comment_id INTEGER",
            "ALTER TABLE comments ADD COLUMN updated_at TEXT DEFAULT ''",
            "ALTER TABLE comments ADD COLUMN deleted_at TEXT DEFAULT ''",
            "ALTER TABLE comments ADD COLUMN deleted_by INTEGER",
            "ALTER TABLE comments ADD COLUMN deleted_by_admin INTEGER NOT NULL DEFAULT 0",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        for ddl in (
            "ALTER TABLE users ADD COLUMN account_status TEXT NOT NULL DEFAULT 'active'",
            "ALTER TABLE users ADD COLUMN frozen_until TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN banned_at TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN ban_reason TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN register_ip TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN last_login_ip TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN deleted_at TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN vip_until TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN unlocked_themes TEXT DEFAULT '[]'",
            "ALTER TABLE users ADD COLUMN rare_perks TEXT DEFAULT '[]'",
            "ALTER TABLE users ADD COLUMN avatar_border_style TEXT DEFAULT '#FFFFFF'",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        for ddl in (
            "ALTER TABLE market_orders ADD COLUMN category TEXT NOT NULL DEFAULT 'GIFT_GENERAL'",
            "ALTER TABLE market_orders ADD COLUMN cost_points INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE market_orders ADD COLUMN shipping_info TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE market_orders ADD COLUMN payload TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE market_orders ADD COLUMN delivered_content TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE market_orders ADD COLUMN fulfilled_at TEXT DEFAULT ''",
            "ALTER TABLE market_orders ADD COLUMN fulfilled_by INTEGER",
            "ALTER TABLE market_items ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        conn.execute("UPDATE market_items SET category=CASE category WHEN 'virtual' THEN 'GIFT_GENERAL' WHEN 'profile' THEN 'MEMBER_BENEFIT' WHEN 'content' THEN 'RARE_PERK' ELSE category END WHERE category IN ('virtual','profile','content')")
        conn.execute("UPDATE market_orders SET status='SUCCESS' WHERE status='completed'")
        conn.execute("UPDATE market_orders SET cost_points=price WHERE COALESCE(cost_points,0)=0")
        conn.execute("UPDATE market_orders SET category=(SELECT COALESCE(mi.category,'GIFT_GENERAL') FROM market_items mi WHERE mi.id=market_orders.item_id) WHERE COALESCE(category,'')='' OR category='GIFT_GENERAL'")
        conn.execute("""
            INSERT OR IGNORE INTO user_points(user_id, available_points, total_earned, current_streak, last_checkin_date, updated_at)
            SELECT u.id,
                   COALESCE((SELECT SUM(delta) FROM point_ledger l WHERE l.user_id=u.id),0),
                   COALESCE((SELECT SUM(delta) FROM point_ledger l WHERE l.user_id=u.id AND delta>0),0),
                   0,
                   '',
                   ?
            FROM users u WHERE COALESCE(u.deleted_at,'')=''
        """, (now(),))
        conn.execute("""
            UPDATE user_points
            SET available_points=COALESCE((SELECT SUM(delta) FROM point_ledger l WHERE l.user_id=user_points.user_id),0),
                total_earned=COALESCE((SELECT SUM(delta) FROM point_ledger l WHERE l.user_id=user_points.user_id AND delta>0),0),
                updated_at=?
        """, (now(),))
        conn.execute("UPDATE point_ledger SET reason='post_reward' WHERE reason='发布帖子'")
        conn.execute("UPDATE point_ledger SET reason='comment_reward' WHERE reason='发表评论'")
        conn.execute("UPDATE point_ledger SET reason='purchase_item' WHERE reason LIKE '兑换：%'")
        conn.execute("UPDATE point_ledger SET reason='purchase_item' WHERE reason='兑换商品'")
        conn.execute("UPDATE market_items SET category=? WHERE category NOT IN (?,?,?,?,?,?,?,?)", (ProductCategory.GIFT_GENERAL.value, *sorted(ALL_PRODUCT_CATEGORIES)))
        conn.execute("UPDATE users SET avatar=? WHERE avatar LIKE 'https://yhdet.top/static/avatars/%'", (DEFAULT_AVATAR,))
        conn.execute("INSERT OR IGNORE INTO site_settings(key,value) VALUES('default_avatar', ?)", (DEFAULT_AVATAR,))
        conn.execute("UPDATE site_settings SET value=? WHERE key='default_avatar' AND value LIKE 'https://yhdet.top/static/avatars/%'", (DEFAULT_AVATAR,))
        market_seed = [
            ("改名卡", "兑换后提交想修改的新昵称，管理员审核后处理。", 188, 20, ProductCategory.MEMBER_BENEFIT.value, "fa-id-card", '{"request_type":"rename"}'),
            ("头衔申请券", "提交你想展示的个人头衔，管理员审核后处理。", 288, 10, ProductCategory.MEMBER_BENEFIT.value, "fa-crown", '{"request_type":"custom_title"}'),
            ("红色用户名", "稀有权益：用户名显示为红色，覆盖个人信息面板、帖子列表和评论区。", 520, 30, ProductCategory.RARE_PERK.value, "fa-gem", '{"perk":"red_username"}'),
        ]
        for title, desc, price, stock, category, icon, payload_json in market_seed:
            conn.execute(
                """
                INSERT INTO market_items(title,description,price,stock,category,cover_icon,enabled,payload_json,created_at,updated_at)
                SELECT ?,?,?,?,?,?,?,?,?,?
                WHERE NOT EXISTS (SELECT 1 FROM market_items WHERE title=? AND category=?)
                """,
                (title, desc, price, stock, category, icon, 1, payload_json, now(), now(), title, category),
            )
        for key, product in AVATAR_BORDER_PRODUCTS.items():
            payload_json = json.dumps({"effect":"avatar_border_style", "key":key, "style":product["style"], "tier":product["tier"]}, ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO market_items(title,description,price,stock,category,cover_icon,enabled,payload_json,created_at,updated_at)
                SELECT ?,?,?,?,?,?,?,?,?,?
                WHERE NOT EXISTS (SELECT 1 FROM market_items WHERE title=? AND category=?)
                """,
                (product["title"], product["desc"], product["price"], -1, ProductCategory.THEME_DRESSUP.value, product["icon"], 1, payload_json, now(), now(), product["title"], ProductCategory.THEME_DRESSUP.value),
            )
            conn.execute(
                "UPDATE market_items SET description=?, category=?, cover_icon=?, payload_json=?, updated_at=? WHERE title=?",
                (product["desc"], ProductCategory.THEME_DRESSUP.value, product["icon"], payload_json, now(), product["title"]),
            )
        conn.execute("UPDATE users SET avatar_border_style=? WHERE COALESCE(avatar_border_style,'')=''", (DEFAULT_AVATAR_BORDER_STYLE,))
        conn.execute("UPDATE market_items SET description=?, payload_json=?, category=?, cover_icon=?, price=CASE WHEN COALESCE(price,0)<=0 THEN 188 ELSE price END, updated_at=? WHERE title='改名卡'", ("兑换后提交想修改的新昵称，管理员审核后处理。", '{"request_type":"rename"}', ProductCategory.MEMBER_BENEFIT.value, 'fa-id-card', now()))
        conn.execute("UPDATE market_items SET description=?, payload_json=?, category=?, cover_icon=?, price=CASE WHEN COALESCE(price,0)<=0 THEN 288 ELSE price END, stock=CASE WHEN COALESCE(stock,0)=0 THEN 10 ELSE stock END, updated_at=? WHERE title='头衔申请券'", ("提交你想展示的个人头衔，管理员审核后处理。", '{"request_type":"custom_title"}', ProductCategory.MEMBER_BENEFIT.value, 'fa-crown', now()))
        if conn.execute("SELECT COUNT(*) FROM users WHERE COALESCE(deleted_at,'')='' ").fetchone()[0] == 0:
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


def client_ip(request: Request | None) -> str:
    if not request:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:80]
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()[:80]
    return (request.client.host if request.client else "")[:80]


def is_frozen(user: sqlite3.Row) -> bool:
    until = (user["frozen_until"] if "frozen_until" in user.keys() else "") or ""
    return bool(until and until > now())


def account_block_message(user: sqlite3.Row) -> str | None:
    status = (user["account_status"] if "account_status" in user.keys() else "active") or "active"
    if status == "banned":
        return "账号已被永久封禁"
    if status == "frozen" and is_frozen(user):
        until = user["frozen_until"] or ""
        try:
            dt = datetime.strptime(until, "%Y-%m-%d %H:%M:%S")
            days = max(1, (dt - datetime.now()).days + 1)
            return f"账号已被冻结，剩余约 {days} 天"
        except Exception:
            return "账号已被冻结"
    return None


def ensure_account_active(conn: sqlite3.Connection, user: sqlite3.Row) -> None:
    msg = account_block_message(user)
    if msg:
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        raise HTTPException(status_code=403, detail=msg)


def send_account_notice(conn: sqlite3.Connection, user: sqlite3.Row, subject: str, body: str) -> None:
    email = (user["email"] if "email" in user.keys() else "") or ""
    if not email:
        return
    settings = get_settings(conn, include_secret=True)
    if not settings.get("email_enabled"):
        return
    try:
        send_smtp_mail(settings, email, subject, body)
    except Exception:
        # 后台操作不能因为邮件失败而中断；管理员仍可在封禁记录里查看状态。
        pass


def user_has_perk(row: sqlite3.Row | None, perk: str) -> bool:
    if not row or "rare_perks" not in row.keys():
        return False
    try:
        perks = json.loads(row["rare_perks"] or "[]")
    except Exception:
        perks = []
    return perk in perks


def user_display_flags(row: sqlite3.Row | None) -> dict[str, Any]:
    return {"red_username": user_has_perk(row, "red_username")}


def post_row_to_dict(r: sqlite3.Row, default_avatar: str = DEFAULT_AVATAR) -> dict[str, Any]:
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
        "avatar": r["avatar"] or default_avatar,
        "avatar_border_style": (r["avatar_border_style"] if "avatar_border_style" in r.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE,
        "role": r["role_label"] or ("超管" if r["role"] == "admin" else ""),
        "custom_title": r["custom_title"] or ("论坛主" if r["role"] == "admin" else ""),
        "pinned": bool(r["pinned"]),
        "display_flags": user_display_flags(r),
    }


def comment_row_to_dict(c: sqlite3.Row, viewer: sqlite3.Row | None = None) -> dict[str, Any]:
    is_deleted = bool((c["deleted_at"] if "deleted_at" in c.keys() else "") or "")
    can_manage = bool(viewer and not is_deleted and (viewer["id"] == c["user_id"] or viewer["role"] == "admin"))
    reply_deleted = bool((c["reply_deleted_at"] if "reply_deleted_at" in c.keys() else "") or "")
    updated_at = (c["updated_at"] if "updated_at" in c.keys() else "") or ""
    created_at = c["created_at"]
    return {
        "id": c["id"],
        "user_id": c["user_id"],
        "content": "" if is_deleted else c["content"],
        "time": created_at,
        "updated_at": updated_at,
        "edited": bool(updated_at and updated_at != created_at and not is_deleted),
        "deleted": is_deleted,
        "deleted_at": (c["deleted_at"] if "deleted_at" in c.keys() else "") or "",
        "deleted_by_admin": bool(c["deleted_by_admin"] if "deleted_by_admin" in c.keys() else 0),
        "author": c["username"],
        "avatar": c["avatar"] or DEFAULT_AVATAR,
        "avatar_border_style": (c["avatar_border_style"] if "avatar_border_style" in c.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE,
        "role": c["role_label"] or ("超管" if c["role"] == "admin" else ""),
        "reply_to_comment_id": c["reply_to_comment_id"] if "reply_to_comment_id" in c.keys() else None,
        "reply_to_user_id": None if reply_deleted else (c["reply_user_id"] if "reply_user_id" in c.keys() else None),
        "reply_to_author": None if reply_deleted else (c["reply_author"] if "reply_author" in c.keys() else None),
        "reply_to_avatar": DEFAULT_AVATAR if reply_deleted else ((c["reply_avatar"] if "reply_avatar" in c.keys() else "") or DEFAULT_AVATAR),
        "reply_to_preview": "" if reply_deleted else ((c["reply_content"] or "")[:120] if "reply_content" in c.keys() and c["reply_content"] else ""),
        "reply_to_deleted": reply_deleted,
        "can_edit": can_manage,
        "can_delete": can_manage,
        "display_flags": user_display_flags(c),
    }


def fetch_post_dict(conn: sqlite3.Connection, post_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id AND (COALESCE(c.deleted_at,'')='' OR EXISTS (SELECT 1 FROM comments child WHERE child.reply_to_comment_id=c.id AND child.post_id=c.post_id))) AS comment_count
        FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?
        """,
        (post_id,),
    ).fetchone()
    return post_row_to_dict(row) if row else None


def fetch_comment_dict(conn: sqlite3.Connection, post_id: int, comment_id: int, viewer: sqlite3.Row | None = None) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT c.*, u.username, u.avatar, u.avatar_border_style, u.role, u.role_label, u.rare_perks,
               ru.id AS reply_user_id, ru.username AS reply_author, ru.avatar AS reply_avatar,
               rc.content AS reply_content, rc.deleted_at AS reply_deleted_at
        FROM comments c
        JOIN users u ON u.id=c.user_id
        LEFT JOIN comments rc ON rc.id=c.reply_to_comment_id AND rc.post_id=c.post_id
        LEFT JOIN users ru ON ru.id=rc.user_id
        WHERE c.id=? AND c.post_id=?
        """,
        (comment_id, post_id),
    ).fetchone()
    return comment_row_to_dict(row, viewer) if row else None


def fetch_market_order_dict(conn: sqlite3.Connection, order_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT o.*, mi.title, mi.cover_icon FROM market_orders o
        LEFT JOIN market_items mi ON mi.id=o.item_id
        WHERE o.id=?
        """,
        (order_id,),
    ).fetchone()
    return market_order_to_dict(row) if row else None


def fetch_admin_market_order_dict(conn: sqlite3.Connection, order_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT o.*, u.username, mi.title AS item_title, mi.cover_icon FROM market_orders o
        JOIN users u ON u.id=o.user_id
        LEFT JOIN market_items mi ON mi.id=o.item_id
        WHERE o.id=?
        """,
        (order_id,),
    ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "item_title": row["item_title"], "price": row["price"], "cost_points": row["cost_points"], "category": row["category"], "status": row["status"], "shipping_info": row["shipping_info"], "payload": row["payload"] if "payload" in row.keys() else "", "delivered_content": row["delivered_content"], "created_at": row["created_at"], "fulfilled_at": row["fulfilled_at"]}


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    with db() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND COALESCE(u.deleted_at,'')=''",
            (token,),
        ).fetchone()


def require_user(user: sqlite3.Row | None) -> sqlite3.Row:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    with db() as conn:
        ensure_account_active(conn, user)
    return user


def require_admin(user: sqlite3.Row | None) -> sqlite3.Row:
    user = require_user(user)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def user_from_token(token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    with db() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND COALESCE(u.deleted_at,'')=''",
            (token,),
        ).fetchone()


def presence_user_payload(user: sqlite3.Row | None, anon_id: str) -> dict[str, Any]:
    if user:
        return {
            "id": user["id"],
            "username": user["username"],
            "avatar": user["avatar"] or DEFAULT_AVATAR,
            "avatar_border_style": (user["avatar_border_style"] if "avatar_border_style" in user.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE,
            "role": user["role_label"] or ("超管" if user["role"] == "admin" else ""),
            "anonymous": False,
        }
    return {"id": anon_id, "username": "访客", "avatar": DEFAULT_AVATAR, "role": "", "anonymous": True}


class TopicPresenceManager:
    def __init__(self):
        self.topics: dict[int, dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    def _topic(self, topic_id: int) -> dict[str, Any]:
        return self.topics.setdefault(topic_id, {"connections": {}, "typing": {}, "editing": {}})

    def _snapshot(self, topic_id: int, state: dict[str, Any]) -> dict[str, Any]:
        now_ts = time.time()
        state["typing"] = {k: v for k, v in state["typing"].items() if now_ts - v.get("ts", 0) < 3.2}
        state["editing"] = {k: v for k, v in state["editing"].items() if now_ts - v.get("ts", 0) < 45}
        viewers = [v["user"] for v in state["connections"].values()]
        unique = []
        seen = set()
        for u in viewers:
            key = str(u.get("id"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(u)
        return {
            "type": "presence_snapshot",
            "topic_id": topic_id,
            "online_count": len(unique),
            "viewers": unique[:5],
            "overflow": max(0, len(unique) - 5),
            "typing": [v["user"] for v in state["typing"].values()],
            "editing": [{"comment_id": int(cid), "user": v["user"]} for cid, v in state["editing"].items()],
        }

    async def connect(self, topic_id: int, websocket: WebSocket, user: sqlite3.Row | None):
        await websocket.accept()
        anon_id = f"guest-{secrets.token_hex(4)}"
        meta = {"ws": websocket, "user": presence_user_payload(user, anon_id), "last_seen": time.time()}
        async with self.lock:
            state = self._topic(topic_id)
            state["connections"][id(websocket)] = meta
            snapshot = self._snapshot(topic_id, state)
        await self.broadcast(topic_id, snapshot)

    async def disconnect(self, topic_id: int, websocket: WebSocket):
        async with self.lock:
            state = self._topic(topic_id)
            meta = state["connections"].pop(id(websocket), None)
            if meta:
                uid = str(meta["user"].get("id"))
                state["typing"].pop(uid, None)
                state["editing"] = {cid: v for cid, v in state["editing"].items() if str(v["user"].get("id")) != uid}
            snapshot = self._snapshot(topic_id, state)
            if not state["connections"]:
                self.topics.pop(topic_id, None)
                return
        await self.broadcast(topic_id, snapshot)

    async def handle(self, topic_id: int, websocket: WebSocket, payload: dict[str, Any]):
        async with self.lock:
            state = self._topic(topic_id)
            meta = state["connections"].get(id(websocket))
            if not meta:
                return
            meta["last_seen"] = time.time()
            user = meta["user"]
            uid = str(user.get("id"))
            typ = payload.get("type")
            if typ == "typing" and not user.get("anonymous"):
                state["typing"][uid] = {"user": user, "ts": time.time()}
                asyncio.create_task(self.expire_typing(topic_id, uid, state["typing"][uid]["ts"]))
            elif typ == "typing_end":
                state["typing"].pop(uid, None)
            elif typ == "editing" and not user.get("anonymous"):
                cid = str(payload.get("comment_id") or "")
                if cid:
                    state["editing"][cid] = {"user": user, "ts": time.time()}
            elif typ == "editing_end":
                cid = str(payload.get("comment_id") or "")
                if cid:
                    state["editing"].pop(cid, None)
            elif typ == "heartbeat":
                pass
            snapshot = self._snapshot(topic_id, state)
        await self.broadcast(topic_id, snapshot)

    async def expire_typing(self, topic_id: int, uid: str, ts: float):
        await asyncio.sleep(3)
        async with self.lock:
            state = self.topics.get(topic_id)
            if not state or state["typing"].get(uid, {}).get("ts") != ts:
                return
            state["typing"].pop(uid, None)
            snapshot = self._snapshot(topic_id, state)
        await self.broadcast(topic_id, snapshot)

    async def broadcast(self, topic_id: int, message: dict[str, Any]):
        state = self.topics.get(topic_id)
        if not state:
            return
        dead = []
        for key, meta in list(state["connections"].items()):
            try:
                await meta["ws"].send_json(message)
            except Exception:
                dead.append(key)
        if dead:
            async with self.lock:
                state = self.topics.get(topic_id)
                if state:
                    for key in dead:
                        state["connections"].pop(key, None)


presence_manager = TopicPresenceManager()


@app.websocket("/ws/topics/{post_id}/presence")
async def topic_presence_ws(websocket: WebSocket, post_id: int, token: str | None = None):
    user = user_from_token(token)
    await presence_manager.connect(post_id, websocket, user)
    try:
        while True:
            payload = await websocket.receive_json()
            if isinstance(payload, dict):
                await presence_manager.handle(post_id, websocket, payload)
    except WebSocketDisconnect:
        await presence_manager.disconnect(post_id, websocket)
    except Exception:
        await presence_manager.disconnect(post_id, websocket)


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
    reply_to_comment_id: int | None = None


class AdminUserIn(BaseModel):
    role: str | None = None
    role_label: str | None = None
    custom_title: str | None = None
    avatar: str | None = None
    bio: str | None = None


class AdminFreezeIn(BaseModel):
    days: int = Field(ge=1, le=3650)
    reason: str | None = Field(default='', max_length=500)


class AdminBanIn(BaseModel):
    reason: str | None = Field(default='', max_length=500)


class AdminHardDeleteIn(BaseModel):
    confirm: str | None = None


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


class SiteSettingsIn(BaseModel):
    site_name: str | None = Field(default=None, max_length=80)
    site_logo: str | None = Field(default=None, max_length=500)
    default_avatar: str | None = Field(default=None, max_length=500)
    email_enabled: bool | None = None
    smtp_host: str | None = Field(default=None, max_length=200)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = Field(default=None, max_length=200)
    smtp_password: str | None = Field(default=None, max_length=500)
    smtp_from: str | None = Field(default=None, max_length=200)
    comment_email_limit_24h: int | None = Field(default=None, ge=0, le=100)
    banners_json: str | None = Field(default=None, max_length=8000)


class NotificationReadIn(BaseModel):
    id: int | None = None


class ChannelIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default='', max_length=1000)
    mode: str = 'manual'
    enabled: bool = True
    source_type: str | None = ''
    endpoint_url: str | None = ''
    auth_type: str | None = 'none'
    auth_secret_ref: str | None = ''
    mapping_json: str | None = '{}'


class ChannelPostIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20000)
    author_name: str | None = Field(default='管理员', max_length=80)
    external_url: str | None = Field(default='', max_length=500)


class MarketBuyIn(BaseModel):
    item_id: int
    shipping_name: str | None = Field(default='', max_length=80)
    shipping_phone: str | None = Field(default='', max_length=40)
    shipping_address: str | None = Field(default='', max_length=500)
    request_note: str | None = Field(default='', max_length=500)


class MarketExchangeIn(BaseModel):
    item_id: int
    value: str = Field(min_length=1, max_length=32)


class MarketBorderExchangeIn(BaseModel):
    item_id: int


class MarketAuditIn(BaseModel):
    approved: bool
    reject_reason: str | None = Field(default='', max_length=500)


class MarketItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=1000)
    price: int = Field(ge=0, le=1000000)
    stock: int = Field(default=-1, ge=-1, le=1000000)
    category: ProductCategory = ProductCategory.GIFT_GENERAL
    cover_icon: str = Field(default='fa-gift', max_length=80)
    enabled: bool = True
    payload_json: str = Field(default='{}', max_length=4000)


class MarketKeysIn(BaseModel):
    product_id: int
    keys_text: str = Field(min_length=1, max_length=200000)


class MarketFulfillIn(BaseModel):
    delivered_content: str = Field(min_length=1, max_length=1000)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "db": DB_PATH.exists()}


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def code_digest(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}:yhdet-email-code".encode("utf-8")).hexdigest()


def smtp_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def send_smtp_mail(settings: dict[str, Any], to_email: str, subject: str, body: str) -> None:
    host = str(settings.get("smtp_host") or "").strip()
    port = int(settings.get("smtp_port") or 465)
    username = str(settings.get("smtp_user") or "").strip()
    password = str(settings.get("smtp_password") or "").strip()
    from_email = str(settings.get("smtp_from") or username).strip()
    from_name = str(settings.get("smtp_from_name") or settings.get("site_name") or "泓聊社区").strip()
    if not (host and port and username and password and from_email):
        raise HTTPException(status_code=400, detail="邮箱发送配置不完整")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(body)
    timeout = 20
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()
            if smtp_bool(settings.get("smtp_tls", "true")):
                server.starttls()
                server.ehlo()
            server.login(username, password)
            server.send_message(msg)


@app.post("/api/captcha")
def captcha():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return {"code": "".join(secrets.choice(alphabet) for _ in range(5))}


@app.post("/api/send_email_code")
def send_email_code(payload: EmailCodeIn):
    email = normalize_email(payload.email)
    if not email:
        return {"success": False, "message": "请先输入邮箱地址"}
    if "@" not in email or len(email) > 200:
        return {"success": False, "message": "邮箱格式不正确"}
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    expires = datetime.now() + timedelta(minutes=10)
    subject = "泓聊社区注册验证码"
    body = f"您的泓聊社区注册验证码是：{code}\n\n验证码 10 分钟内有效。如非本人操作，请忽略本邮件。"
    with db() as conn:
        settings = get_settings(conn, include_secret=True)
        if not settings.get("email_enabled"):
            raise HTTPException(status_code=400, detail="邮箱发送尚未启用")
        try:
            send_smtp_mail(settings, email, subject, body)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"发送验证码失败：{exc}")
        conn.execute(
            "INSERT OR REPLACE INTO email_verification_codes(email,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,?,?)",
            (email, code_digest(email, code), expires.strftime("%Y-%m-%d %H:%M:%S"), 0, now()),
        )
    return {"success": True, "message": "验证码已发送，请查收邮箱"}


def verify_email_code(conn: sqlite3.Connection, email: str, code: str | None) -> None:
    email = normalize_email(email)
    code = (code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="请填写邮箱验证码")
    row = conn.execute("SELECT * FROM email_verification_codes WHERE email=?", (email,)).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="请先获取邮箱验证码")
    if row["expires_at"] < now():
        conn.execute("DELETE FROM email_verification_codes WHERE email=?", (email,))
        raise HTTPException(status_code=400, detail="邮箱验证码已过期，请重新获取")
    if int(row["attempts"] or 0) >= 5:
        raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取")
    if row["code_hash"] != code_digest(email, code):
        conn.execute("UPDATE email_verification_codes SET attempts=attempts+1 WHERE email=?", (email,))
        raise HTTPException(status_code=400, detail="邮箱验证码不正确")
    conn.execute("DELETE FROM email_verification_codes WHERE email=?", (email,))


def get_chrome_data(conn: sqlite3.Connection) -> dict[str, Any]:
    visits = conn.execute("SELECT value FROM site_stats WHERE key='visits'").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    donor_rows = conn.execute("SELECT * FROM donors ORDER BY id DESC LIMIT 10").fetchall()
    notice = conn.execute("SELECT a.*, u.username FROM announcements a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 1").fetchone()
    settings = get_settings(conn)
    uptime_seconds = int((datetime.now() - SITE_STARTED_AT).total_seconds())
    return {
        "settings": {"site_name": settings.get("site_name"), "site_logo": settings.get("site_logo"), "default_avatar": settings.get("default_avatar")},
        "stats": {"visits": visits, "users": users, "posts": posts, "comments": comments},
        "runtime": {"started_at": SITE_STARTED_AT.strftime("%Y-%m-%d %H:%M:%S"), "uptime_seconds": uptime_seconds, "uptime_text": human_duration(uptime_seconds), "version": app.version},
        "banners": get_banners_from_settings(settings),
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
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
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
def register(payload: RegisterIn, request: Request):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="请填写邮箱")
    ip = client_ip(request)
    with db() as conn:
        if conn.execute("SELECT 1 FROM banned_identities WHERE email=? OR (ip<>'' AND ip=?)", (email, ip)).fetchone():
            raise HTTPException(status_code=403, detail="该邮箱或网络地址已被禁止注册")
        verify_email_code(conn, email, payload.email_code)
        try:
            cur = conn.execute(
                "INSERT INTO users(username,email,password_hash,role,avatar,bio,created_at,register_ip,last_login_ip) VALUES(?,?,?,?,?,?,?,?,?)",
                (payload.username.strip(), email, hash_password(payload.password), "user", current_default_avatar(conn), "", now(), ip, ip),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, cur.lastrowid, now()))
        user = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"token": token, "user": public_user(user)}


@app.post("/api/login")
def login(payload: LoginIn, request: Request):
    ip = client_ip(request)
    with db() as conn:
        if conn.execute("SELECT 1 FROM banned_identities WHERE ip<>'' AND ip=?", (ip,)).fetchone():
            raise HTTPException(status_code=403, detail="当前网络地址已被禁止访问")
        user = conn.execute("SELECT * FROM users WHERE (username=? OR email=?) AND COALESCE(deleted_at,'')=''", (payload.username, payload.username)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        ensure_account_active(conn, user)
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, user["id"], now()))
        conn.execute("UPDATE users SET last_login_ip=? WHERE id=?", (ip, user["id"]))
        user = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"token": token, "user": public_user(user)}


@app.get("/api/me", response_model=None)
def me(authorization: str | None = Header(default=None)):
    found = current_user(authorization)
    if found:
        with db() as conn:
            ensure_account_active(conn, found)
    return {"user": public_user(found) if found else None}


@app.get("/api/settings")
def public_settings():
    init_db()
    with db() as conn:
        s = get_settings(conn)
    return {"settings": {"site_name": s.get("site_name"), "site_logo": s.get("site_logo"), "default_avatar": s.get("default_avatar")}}


@app.get("/api/me/notifications")
def my_notifications(page: int = 1, page_size: int = 30, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 30), 100))
    offset_value = (page - 1) * page_size
    with db() as conn:
        rows = conn.execute(
            """
            SELECT n.*, a.username AS actor_name, p.title AS post_title
            FROM comment_notifications n
            JOIN users a ON a.id=n.actor_id
            JOIN posts p ON p.id=n.post_id
            WHERE n.user_id=? ORDER BY n.created_at DESC, n.id DESC LIMIT ? OFFSET ?
            """,
            (user["id"], page_size, offset_value),
        ).fetchall()
        unread = conn.execute("SELECT COUNT(*) FROM comment_notifications WHERE user_id=? AND COALESCE(read_at,'')=''", (user["id"],)).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM comment_notifications WHERE user_id=?", (user["id"],)).fetchone()[0]
    return {
        "unread": unread,
        "items": [{"id": r["id"], "post_id": r["post_id"], "comment_id": r["comment_id"], "actor_id": r["actor_id"], "actor_name": r["actor_name"], "post_title": r["post_title"], "message": r["message"], "read": bool(r["read_at"]), "created_at": r["created_at"]} for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": offset_value + len(rows) < total,
    }


@app.post("/api/me/notifications/read")
def mark_notifications_read(payload: NotificationReadIn | None = None, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    target_id = payload.id if payload else None
    with db() as conn:
        if target_id:
            conn.execute("UPDATE comment_notifications SET read_at=? WHERE id=? AND user_id=? AND COALESCE(read_at,'')=''", (now(), target_id, user["id"]))
        else:
            conn.execute("UPDATE comment_notifications SET read_at=? WHERE user_id=? AND COALESCE(read_at,'')=''", (now(), user["id"]))
        unread = conn.execute("SELECT COUNT(*) FROM comment_notifications WHERE user_id=? AND COALESCE(read_at,'')=''", (user["id"],)).fetchone()[0]
    return {"ok": True, "unread": unread}


@app.post("/api/me/notifications/{notification_id}/read")
def mark_one_notification_read(notification_id: int, authorization: str | None = Header(default=None)):
    return mark_notifications_read(NotificationReadIn(id=notification_id), authorization)


@app.post("/api/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    x: int = Form(0),
    y: int = Form(0),
    width: int = Form(0),
    height: int = Form(0),
    authorization: str | None = Header(default=None),
):
    user = require_user(current_user(authorization))
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像不能超过 8MB")
    if not content:
        raise HTTPException(status_code=400, detail="请选择头像文件")
    try:
        src = Image.open(io.BytesIO(content))
        src = ImageOps.exif_transpose(src).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="图片文件无法识别")

    natural_w, natural_h = src.size
    if width <= 0 or height <= 0:
        side = min(natural_w, natural_h)
        x = (natural_w - side) // 2
        y = (natural_h - side) // 2
        width = height = side
    x = max(0, min(int(x), natural_w - 1))
    y = max(0, min(int(y), natural_h - 1))
    width = max(1, min(int(width), natural_w - x))
    height = max(1, min(int(height), natural_h - y))
    box = (x, y, x + width, y + height)
    avatar = src.crop(box).resize((512, 512), Image.Resampling.LANCZOS)

    name = f"avatar_{user['id']}_{secrets.token_hex(8)}.png"
    path = UPLOAD_DIR / name
    out = io.BytesIO()
    avatar.save(out, format="PNG", optimize=True)
    path.write_bytes(out.getvalue())
    url = f"/uploads/{name}"
    with db() as conn:
        conn.execute("UPDATE users SET avatar=? WHERE id=?", (url, user["id"]))
        refreshed = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"ok": True, "url": url, "user": public_user(refreshed)}


def public_user(user: sqlite3.Row | None, default_avatar: str = DEFAULT_AVATAR) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "role_label": user["role_label"] or ("超管" if user["role"] == "admin" else ""),
        "custom_title": user["custom_title"],
        "avatar": user["avatar"] or default_avatar,
        "avatar_border_style": (user["avatar_border_style"] if "avatar_border_style" in user.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE,
        "bio": user["bio"],
        "created_at": user["created_at"],
        "account_status": user["account_status"] if "account_status" in user.keys() else "active",
        "frozen_until": user["frozen_until"] if "frozen_until" in user.keys() else "",
        "display_flags": user_display_flags(user),
    }


@app.get("/api/posts")
def list_posts(q: str = "", page: int = 1, page_size: int = 30, limit: int | None = None, offset: int | None = None, authorization: str | None = Header(default=None)):
    q_clean = q.strip()
    if q_clean or int(page or 1) > 1 or limit is not None or offset is not None:
        require_user(current_user(authorization))
    like = f"%{q_clean}%"
    if limit is not None or offset is not None:
        page_size = limit or page_size
        offset_value = max(0, int(offset or 0))
        page = (offset_value // max(1, int(page_size or 30))) + 1
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 30), 100))
    offset_value = (page - 1) * page_size
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            WHERE ?='' OR p.title LIKE ? OR p.content LIKE ? OR u.username LIKE ?
            ORDER BY p.pinned DESC, p.created_at DESC, p.id DESC
            LIMIT ? OFFSET ?
            """,
            (q_clean, like, like, like, page_size, offset_value),
        ).fetchall()
        total = conn.execute(
            """
            SELECT COUNT(*) FROM posts p JOIN users u ON u.id=p.user_id
            WHERE ?='' OR p.title LIKE ? OR p.content LIKE ? OR u.username LIKE ?
            """,
            (q_clean, like, like, like),
        ).fetchone()[0]
    return {
        "items": [post_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "limit": page_size,
        "offset": offset_value,
        "has_more": offset_value + len(rows) < total,
    }


@app.post("/api/posts")
def create_post(payload: PostIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO posts(user_id,title,content,views,pinned,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (user["id"], payload.title.strip(), payload.content.strip(), 0, 0, now(), now()),
        )
        post_id = cur.lastrowid
        award_points(conn, user["id"], 12, "发布帖子", "post", post_id)
        post = fetch_post_dict(conn, post_id)
        current_points = refresh_user_points(conn, user["id"])
    return {"ok": True, "id": post_id, "post": post, "current_points": int(current_points or 0)}


@app.get("/api/posts/{post_id}")
def get_post(post_id: int, authorization: str | None = Header(default=None)):
    viewer = current_user(authorization)
    with db() as conn:
        conn.execute("UPDATE posts SET views=views+1 WHERE id=?", (post_id,))
        row = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id AND (COALESCE(c.deleted_at,'')='' OR EXISTS (SELECT 1 FROM comments child WHERE child.reply_to_comment_id=c.id AND child.post_id=c.post_id))) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?
            """,
            (post_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="帖子不存在")
        comments = conn.execute(
            """
            SELECT c.*, u.username, u.avatar, u.avatar_border_style, u.role, u.role_label, u.rare_perks,
                   ru.id AS reply_user_id, ru.username AS reply_author, ru.avatar AS reply_avatar,
                   rc.content AS reply_content, rc.deleted_at AS reply_deleted_at
            FROM comments c
            JOIN users u ON u.id=c.user_id
            LEFT JOIN comments rc ON rc.id=c.reply_to_comment_id AND rc.post_id=c.post_id
            LEFT JOIN users ru ON ru.id=rc.user_id
            WHERE c.post_id=?
              AND (COALESCE(c.deleted_at,'')='' OR EXISTS (SELECT 1 FROM comments child WHERE child.reply_to_comment_id=c.id AND child.post_id=c.post_id))
            ORDER BY c.created_at ASC, c.id ASC
            """,
            (post_id,),
        ).fetchall()
    return {"post": post_row_to_dict(row), "comments": [comment_row_to_dict(c, viewer) for c in comments]}


def _record_comment_notification(conn: sqlite3.Connection, post: sqlite3.Row, actor: sqlite3.Row, comment_id: int, content: str) -> None:
    owner_id = post["user_id"]
    if owner_id == actor["id"]:
        return
    message = f"{actor['username']} 评论了你的帖子《{post['title']}》"
    conn.execute(
        "INSERT INTO comment_notifications(user_id,actor_id,post_id,comment_id,message,created_at) VALUES(?,?,?,?,?,?)",
        (owner_id, actor["id"], post["id"], comment_id, message, now()),
    )
    settings = get_settings(conn, include_secret=True)
    limit = int(settings.get("comment_email_limit_24h") or 8)
    if not settings.get("email_enabled") or limit <= 0:
        return
    cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    sent_count = conn.execute(
        "SELECT COUNT(*) FROM email_notification_log WHERE user_id=? AND post_id=? AND created_at>=?",
        (owner_id, post["id"], cutoff),
    ).fetchone()[0]
    if sent_count >= limit:
        return
    # 邮箱通知采用硬限流记录。实际 SMTP 发送可接入配置；当前先保证不会因海量评论刷爆邮件。
    conn.execute("INSERT INTO email_notification_log(user_id,post_id,comment_id,created_at) VALUES(?,?,?,?)", (owner_id, post["id"], comment_id, now()))
    conn.execute("UPDATE comment_notifications SET email_sent=1 WHERE comment_id=?", (comment_id,))


@app.post("/api/posts/{post_id}/comments")
async def add_comment(post_id: int, payload: CommentIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        exists = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="帖子不存在")
        reply_to_comment_id = payload.reply_to_comment_id
        if reply_to_comment_id:
            reply_exists = conn.execute("SELECT id FROM comments WHERE id=? AND post_id=?", (reply_to_comment_id, post_id)).fetchone()
            if not reply_exists:
                raise HTTPException(status_code=400, detail="回复的评论不存在")
        cur = conn.execute("INSERT INTO comments(post_id,user_id,content,reply_to_comment_id,created_at) VALUES(?,?,?,?,?)", (post_id, user["id"], payload.content.strip(), reply_to_comment_id, now()))
        comment_id = cur.lastrowid
        award_points(conn, user["id"], 3, "发表评论", "comment", comment_id)
        _record_comment_notification(conn, exists, user, comment_id, payload.content.strip())
        comment = fetch_comment_dict(conn, post_id, comment_id, user)
        comment_count = conn.execute("SELECT COUNT(*) FROM comments WHERE post_id=? AND COALESCE(deleted_at,'')=''", (post_id,)).fetchone()[0]
        current_points = refresh_user_points(conn, user["id"])
    await presence_manager.broadcast(post_id, {"type": "comment_created", "post_id": post_id, "comment_id": comment_id, "comment": comment})
    return {"ok": True, "id": comment_id, "comment": comment, "comment_count": int(comment_count or 0), "current_points": int(current_points or 0)}


@app.patch("/api/posts/{post_id}/comments/{comment_id}")
async def update_comment(post_id: int, comment_id: int, payload: CommentIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    with db() as conn:
        row = conn.execute("SELECT * FROM comments WHERE id=? AND post_id=?", (comment_id, post_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="评论不存在")
        if (row["deleted_at"] if "deleted_at" in row.keys() else ""):
            raise HTTPException(status_code=400, detail="已删除的评论不能编辑")
        if row["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="无权编辑这条评论")
        conn.execute("UPDATE comments SET content=?, updated_at=? WHERE id=?", (content, now(), comment_id))
        comment = fetch_comment_dict(conn, post_id, comment_id, user)
    await presence_manager.broadcast(post_id, {"type": "comment_updated", "post_id": post_id, "comment_id": comment_id, "comment": comment})
    return {"ok": True, "comment": comment}


@app.delete("/api/posts/{post_id}/comments/{comment_id}")
async def delete_comment(post_id: int, comment_id: int, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        row = conn.execute("SELECT * FROM comments WHERE id=? AND post_id=?", (comment_id, post_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="评论不存在")
        if row["user_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="无权删除这条评论")
        if (row["deleted_at"] if "deleted_at" in row.keys() else ""):
            return {"ok": True}
        deleted_by_admin = 1 if user["role"] == "admin" and row["user_id"] != user["id"] else 0
        conn.execute(
            "UPDATE comments SET content='', deleted_at=?, deleted_by=?, deleted_by_admin=?, updated_at=? WHERE id=?",
            (now(), user["id"], deleted_by_admin, now(), comment_id),
        )
        comment = fetch_comment_dict(conn, post_id, comment_id, user)
        has_visible_replies = conn.execute("SELECT COUNT(*) FROM comments WHERE post_id=? AND reply_to_comment_id=? AND COALESCE(deleted_at,'')=''", (post_id, comment_id)).fetchone()[0] > 0
    await presence_manager.broadcast(post_id, {"type": "comment_deleted", "post_id": post_id, "comment_id": comment_id, "comment": comment, "visible": has_visible_replies})
    return {"ok": True, "comment": comment, "visible": has_visible_replies}


@app.get("/api/users")
def users(q: str = "", page: int = 1, page_size: int = 30, limit: int | None = None, offset: int | None = None, authorization: str | None = Header(default=None)):
    q_clean = q.strip()
    if q_clean or int(page or 1) > 1 or limit is not None or offset is not None:
        require_user(current_user(authorization))
    like = f"%{q_clean}%"
    if limit is not None or offset is not None:
        page_size = limit or page_size
        offset_value = max(0, int(offset or 0))
        page = (offset_value // max(1, int(page_size or 30))) + 1
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 30), 100))
    offset_value = (page - 1) * page_size
    with db() as conn:
        rows = conn.execute("SELECT * FROM users WHERE ?='' OR username LIKE ? OR COALESCE(email,'') LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?", (q_clean, like, like, page_size, offset_value)).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM users WHERE ?='' OR username LIKE ? OR COALESCE(email,'') LIKE ?", (q_clean, like, like)).fetchone()[0]
    return {"items": [public_user(u) for u in rows], "total": total, "page": page, "page_size": page_size, "limit": page_size, "offset": offset_value, "has_more": offset_value + len(rows) < total}


@app.get("/api/users/{user_id}")
def user_detail(user_id: int, posts_page: int = 1, comments_page: int = 1, sent_comments_page: int = 1, orders_page: int = 1, page_size: int = 10, authorization: str | None = Header(default=None)):
    page_size = max(1, min(int(page_size or 10), 30))
    posts_page = max(1, int(posts_page or 1))
    comments_page = max(1, int(comments_page or 1))
    sent_comments_page = max(1, int(sent_comments_page or 1))
    orders_page = max(1, int(orders_page or 1))
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=? AND COALESCE(deleted_at,'')=''", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id WHERE p.user_id=? ORDER BY p.created_at DESC LIMIT ? OFFSET ?
            """,
            (user_id, page_size, (posts_page-1)*page_size),
        ).fetchall()
        post_total = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id=?", (user_id,)).fetchone()[0]
        sent_comment_total_all = conn.execute("SELECT COUNT(*) FROM comments WHERE user_id=?", (user_id,)).fetchone()[0]
        views_total = conn.execute("SELECT COALESCE(SUM(views),0) FROM posts WHERE user_id=?", (user_id,)).fetchone()[0]
        max_comments = conn.execute("SELECT COALESCE(MAX(comment_count),0) FROM (SELECT COUNT(c.id) AS comment_count FROM posts p LEFT JOIN comments c ON c.post_id=p.id WHERE p.user_id=? GROUP BY p.id)", (user_id,)).fetchone()[0]
        last_active_row = conn.execute("SELECT MAX(ts) AS last_active FROM (SELECT created_at AS ts FROM posts WHERE user_id=? UNION ALL SELECT created_at AS ts FROM comments WHERE user_id=?)", (user_id, user_id)).fetchone()
        community_age_days = days_between(user["created_at"] if "created_at" in user.keys() else "")
        profile_stats = {
            "joined_at": user["created_at"] if "created_at" in user.keys() else "",
            "community_age_days": community_age_days,
            "posts_count": int(post_total or 0),
            "comments_count": int(sent_comment_total_all or 0),
            "views_count": int(views_total or 0),
            "max_post_comments": int(max_comments or 0),
            "last_active_at": (last_active_row["last_active"] if last_active_row else "") or "",
        }
        point_balance = conn.execute("SELECT COALESCE(SUM(delta),0) FROM point_ledger WHERE user_id=?", (user_id,)).fetchone()[0]
        order_count = conn.execute("SELECT COUNT(*) FROM market_orders WHERE user_id=?", (user_id,)).fetchone()[0]
        profile_stats["hongcoin_balance"] = int(point_balance or 0)
        profile_stats["market_orders_count"] = int(order_count or 0)
        viewer = current_user(authorization)
        is_owner = bool(viewer and viewer["id"] == user_id)
        if is_owner:
            comment_rows = conn.execute(
                """
                SELECT c.*, a.username AS actor_name, a.avatar AS actor_avatar, p.id AS post_id, p.title AS post_title,
                       n.id AS notification_id, n.read_at AS notification_read_at
                FROM comments c
                JOIN posts p ON p.id=c.post_id
                JOIN users a ON a.id=c.user_id
                LEFT JOIN comment_notifications n ON n.comment_id=c.id AND n.user_id=?
                WHERE p.user_id=? AND c.user_id<>p.user_id
                ORDER BY c.created_at DESC, c.id DESC LIMIT ? OFFSET ?
                """,
                (user_id, user_id, page_size, (comments_page-1)*page_size),
            ).fetchall()
            comment_total = conn.execute("SELECT COUNT(*) FROM comments c JOIN posts p ON p.id=c.post_id WHERE p.user_id=? AND c.user_id<>p.user_id", (user_id,)).fetchone()[0]
            sent_comment_rows = conn.execute(
                """
                SELECT c.*, p.id AS post_id, p.title AS post_title, u.username AS owner_name, u.avatar AS owner_avatar
                FROM comments c
                JOIN posts p ON p.id=c.post_id
                JOIN users u ON u.id=p.user_id
                WHERE c.user_id=?
                ORDER BY c.created_at DESC, c.id DESC LIMIT ? OFFSET ?
                """,
                (user_id, page_size, (sent_comments_page-1)*page_size),
            ).fetchall()
            sent_comment_total = sent_comment_total_all
            unread_notifications = conn.execute("SELECT COUNT(*) FROM comment_notifications WHERE user_id=? AND COALESCE(read_at,'')=''", (user_id,)).fetchone()[0]
            order_rows = conn.execute(
                """
                SELECT o.*, mi.title, mi.cover_icon FROM market_orders o
                LEFT JOIN market_items mi ON mi.id=o.item_id
                WHERE o.user_id=? ORDER BY o.id DESC LIMIT ? OFFSET ?
                """,
                (user_id, 5, (orders_page-1)*5),
            ).fetchall()
            order_total = conn.execute("SELECT COUNT(*) FROM market_orders WHERE user_id=?", (user_id,)).fetchone()[0]
        else:
            comment_rows = []
            sent_comment_rows = []
            comment_total = 0
            sent_comment_total = 0
            unread_notifications = 0
            order_rows = []
            order_total = 0
    return {
        "user": public_user(user),
        "profile_stats": profile_stats,
        "posts": [post_row_to_dict(r) for r in rows],
        "posts_total": post_total,
        "posts_has_more": posts_page * page_size < post_total,
        "received_comments": [{"id": c["id"], "notification_id": c["notification_id"], "read": bool(c["notification_read_at"]) if c["notification_id"] else True, "post_id": c["post_id"], "post_title": c["post_title"], "user_id": c["user_id"], "author": c["actor_name"], "avatar": c["actor_avatar"] or DEFAULT_AVATAR, "content": c["content"], "time": c["created_at"]} for c in comment_rows],
        "sent_comments": [{"id": c["id"], "post_id": c["post_id"], "post_title": c["post_title"], "owner_name": c["owner_name"], "owner_avatar": c["owner_avatar"] or DEFAULT_AVATAR, "content": c["content"], "time": c["created_at"]} for c in sent_comment_rows],
        "market_orders": [market_order_to_dict(o) for o in order_rows],
        "market_orders_total": order_total,
        "market_orders_has_more": orders_page * 5 < order_total,
        "unread_notifications": unread_notifications,
        "received_comments_total": comment_total,
        "received_comments_has_more": comments_page * page_size < comment_total,
        "sent_comments_total": sent_comment_total,
        "sent_comments_has_more": sent_comments_page * page_size < sent_comment_total,
    }


def refresh_user_points(conn: sqlite3.Connection, user_id: int) -> int:
    conn.execute("INSERT OR IGNORE INTO user_points(user_id, available_points, total_earned, current_streak, last_checkin_date, updated_at) VALUES(?,?,?,?,?,?)", (user_id, 0, 0, 0, '', now()))
    balance = conn.execute("SELECT COALESCE(SUM(delta),0) FROM point_ledger WHERE user_id=?", (user_id,)).fetchone()[0]
    earned = conn.execute("SELECT COALESCE(SUM(delta),0) FROM point_ledger WHERE user_id=? AND delta>0", (user_id,)).fetchone()[0]
    conn.execute("UPDATE user_points SET available_points=?, total_earned=?, updated_at=? WHERE user_id=?", (int(balance or 0), int(earned or 0), now(), user_id))
    return int(balance or 0)


def award_points(conn: sqlite3.Connection, user_id: int, delta: int, reason: str, ref_type: str, ref_id: int, daily_cap: int = 80) -> int:
    """Idempotently award positive points and keep user_points snapshot in sync."""
    if delta <= 0:
        raise ValueError("award_points delta must be positive")
    refresh_user_points(conn, user_id)
    existing = conn.execute("SELECT id FROM point_ledger WHERE user_id=? AND ref_type=? AND ref_id=?", (user_id, ref_type, ref_id)).fetchone()
    if existing:
        return refresh_user_points(conn, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if daily_cap > 0:
        earned_today = conn.execute("SELECT COALESCE(SUM(delta),0) FROM point_ledger WHERE user_id=? AND delta>0 AND ref_type IN ('post','comment') AND substr(created_at,1,10)=?", (user_id, today)).fetchone()[0]
        delta = max(0, min(delta, daily_cap - int(earned_today or 0)))
    if delta <= 0:
        return refresh_user_points(conn, user_id)
    conn.execute("INSERT OR IGNORE INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (user_id, delta, reason, ref_type, ref_id, now()))
    return refresh_user_points(conn, user_id)


def checkin_points(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    refresh_user_points(conn, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    row = conn.execute("SELECT * FROM user_points WHERE user_id=?", (user_id,)).fetchone()
    if row and row["last_checkin_date"] == today:
        return {"ok": True, "already": True, "earned": 0, "streak": int(row["current_streak"] or 0), "balance": int(row["available_points"] or 0)}
    streak = (int(row["current_streak"] or 0) + 1) if row and row["last_checkin_date"] == yesterday else 1
    earned = min(20, 5 + streak)
    conn.execute("INSERT INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (user_id, earned, "每日签到", "checkin", int(datetime.now().strftime("%Y%m%d")), now()))
    balance = refresh_user_points(conn, user_id)
    conn.execute("UPDATE user_points SET current_streak=?, last_checkin_date=?, updated_at=? WHERE user_id=?", (streak, today, now(), user_id))
    return {"ok": True, "already": False, "earned": earned, "streak": streak, "balance": balance}


def apply_direct_market_effect(conn: sqlite3.Connection, user_id: int, category: str, item: sqlite3.Row) -> str:
    payload_raw = item["payload_json"] if "payload_json" in item.keys() else "{}"
    try:
        payload = json.loads(payload_raw or "{}")
    except Exception:
        payload = {}
    if category == ProductCategory.MEMBER_BENEFIT.value:
        days = int(payload.get("vip_days") or 30)
        current = conn.execute("SELECT vip_until FROM users WHERE id=?", (user_id,)).fetchone()
        base = datetime.now()
        if current and (current["vip_until"] or "") > now():
            try:
                base = datetime.strptime(current["vip_until"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                base = datetime.now()
        until = (base + timedelta(days=max(1, days))).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET vip_until=?, role_label=CASE WHEN COALESCE(role_label,'')='' THEN 'VIP会员' ELSE role_label END WHERE id=?", (until, user_id))
        return f"VIP 已开通至 {until}"
    if category == ProductCategory.THEME_DRESSUP.value:
        if payload.get("effect") == "avatar_border_style":
            style = str(payload.get("style") or "").strip()
            if not (style.startswith("#") or style.startswith("conic-gradient(")):
                raise HTTPException(status_code=400, detail="头像边框样式配置异常")
            conn.execute("UPDATE users SET avatar_border_style=? WHERE id=?", (style[:240], user_id))
            return f"头像边框已生效：{payload.get('tier') or item['title']}"
        theme_id = str(payload.get("theme_id") or item["title"]).strip()[:80]
        row = conn.execute("SELECT unlocked_themes FROM users WHERE id=?", (user_id,)).fetchone()
        themes = []
        try:
            themes = json.loads((row["unlocked_themes"] if row else "[]") or "[]")
        except Exception:
            themes = []
        if theme_id not in themes:
            themes.append(theme_id)
        conn.execute("UPDATE users SET unlocked_themes=? WHERE id=?", (json.dumps(themes, ensure_ascii=False), user_id))
        return f"已解锁主题：{theme_id}"
    if category == ProductCategory.RARE_PERK.value:
        perk = str(payload.get("perk") or item["title"]).strip()[:120]
        perk_key = "red_username" if perk in ("red_username", "红色用户名") or item["title"] == "红色用户名" else perk
        row = conn.execute("SELECT rare_perks FROM users WHERE id=?", (user_id,)).fetchone()
        perks = []
        try:
            perks = json.loads((row["rare_perks"] if row else "[]") or "[]")
        except Exception:
            perks = []
        if perk_key not in perks:
            perks.append(perk_key)
        conn.execute("UPDATE users SET rare_perks=? WHERE id=?", (json.dumps(perks, ensure_ascii=False), user_id))
        if perk_key == "red_username":
            return "已解锁权益：红色用户名"
        return f"已解锁权益：{perk_key}"
    raise HTTPException(status_code=400, detail="不支持的即时生效商品")


def virtual_audit_type(item: sqlite3.Row | dict[str, Any]) -> str | None:
    title = (item.get("title") if isinstance(item, dict) else item["title"] if "title" in item.keys() else "") or ""
    payload_raw = (item.get("payload_json") if isinstance(item, dict) else item["payload_json"] if "payload_json" in item.keys() else "") or "{}"
    try:
        payload = json.loads(payload_raw)
        if payload.get("request_type") == "rename":
            return "rename"
        if payload.get("request_type") in {"custom_title", "title"}:
            return "title"
    except Exception:
        pass
    return AUDIT_MARKET_TITLES.get(title)


def validate_virtual_exchange(conn: sqlite3.Connection, user_id: int, item: sqlite3.Row, value: str) -> tuple[str, str]:
    exchange_type = virtual_audit_type(item)
    if exchange_type not in {"rename", "title"}:
        raise HTTPException(status_code=400, detail="该商品不是虚拟权益审核商品")
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="请填写申请内容")
    if len(cleaned) > 32:
        raise HTTPException(status_code=400, detail="申请内容不能超过 32 个字符")
    if exchange_type == "rename":
        if not USERNAME_RE.match(cleaned):
            raise HTTPException(status_code=400, detail="用户名必须以字母开头，且只能包含字母、数字和下划线！")
        exists = conn.execute("SELECT 1 FROM users WHERE username=? AND id<>? AND COALESCE(deleted_at,'')=''", (cleaned, user_id)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="该用户名已被占用")
    return exchange_type, cleaned


def shipping_text(payload: MarketBuyIn) -> str:
    name = (payload.shipping_name or "").strip()
    phone = (payload.shipping_phone or "").strip()
    address = (payload.shipping_address or "").strip()
    if not (name and phone and address):
        raise HTTPException(status_code=400, detail="实物商品需要填写收货人、电话和地址")
    return json.dumps({"name": name, "phone": phone, "address": address}, ensure_ascii=False)


@app.post("/api/points/checkin")
def points_checkin(authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        return checkin_points(conn, user["id"])


@app.get("/api/market")
def market_home(authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        balance = refresh_user_points(conn, user["id"])
        items = conn.execute("SELECT * FROM market_items WHERE enabled=1 ORDER BY price ASC, id ASC").fetchall()
        orders = conn.execute(
            """
            SELECT o.*, mi.title, mi.cover_icon FROM market_orders o
            JOIN market_items mi ON mi.id=o.item_id
            WHERE o.user_id=? ORDER BY o.id DESC LIMIT 8
            """,
            (user["id"],),
        ).fetchall()
    return {
        "balance": int(balance or 0),
        "items": [{**dict(i), "fulfillment_method": market_item_fulfillment_method(i)} for i in items],
        "orders": [market_order_to_dict(o) for o in orders],
        "rules": ["发布帖子 +12 泓币", "发表评论 +3 泓币", "卡密自动发放，实物/赞助进入待处理"],
    }


@app.get("/api/market/orders")
def market_orders(page: int = 1, page_size: int = 5, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 5), 30))
    offset_value = (page - 1) * page_size
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM market_orders WHERE user_id=?", (user["id"],)).fetchone()[0]
        rows = conn.execute(
            """
            SELECT o.*, mi.title, mi.cover_icon FROM market_orders o
            LEFT JOIN market_items mi ON mi.id=o.item_id
            WHERE o.user_id=? ORDER BY o.id DESC LIMIT ? OFFSET ?
            """,
            (user["id"], page_size, offset_value),
        ).fetchall()
    return {"items": [market_order_to_dict(o) for o in rows], "total": total, "page": page, "page_size": page_size, "has_more": offset_value + len(rows) < total}


@app.post("/api/market/exchange")
def market_exchange(payload: MarketExchangeIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    order_id = None
    new_balance = 0
    exchange_payload = {}
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                item = conn.execute("SELECT * FROM market_items WHERE id=? AND enabled=1", (payload.item_id,)).fetchone()
                if not item:
                    raise HTTPException(status_code=404, detail="商品不存在或已下架")
                category = normalize_market_category(item["category"])
                exchange_type, cleaned = validate_virtual_exchange(conn, user["id"], item, payload.value)
                price = int(item["price"] or 0)
                if price < 0:
                    raise HTTPException(status_code=400, detail="商品价格异常")
                balance = refresh_user_points(conn, user["id"])
                if balance < price:
                    raise HTTPException(status_code=400, detail="泓币不足")
                if int(item["stock"] or 0) == 0:
                    raise HTTPException(status_code=400, detail="商品已售罄")
                stock_cur = conn.execute("UPDATE market_items SET stock=CASE WHEN stock>0 THEN stock-1 ELSE stock END, updated_at=? WHERE id=? AND enabled=1 AND stock<>0", (now(), item["id"]))
                if stock_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="商品库存不足")
                exchange_payload = {"type": exchange_type, "value": cleaned, "item_title": item["title"]}
                payload_text = json.dumps(exchange_payload, ensure_ascii=False)
                cur = conn.execute(
                    "INSERT INTO market_orders(user_id,item_id,price,category,cost_points,status,shipping_info,payload,delivered_content,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (user["id"], item["id"], price, category, price, OrderStatus.PENDING_AUDIT.value, payload_text, payload_text, "", now()),
                )
                order_id = cur.lastrowid
                points_cur = conn.execute("UPDATE user_points SET available_points=available_points-?, updated_at=? WHERE user_id=? AND available_points>=?", (price, now(), user["id"], price))
                if points_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="泓币不足")
                conn.execute("INSERT INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (user["id"], -price, "purchase_item", "market_order", order_id, now()))
                new_balance = refresh_user_points(conn, user["id"])
                if new_balance < 0:
                    raise HTTPException(status_code=500, detail="积分账目异常，已回滚")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            raise HTTPException(status_code=409, detail="系统繁忙，请稍后重试")
        raise
    with db() as conn:
        order = fetch_market_order_dict(conn, order_id) if order_id else None
        refreshed = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"ok": True, "order_id": order_id, "order": order, "status": OrderStatus.PENDING_AUDIT.value, "balance": int(new_balance or 0), "current_points": int(new_balance or 0), "payload": exchange_payload, "user": public_user(refreshed)}


@app.post("/api/market/exchange/border")
def market_exchange_border(payload: MarketBorderExchangeIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    order_id = None
    delivered_content = ""
    payload_data = {}
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                item = conn.execute("SELECT * FROM market_items WHERE id=? AND enabled=1", (payload.item_id,)).fetchone()
                if not item:
                    raise HTTPException(status_code=404, detail="商品不存在或已下架")
                category = normalize_market_category(item["category"])
                if category != ProductCategory.THEME_DRESSUP.value:
                    raise HTTPException(status_code=400, detail="请选择头像颜色卡商品")
                try:
                    payload_data = json.loads((item["payload_json"] if "payload_json" in item.keys() else "{}") or "{}")
                except Exception:
                    payload_data = {}
                if payload_data.get("effect") != "avatar_border_style":
                    raise HTTPException(status_code=400, detail="请选择头像颜色卡商品")
                style = str(payload_data.get("style") or "").strip()
                if not (style.startswith("#") or style.startswith("conic-gradient(")):
                    raise HTTPException(status_code=400, detail="头像边框样式配置异常")
                price = int(item["price"] or 0)
                if price < 0:
                    raise HTTPException(status_code=400, detail="商品价格异常")
                balance = refresh_user_points(conn, user["id"])
                if balance < price:
                    raise HTTPException(status_code=400, detail="泓币不足")
                if int(item["stock"] or 0) == 0:
                    raise HTTPException(status_code=400, detail="商品已售罄")
                stock_cur = conn.execute("UPDATE market_items SET stock=CASE WHEN stock>0 THEN stock-1 ELSE stock END, updated_at=? WHERE id=? AND enabled=1 AND stock<>0", (now(), item["id"]))
                if stock_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="商品库存不足")
                order_payload = json.dumps({"type":"avatar_border", "value":style, "tier":payload_data.get("tier") or "", "item_title":item["title"]}, ensure_ascii=False)
                cur = conn.execute(
                    "INSERT INTO market_orders(user_id,item_id,price,category,cost_points,status,shipping_info,payload,delivered_content,created_at,fulfilled_at,fulfilled_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (user["id"], item["id"], price, category, price, OrderStatus.SUCCESS.value, order_payload, order_payload, "", now(), now(), user["id"]),
                )
                order_id = cur.lastrowid
                points_cur = conn.execute("UPDATE user_points SET available_points=available_points-?, updated_at=? WHERE user_id=? AND available_points>=?", (price, now(), user["id"], price))
                if points_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="泓币不足")
                conn.execute("INSERT INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (user["id"], -price, "purchase_item", "market_order", order_id, now()))
                delivered_content = apply_direct_market_effect(conn, user["id"], category, item)
                conn.execute("UPDATE market_orders SET delivered_content=? WHERE id=?", (delivered_content, order_id))
                new_balance = refresh_user_points(conn, user["id"])
                refreshed = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
                if new_balance < 0:
                    raise HTTPException(status_code=500, detail="积分账目异常，已回滚")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            raise HTTPException(status_code=409, detail="系统繁忙，请稍后重试")
        raise
    with db() as conn:
        order = fetch_market_order_dict(conn, order_id) if order_id else None
        refreshed = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"ok": True, "order_id": order_id, "order": order, "status": OrderStatus.SUCCESS.value, "balance": int(new_balance or 0), "current_points": int(new_balance or 0), "avatar_border_style": payload_data.get("style"), "delivered_content": delivered_content, "user": public_user(refreshed)}


@app.post("/api/market/buy")
@app.post("/api/market/orders")
def market_buy(payload: MarketBuyIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    order_id = None
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                item = conn.execute("SELECT * FROM market_items WHERE id=? AND enabled=1", (payload.item_id,)).fetchone()
                if not item:
                    raise HTTPException(status_code=404, detail="商品不存在或已下架")
                category = normalize_market_category(item["category"])
                method = market_item_fulfillment_method(item)
                price = int(item["price"] or 0)
                if price < 0:
                    raise HTTPException(status_code=400, detail="商品价格异常")
                balance = refresh_user_points(conn, user["id"])
                if balance < price:
                    raise HTTPException(status_code=400, detail="泓币不足")
                if int(item["stock"] or 0) == 0:
                    raise HTTPException(status_code=400, detail="商品已售罄")
                shipping_info = ""
                delivered_content = ""
                status = OrderStatus.SUCCESS.value
                if method == FulfillmentMethod.MANUAL_PROCESS.value:
                    status = OrderStatus.PENDING.value
                    note = (payload.request_note or "").strip()
                    if category == ProductCategory.PERIPHERAL_PHYSICAL.value:
                        shipping_info = shipping_text(payload)
                    elif note:
                        shipping_info = json.dumps({"note": note}, ensure_ascii=False)
                    elif item["title"] == "改名卡":
                        shipping_info = json.dumps({"note": "待提交新昵称"}, ensure_ascii=False)
                    elif item["title"] == "头衔申请券":
                        shipping_info = json.dumps({"note": "待提交申请头衔"}, ensure_ascii=False)
                    else:
                        shipping_info = json.dumps({"note": "赞助/人工履约，等待管理员处理"}, ensure_ascii=False)
                stock_cur = conn.execute("UPDATE market_items SET stock=CASE WHEN stock>0 THEN stock-1 ELSE stock END, updated_at=? WHERE id=? AND enabled=1 AND stock<>0", (now(), item["id"]))
                if stock_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="商品库存不足")
                cur = conn.execute(
                    "INSERT INTO market_orders(user_id,item_id,price,category,cost_points,status,shipping_info,delivered_content,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (user["id"], item["id"], price, category, price, status, shipping_info, delivered_content, now()),
                )
                order_id = cur.lastrowid
                if method == FulfillmentMethod.CARD_KEY.value:
                    key = conn.execute("SELECT * FROM product_card_keys WHERE product_id=? AND is_used=0 ORDER BY id ASC LIMIT 1", (item["id"],)).fetchone()
                    if not key:
                        raise HTTPException(status_code=400, detail="卡密库存不足，请联系管理员补货")
                    used = conn.execute("UPDATE product_card_keys SET is_used=1, order_id=?, used_at=? WHERE id=? AND is_used=0", (order_id, now(), key["id"]))
                    if used.rowcount == 0:
                        raise HTTPException(status_code=409, detail="卡密被其他订单占用，请重试")
                    delivered_content = key["key_content"]
                    conn.execute("UPDATE market_orders SET delivered_content=? WHERE id=?", (delivered_content, order_id))
                elif method == FulfillmentMethod.DIRECT_EFFECT.value:
                    delivered_content = apply_direct_market_effect(conn, user["id"], category, item)
                    conn.execute("UPDATE market_orders SET delivered_content=? WHERE id=?", (delivered_content, order_id))
                points_cur = conn.execute("UPDATE user_points SET available_points=available_points-?, updated_at=? WHERE user_id=? AND available_points>=?", (price, now(), user["id"], price))
                if points_cur.rowcount == 0:
                    raise HTTPException(status_code=400, detail="泓币不足")
                conn.execute("INSERT INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (user["id"], -price, "purchase_item", "market_order", order_id, now()))
                new_balance = refresh_user_points(conn, user["id"])
                if new_balance < 0:
                    raise HTTPException(status_code=500, detail="积分账目异常，已回滚")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            raise HTTPException(status_code=409, detail="系统繁忙，请稍后重试")
        raise
    with db() as conn:
        order = fetch_market_order_dict(conn, order_id) if order_id else None
        refreshed = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"ok": True, "order_id": order_id, "order": order, "balance": int(new_balance or 0), "current_points": int(new_balance or 0), "status": status, "delivered_content": delivered_content, "user": public_user(refreshed)}


@app.get("/api/admin/market")
def admin_market(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        items = conn.execute("SELECT * FROM market_items ORDER BY enabled DESC, id DESC").fetchall()
        orders = conn.execute(
            """
            SELECT o.*, u.username, mi.title AS item_title
            FROM market_orders o
            JOIN users u ON u.id=o.user_id
            JOIN market_items mi ON mi.id=o.item_id
            ORDER BY o.id DESC LIMIT 80
            """
        ).fetchall()
        ledgers = conn.execute(
            """
            SELECT l.*, u.username
            FROM point_ledger l JOIN users u ON u.id=l.user_id
            ORDER BY l.id DESC LIMIT 80
            """
        ).fetchall()
    return {
        "items": [{**dict(i), "fulfillment_method": market_item_fulfillment_method(i), "card_key_available": conn.execute("SELECT COUNT(*) FROM product_card_keys WHERE product_id=? AND is_used=0", (i["id"],)).fetchone()[0], "orders_count": conn.execute("SELECT COUNT(*) FROM market_orders WHERE item_id=?", (i["id"],)).fetchone()[0]} for i in items],
        "orders": [{"id": o["id"], "username": o["username"], "item_title": o["item_title"], "price": o["price"], "cost_points": o["cost_points"], "category": o["category"], "status": o["status"], "shipping_info": o["shipping_info"], "payload": o["payload"] if "payload" in o.keys() else "", "delivered_content": o["delivered_content"], "created_at": o["created_at"], "fulfilled_at": o["fulfilled_at"]} for o in orders],
        "ledgers": [{"id": l["id"], "username": l["username"], "delta": l["delta"], "reason": l["reason"], "ref_type": l["ref_type"], "ref_id": l["ref_id"], "created_at": l["created_at"]} for l in ledgers],
        "categories": [{"value": c, "method": CATEGORY_METHOD[c]} for c in sorted(ALL_PRODUCT_CATEGORIES)],
    }


@app.post("/api/admin/market/products")
@app.post("/api/admin/market/items")
def admin_create_market_item(payload: MarketItemIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    category = normalize_market_category(payload.category.value if isinstance(payload.category, ProductCategory) else str(payload.category))
    try:
        json.loads(payload.payload_json or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="商品参数 JSON 格式不正确")
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM market_items WHERE title=? AND category=? ORDER BY enabled DESC, id ASC LIMIT 1",
            (payload.title.strip(), category),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE market_items SET description=?, price=?, stock=?, cover_icon=?, enabled=?, payload_json=?, updated_at=? WHERE id=?",
                (payload.description.strip(), payload.price, payload.stock, payload.cover_icon.strip() or 'fa-gift', 1 if payload.enabled else 0, payload.payload_json or '{}', now(), existing["id"]),
            )
            return {"ok": True, "id": existing["id"], "updated": True}
        cur = conn.execute(
            "INSERT INTO market_items(title,description,price,stock,category,cover_icon,enabled,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (payload.title.strip(), payload.description.strip(), payload.price, payload.stock, category, payload.cover_icon.strip() or 'fa-gift', 1 if payload.enabled else 0, payload.payload_json or '{}', now(), now()),
        )
    return {"ok": True, "id": cur.lastrowid}


@app.put("/api/admin/market/items/{item_id}")
def admin_update_market_item(item_id: int, payload: MarketItemIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    category = normalize_market_category(payload.category.value if isinstance(payload.category, ProductCategory) else str(payload.category))
    try:
        json.loads(payload.payload_json or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="商品参数 JSON 格式不正确")
    with db() as conn:
        cur = conn.execute(
            "UPDATE market_items SET title=?, description=?, price=?, stock=?, category=?, cover_icon=?, enabled=?, payload_json=?, updated_at=? WHERE id=?",
            (payload.title.strip(), payload.description.strip(), payload.price, payload.stock, category, payload.cover_icon.strip() or 'fa-gift', 1 if payload.enabled else 0, payload.payload_json or '{}', now(), item_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="商品不存在")
    return {"ok": True}


@app.patch("/api/admin/market/items/{item_id}/enabled")
def admin_set_market_item_enabled(item_id: int, payload: dict[str, Any], authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    enabled = 1 if bool(payload.get("enabled")) else 0
    with db() as conn:
        cur = conn.execute("UPDATE market_items SET enabled=?, updated_at=? WHERE id=?", (enabled, now(), item_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="商品不存在")
    return {"ok": True, "enabled": bool(enabled)}


@app.delete("/api/admin/market/items/{item_id}")
def admin_delete_market_item(item_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        used = conn.execute("SELECT COUNT(*) FROM market_orders WHERE item_id=?", (item_id,)).fetchone()[0]
        if used:
            conn.execute("UPDATE market_items SET enabled=0, updated_at=? WHERE id=?", (now(), item_id))
            return {"ok": True, "archived": True, "message": "已有兑换记录，已下架保留历史记录"}
        cur = conn.execute("DELETE FROM market_items WHERE id=?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="商品不存在")
    return {"ok": True}


@app.post("/api/admin/market/add-keys")
def admin_add_market_keys(payload: MarketKeysIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    keys = []
    seen = set()
    for line in payload.keys_text.splitlines():
        key = line.strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)
    if not keys:
        raise HTTPException(status_code=400, detail="没有可导入的卡密")
    with db() as conn:
        product = conn.execute("SELECT * FROM market_items WHERE id=?", (payload.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        category = normalize_market_category(product["category"])
        if fulfillment_method(category) != FulfillmentMethod.CARD_KEY.value:
            raise HTTPException(status_code=400, detail="只有卡密类商品可以导入卡密")
        inserted = 0
        for key in keys:
            try:
                cur = conn.execute("INSERT OR IGNORE INTO product_card_keys(product_id,key_content,is_used,created_at) VALUES(?,?,0,?)", (payload.product_id, key, now()))
                inserted += cur.rowcount
            except sqlite3.IntegrityError:
                pass
    return {"ok": True, "inserted": inserted, "ignored": len(keys) - inserted}


@app.put("/api/admin/market/audit/{order_id}")
def admin_audit_market_order(order_id: int, payload: MarketAuditIn, authorization: str | None = Header(default=None)):
    admin = require_admin(current_user(authorization))
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                order = conn.execute(
                    """
                    SELECT o.*, mi.title AS item_title, u.username AS current_username
                    FROM market_orders o
                    JOIN market_items mi ON mi.id=o.item_id
                    JOIN users u ON u.id=o.user_id
                    WHERE o.id=?
                    """,
                    (order_id,),
                ).fetchone()
                if not order:
                    raise HTTPException(status_code=404, detail="订单不存在")
                if order["status"] != OrderStatus.PENDING_AUDIT.value:
                    raise HTTPException(status_code=400, detail="只有待审核订单可以审核")
                try:
                    data = json.loads(order["payload"] or order["shipping_info"] or "{}")
                except Exception:
                    raise HTTPException(status_code=400, detail="订单申请数据损坏，无法审核")
                req_type = data.get("type")
                value = str(data.get("value") or "").strip()
                if req_type not in {"rename", "title"} or not value:
                    raise HTTPException(status_code=400, detail="订单申请数据不完整")
                if payload.approved:
                    if req_type == "rename":
                        if not USERNAME_RE.match(value):
                            raise HTTPException(status_code=400, detail="用户名必须以字母开头，且只能包含字母、数字和下划线！")
                        exists = conn.execute("SELECT 1 FROM users WHERE username=? AND id<>? AND COALESCE(deleted_at,'')=''", (value, order["user_id"])).fetchone()
                        if exists:
                            raise HTTPException(status_code=400, detail="该用户名已被占用，无法通过")
                        conn.execute("UPDATE users SET username=? WHERE id=?", (value, order["user_id"]))
                        result = f"已通过改名申请：{order['current_username']} → {value}"
                    else:
                        conn.execute("UPDATE users SET custom_title=? WHERE id=?", (value[:32], order["user_id"]))
                        result = f"已通过头衔申请：{value[:32]}"
                    conn.execute("UPDATE market_orders SET status=?, delivered_content=?, fulfilled_at=?, fulfilled_by=? WHERE id=?", (OrderStatus.SUCCESS.value, result, now(), admin["id"], order_id))
                    conn.commit()
                    order_state = fetch_admin_market_order_dict(conn, order_id)
                    return {"ok": True, "status": OrderStatus.SUCCESS.value, "message": result, "order": order_state}
                reason = (payload.reject_reason or "管理员拒绝该申请").strip()[:500]
                refund = int(order["cost_points"] or order["price"] or 0)
                if refund > 0:
                    try:
                        conn.execute("INSERT INTO point_ledger(user_id,delta,reason,ref_type,ref_id,created_at) VALUES(?,?,?,?,?,?)", (order["user_id"], refund, "refund_market_order", "market_order", order_id, now()))
                    except sqlite3.IntegrityError:
                        raise HTTPException(status_code=409, detail="该订单已退款，请勿重复操作")
                    conn.execute("UPDATE user_points SET available_points=available_points+?, total_earned=total_earned+?, updated_at=? WHERE user_id=?", (refund, refund, now(), order["user_id"]))
                conn.execute("UPDATE market_items SET stock=CASE WHEN stock>=0 THEN stock+1 ELSE stock END, updated_at=? WHERE id=?", (now(), order["item_id"]))
                result = f"审核拒绝：{reason}；已退回 {refund} 泓币"
                conn.execute("UPDATE market_orders SET status=?, delivered_content=?, fulfilled_at=?, fulfilled_by=? WHERE id=?", (OrderStatus.REJECTED.value, result, now(), admin["id"], order_id))
                refresh_user_points(conn, order["user_id"])
                conn.commit()
                order_state = fetch_admin_market_order_dict(conn, order_id)
                balance = refresh_user_points(conn, order["user_id"])
                return {"ok": True, "status": OrderStatus.REJECTED.value, "message": result, "refund": refund, "balance": int(balance or 0), "order": order_state}
            except Exception:
                conn.rollback()
                raise
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            raise HTTPException(status_code=409, detail="系统繁忙，请稍后重试")
        raise


@app.put("/api/admin/market/orders/{order_id}/fulfill")
def admin_fulfill_market_order(order_id: int, payload: MarketFulfillIn, authorization: str | None = Header(default=None)):
    admin = require_admin(current_user(authorization))
    with db() as conn:
        order = conn.execute("SELECT * FROM market_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order["status"] != OrderStatus.PENDING.value:
            raise HTTPException(status_code=400, detail="只有待处理订单可以手动发货")
        category = normalize_market_category(order["category"])
        if fulfillment_method(category) != FulfillmentMethod.MANUAL_PROCESS.value:
            raise HTTPException(status_code=400, detail="该订单不是人工履约类型")
        conn.execute("UPDATE market_orders SET status=?, delivered_content=?, fulfilled_at=?, fulfilled_by=? WHERE id=?", (OrderStatus.SUCCESS.value, payload.delivered_content.strip(), now(), admin["id"], order_id))
        order_state = fetch_admin_market_order_dict(conn, order_id)
    return {"ok": True, "status": OrderStatus.SUCCESS.value, "order": order_state}


@app.get("/api/search")
def search(q: str = "", type: str = "posts", page: int = 1, page_size: int = 30, limit: int | None = None, offset: int | None = None, authorization: str | None = Header(default=None)):
    require_user(current_user(authorization))
    if type == "users":
        return users(q=q, page=page, page_size=page_size, limit=limit, offset=offset, authorization=authorization)
    return list_posts(q=q, page=page, page_size=page_size, limit=limit, offset=offset, authorization=authorization)


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
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
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
            WHERE COALESCE(u.deleted_at,'')='' AND (?='' OR u.username LIKE ? OR COALESCE(u.email,'') LIKE ?)
            ORDER BY u.id ASC
            """,
            (q.strip(), like, like),
        ).fetchall()
    items = []
    for u in rows:
        d = public_user(u)
        d.update({"email": u["email"], "post_count": u["post_count"], "comment_count": u["comment_count"], "register_ip": u["register_ip"] if "register_ip" in u.keys() else "", "last_login_ip": u["last_login_ip"] if "last_login_ip" in u.keys() else "", "ban_reason": u["ban_reason"] if "ban_reason" in u.keys() else "", "banned_at": u["banned_at"] if "banned_at" in u.keys() else ""})
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


@app.get("/api/admin/users/{user_id}")
def admin_user_info(user_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        bans = conn.execute("SELECT * FROM banned_identities WHERE user_id=? OR email=? ORDER BY id DESC", (user_id, u["email"] or "")).fetchall()
    data = public_user(u) or {}
    data.update({"email": u["email"], "register_ip": u["register_ip"] if "register_ip" in u.keys() else "", "last_login_ip": u["last_login_ip"] if "last_login_ip" in u.keys() else "", "ban_reason": u["ban_reason"] if "ban_reason" in u.keys() else "", "banned_at": u["banned_at"] if "banned_at" in u.keys() else "", "deleted_at": u["deleted_at"] if "deleted_at" in u.keys() else ""})
    return {"user": data, "bans": [{"id": b["id"], "email": b["email"], "ip": b["ip"], "reason": b["reason"], "banned_at": b["banned_at"]} for b in bans]}


@app.post("/api/admin/users/{user_id}/freeze")
def admin_freeze_user(user_id: int, payload: AdminFreezeIn, authorization: str | None = Header(default=None)):
    admin = require_admin(current_user(authorization))
    until = (datetime.now() + timedelta(days=payload.days)).strftime("%Y-%m-%d %H:%M:%S")
    reason = (payload.reason or "").strip()
    with db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=? AND COALESCE(deleted_at,'')=''", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute("UPDATE users SET account_status='frozen', frozen_until=?, ban_reason=? WHERE id=?", (until, reason, user_id))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        send_account_notice(conn, u, "账号冻结通知", f"你的账号已被冻结 {payload.days} 天。原因：{reason or '管理员处理'}")
    return {"ok": True, "frozen_until": until}


@app.post("/api/admin/users/{user_id}/unfreeze")
def admin_unfreeze_user(user_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        cur = conn.execute("UPDATE users SET account_status='active', frozen_until='', ban_reason='' WHERE id=? AND account_status='frozen'", (user_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="冻结用户不存在")
    return {"ok": True}


@app.post("/api/admin/users/{user_id}/ban")
def admin_ban_user(user_id: int, payload: AdminBanIn, request: Request, authorization: str | None = Header(default=None)):
    admin = require_admin(current_user(authorization))
    reason = (payload.reason or "").strip()
    with db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=? AND COALESCE(deleted_at,'')=''", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        data = dict(u)
        ip = (u["last_login_ip"] or u["register_ip"] or "") if "last_login_ip" in u.keys() else ""
        conn.execute("""INSERT INTO banned_identities(user_id,username,email,ip,reason,banned_at,banned_by,data_json)
            VALUES(?,?,?,?,?,?,?,?)""", (user_id, u["username"], u["email"] or "", ip, reason, now(), admin["id"], json.dumps(data, ensure_ascii=False, default=str)))
        conn.execute("UPDATE users SET account_status='banned', banned_at=?, ban_reason=?, deleted_at=? WHERE id=?", (now(), reason, now(), user_id))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        send_account_notice(conn, u, "账号封禁通知", f"你的账号已被永久封禁。原因：{reason or '管理员处理'}")
    return {"ok": True}


@app.delete("/api/admin/users/{user_id}/hard-delete")
def admin_hard_delete_user(user_id: int, payload: AdminHardDeleteIn | None = None, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        if u["role"] == "admin":
            raise HTTPException(status_code=400, detail="不能硬删除管理员")
        conn.execute("DELETE FROM comment_notifications WHERE user_id=? OR actor_id=?", (user_id, user_id))
        conn.execute("DELETE FROM email_notification_log WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM channel_comments WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM comments WHERE user_id=? OR post_id IN (SELECT id FROM posts WHERE user_id=?)", (user_id, user_id))
        conn.execute("DELETE FROM posts WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM email_verification_codes WHERE email=?", (u["email"] or "",))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    return {"ok": True}


@app.get("/api/admin/bans")
def admin_bans(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        rows = conn.execute("SELECT * FROM banned_identities ORDER BY id DESC LIMIT 200").fetchall()
    return {"items": [{"id": r["id"], "user_id": r["user_id"], "username": r["username"], "email": r["email"], "ip": r["ip"], "reason": r["reason"], "banned_at": r["banned_at"]} for r in rows]}


@app.get("/api/admin/posts")
def admin_posts(q: str = "", authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    like = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.username, u.avatar, u.role, u.role_label, u.custom_title, u.rare_perks, u.avatar_border_style,
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



@app.get("/api/admin/settings")
def admin_get_settings(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        return {"settings": get_settings(conn)}


@app.put("/api/admin/settings")
def admin_update_settings(payload: SiteSettingsIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    data = payload.model_dump(exclude_unset=True)
    with db() as conn:
        existing = get_settings(conn, include_secret=True)
        for key, value in data.items():
            if key == "smtp_password" and (value is None or value == "***"):
                continue
            if key == "email_enabled":
                value = "1" if value else "0"
            set_setting(conn, key, value)
        updated = get_settings(conn)
    return {"ok": True, "settings": updated}


def channel_to_dict(c: sqlite3.Row, post_count: int | None = None) -> dict[str, Any]:
    return {
        "id": c["id"],
        "name": c["name"],
        "slug": c["slug"],
        "description": c["description"] or "",
        "mode": c["mode"],
        "enabled": bool(c["enabled"]),
        "source_type": c["source_type"] or "",
        "endpoint_url": c["endpoint_url"] or "",
        "auth_type": c["auth_type"] or "none",
        "auth_secret_ref": "***" if c["auth_secret_ref"] else "",
        "mapping_json": c["mapping_json"] or "{}",
        "last_sync_at": c["last_sync_at"] or "",
        "created_at": c["created_at"],
        "updated_at": c["updated_at"],
        "post_count": post_count if post_count is not None else 0,
    }


def channel_post_to_dict(p: sqlite3.Row) -> dict[str, Any]:
    raw_time = p["created_at"] or ""
    # Channel feed timestamps are stored in UTC. Expose an explicit UTC suffix so
    # browsers do not parse them as local time and show an 8-hour offset.
    display_time = raw_time
    if isinstance(display_time, str) and display_time and 'T' not in display_time:
        display_time = display_time.replace(' ', 'T') + 'Z'
    elif isinstance(display_time, str) and display_time and not display_time.endswith(('Z', '+00:00')):
        display_time = display_time + 'Z'
    return {
        "id": p["id"],
        "channel_id": p["channel_id"],
        "channel_name": p["channel_name"] if "channel_name" in p.keys() else "",
        "channel_slug": p["channel_slug"] if "channel_slug" in p.keys() else "",
        "title": p["title"],
        "content": p["content"],
        "preview": p["content"],
        "author_name": "管理员",
        "external_url": p["external_url"] or "",
        "views": p["views"],
        "comments": p["comment_count"] if "comment_count" in p.keys() else 0,
        "time": display_time,
    }


def get_channel(conn: sqlite3.Connection, id_or_slug: str) -> sqlite3.Row | None:
    if id_or_slug.isdigit():
        return conn.execute("SELECT * FROM channels WHERE id=?", (int(id_or_slug),)).fetchone()
    return conn.execute("SELECT * FROM channels WHERE slug=?", (id_or_slug,)).fetchone()


def clean_slug(slug: str) -> str:
    value = ''.join(ch.lower() if ch.isalnum() else '-' for ch in slug.strip())
    value = '-'.join(part for part in value.split('-') if part)
    if not value:
        raise HTTPException(status_code=400, detail="slug 无效")
    return value[:80]


@app.get("/api/channels")
def list_channels(authorization: str | None = Header(default=None)):
    require_user(current_user(authorization))
    init_db()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT ch.*, (SELECT COUNT(*) FROM channel_posts cp WHERE cp.channel_id=ch.id) AS post_count
            FROM channels ch WHERE ch.enabled=1 ORDER BY ch.id DESC
            """
        ).fetchall()
    return {"items": [channel_to_dict(r, r["post_count"]) for r in rows]}


@app.get("/api/channels/{id_or_slug}")
def channel_detail(id_or_slug: str, authorization: str | None = Header(default=None)):
    require_user(current_user(authorization))
    with db() as conn:
        ch = get_channel(conn, id_or_slug)
        if not ch or not ch["enabled"]:
            raise HTTPException(status_code=404, detail="频道不存在")
        count = conn.execute("SELECT COUNT(*) FROM channel_posts WHERE channel_id=?", (ch["id"],)).fetchone()[0]
    return {"channel": channel_to_dict(ch, count)}


@app.get("/api/channels/{id_or_slug}/posts")
def channel_posts(id_or_slug: str, authorization: str | None = Header(default=None)):
    require_user(current_user(authorization))
    with db() as conn:
        ch = get_channel(conn, id_or_slug)
        if not ch or not ch["enabled"]:
            raise HTTPException(status_code=404, detail="频道不存在")
        sync_result = _auto_sync_channel_if_stale(conn, ch)
        if sync_result:
            ch = get_channel(conn, id_or_slug)
        rows = conn.execute(
            """
            SELECT cp.*, ch.name AS channel_name, ch.slug AS channel_slug,
                   (SELECT COUNT(*) FROM channel_comments cc WHERE cc.channel_post_id=cp.id) AS comment_count
            FROM channel_posts cp JOIN channels ch ON ch.id=cp.channel_id
            WHERE cp.channel_id=? ORDER BY datetime(cp.created_at) DESC, cp.id DESC LIMIT 50
            """,
            (ch["id"],),
        ).fetchall()
    return {"channel": channel_to_dict(ch), "items": [channel_post_to_dict(r) for r in rows], "sync": sync_result}


@app.get("/api/channel_posts/{post_id}")
def channel_post_detail(post_id: int, authorization: str | None = Header(default=None)):
    require_user(current_user(authorization))
    with db() as conn:
        conn.execute("UPDATE channel_posts SET views=views+1 WHERE id=?", (post_id,))
        row = conn.execute(
            """
            SELECT cp.*, ch.name AS channel_name, ch.slug AS channel_slug,
                   (SELECT COUNT(*) FROM channel_comments cc WHERE cc.channel_post_id=cp.id) AS comment_count
            FROM channel_posts cp JOIN channels ch ON ch.id=cp.channel_id WHERE cp.id=? AND ch.enabled=1
            """,
            (post_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="频道内容不存在")
        comments = conn.execute(
            "SELECT cc.*, u.username, u.avatar, u.avatar_border_style, u.role, u.role_label FROM channel_comments cc JOIN users u ON u.id=cc.user_id WHERE cc.channel_post_id=? ORDER BY cc.id ASC",
            (post_id,),
        ).fetchall()
    return {"post": channel_post_to_dict(row), "comments": [{"id": c["id"], "user_id": c["user_id"], "content": c["content"], "time": c["created_at"], "author": c["username"], "avatar": c["avatar"] or DEFAULT_AVATAR, "avatar_border_style": (c["avatar_border_style"] if "avatar_border_style" in c.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE, "role": c["role_label"] or ("超管" if c["role"] == "admin" else "")} for c in comments]}


@app.post("/api/channel_posts/{post_id}/comments")
def add_channel_comment(post_id: int, payload: CommentIn, authorization: str | None = Header(default=None)):
    user = require_user(current_user(authorization))
    with db() as conn:
        exists = conn.execute("SELECT id FROM channel_posts WHERE id=?", (post_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="频道内容不存在")
        cur = conn.execute("INSERT INTO channel_comments(channel_post_id,user_id,content,created_at) VALUES(?,?,?,?)", (post_id, user["id"], payload.content.strip(), now()))
        comment_id = cur.lastrowid
        row = conn.execute(
            "SELECT cc.*, u.username, u.avatar, u.avatar_border_style, u.role, u.role_label FROM channel_comments cc JOIN users u ON u.id=cc.user_id WHERE cc.id=?",
            (comment_id,),
        ).fetchone()
        comment = {"id": row["id"], "user_id": row["user_id"], "content": row["content"], "time": row["created_at"], "author": row["username"], "avatar": row["avatar"] or DEFAULT_AVATAR, "avatar_border_style": (row["avatar_border_style"] if "avatar_border_style" in row.keys() else "") or DEFAULT_AVATAR_BORDER_STYLE, "role": row["role_label"] or ("超管" if row["role"] == "admin" else "")}
    return {"ok": True, "id": comment_id, "comment": comment}


@app.get("/api/admin/channels")
def admin_channels(authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        rows = conn.execute(
            """
            SELECT ch.*, (SELECT COUNT(*) FROM channel_posts cp WHERE cp.channel_id=ch.id) AS post_count
            FROM channels ch ORDER BY ch.id DESC
            """
        ).fetchall()
        posts = conn.execute(
            """
            SELECT cp.*, ch.name AS channel_name, ch.slug AS channel_slug,
                   (SELECT COUNT(*) FROM channel_comments cc WHERE cc.channel_post_id=cp.id) AS comment_count
            FROM channel_posts cp JOIN channels ch ON ch.id=cp.channel_id ORDER BY datetime(cp.created_at) DESC, cp.id DESC LIMIT 100
            """
        ).fetchall()
    return {"items": [channel_to_dict(r, r["post_count"]) for r in rows], "posts": [channel_post_to_dict(p) for p in posts]}


@app.post("/api/admin/channels")
def admin_create_channel(payload: ChannelIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    if payload.mode not in {"manual", "api"}:
        raise HTTPException(status_code=400, detail="频道模式只能是 manual 或 api")
    slug = clean_slug(payload.slug)
    with db() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO channels(name,slug,description,mode,enabled,source_type,endpoint_url,auth_type,auth_secret_ref,mapping_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (payload.name.strip(), slug, (payload.description or '').strip(), payload.mode, 1 if payload.enabled else 0, (payload.source_type or '').strip(), (payload.endpoint_url or '').strip(), (payload.auth_type or 'none').strip(), (payload.auth_secret_ref or '').strip(), payload.mapping_json or '{}', now(), now()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="频道 slug 已存在")
    return {"id": cur.lastrowid}


@app.put("/api/admin/channels/{channel_id}")
def admin_update_channel(channel_id: int, payload: ChannelIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    if payload.mode not in {"manual", "api"}:
        raise HTTPException(status_code=400, detail="频道模式只能是 manual 或 api")
    slug = clean_slug(payload.slug)
    with db() as conn:
        try:
            cur = conn.execute(
                """UPDATE channels SET name=?, slug=?, description=?, mode=?, enabled=?, source_type=?, endpoint_url=?, auth_type=?, auth_secret_ref=?, mapping_json=?, updated_at=? WHERE id=?""",
                (payload.name.strip(), slug, (payload.description or '').strip(), payload.mode, 1 if payload.enabled else 0, (payload.source_type or '').strip(), (payload.endpoint_url or '').strip(), (payload.auth_type or 'none').strip(), (payload.auth_secret_ref or '').strip(), payload.mapping_json or '{}', now(), channel_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="频道 slug 已存在")
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="频道不存在")
    return {"ok": True}


@app.delete("/api/admin/channels/{channel_id}")
def admin_delete_channel(channel_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        conn.execute("DELETE FROM channel_comments WHERE channel_post_id IN (SELECT id FROM channel_posts WHERE channel_id=?)", (channel_id,))
        conn.execute("DELETE FROM channel_posts WHERE channel_id=?", (channel_id,))
        cur = conn.execute("DELETE FROM channels WHERE id=?", (channel_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="频道不存在")
    return {"ok": True}


@app.post("/api/admin/channels/{channel_id}/posts")
def admin_create_channel_post(channel_id: int, payload: ChannelPostIn, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        ch = conn.execute("SELECT * FROM channels WHERE id=?", (channel_id,)).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="频道不存在")
        cur = conn.execute(
            "INSERT INTO channel_posts(channel_id,title,content,author_name,external_url,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (channel_id, payload.title.strip(), payload.content.strip(), (payload.author_name or '管理员').strip(), (payload.external_url or '').strip(), now(), now()),
        )
        pruned = prune_channel_posts(conn, channel_id, 50)
    return {"id": cur.lastrowid, "pruned": pruned}


@app.delete("/api/admin/channel_posts/{post_id}")
def admin_delete_channel_post(post_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        conn.execute("DELETE FROM channel_comments WHERE channel_post_id=?", (post_id,))
        cur = conn.execute("DELETE FROM channel_posts WHERE id=?", (post_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="频道内容不存在")
    return {"ok": True}



def prune_channel_posts(conn: sqlite3.Connection, channel_id: int, keep: int = 50) -> int:
    old = conn.execute(
        """SELECT id FROM channel_posts WHERE channel_id=? ORDER BY datetime(created_at) DESC, id DESC LIMIT -1 OFFSET ?""",
        (channel_id, keep),
    ).fetchall()
    ids = [r["id"] for r in old]
    if not ids:
        return 0
    placeholders = ','.join('?' for _ in ids)
    conn.execute(f"DELETE FROM channel_comments WHERE channel_post_id IN ({placeholders})", ids)
    conn.execute(f"DELETE FROM channel_posts WHERE id IN ({placeholders})", ids)
    return len(ids)

def _get_mapping_value(item: dict[str, Any], key: str, default: Any = '') -> Any:
    cur: Any = item
    for part in (key or '').split('.'):
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return default
    return default if cur is None else cur


def _load_channel_mapping(raw: str | None) -> dict[str, str]:
    defaults = {
        'items': 'items',
        'external_id': 'external_id',
        'title': 'title',
        'content': 'content',
        'author_name': 'author_name',
        'external_url': 'external_url',
        'created_at': 'created_at',
    }
    if not raw:
        return defaults
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            defaults.update({str(k): str(v) for k, v in parsed.items() if v is not None})
    except Exception:
        pass
    return defaults


def _resolve_channel_secret(secret_ref: str | None) -> str:
    ref = (secret_ref or '').strip()
    if not ref:
        return ''
    # 管理后台只保存引用名；真实密钥从环境变量读取，避免落库/前端泄露。
    candidates = [ref, ref.upper(), f'YHDET_SECRET_{ref}'.upper(), f'YHDET_{ref}'.upper()]
    for name in candidates:
        value = os.getenv(name)
        if value:
            return value.strip()
    # 兼容从 /opt/data/.env 读取但不打印内容。
    env_path = Path('/opt/data/.env')
    if env_path.exists():
        try:
            for line in env_path.read_text(errors='ignore').splitlines():
                if not line or line.lstrip().startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                if k.strip() in candidates:
                    return v.strip().strip('"').strip("'")
        except Exception:
            return ''
    return ''


def _fetch_channel_source(ch: sqlite3.Row) -> dict[str, Any]:
    url = (ch['endpoint_url'] or '').strip()
    if not url:
        raise HTTPException(status_code=400, detail='接口地址为空')
    headers = {'Accept': 'application/json', 'User-Agent': 'yhdet-channel-sync/1.0'}
    auth_type = (ch['auth_type'] or 'none').strip().lower()
    secret = _resolve_channel_secret(ch['auth_secret_ref'])
    if auth_type in {'bearer', 'api_key', 'apikey'}:
        if not secret:
            raise HTTPException(status_code=400, detail='接口密钥引用未解析，请检查服务器环境变量')
        if auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {secret}'
        else:
            headers['X-API-Key'] = secret
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read(1024 * 1024)
            charset = resp.headers.get_content_charset() or 'utf-8'
            return json.loads(body.decode(charset, errors='replace'))
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'接口返回 HTTP {exc.code}')
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'接口请求失败：{type(exc).__name__}')



def _normalize_iso_time(value: Any) -> str:
    raw = str(value or '').strip()
    if not raw:
        return now()
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw[:19].replace('T', ' ') if len(raw) >= 10 else now()


def _prefer_source_url(url: str, content: str, title: str) -> str:
    import re
    from urllib.parse import quote
    raw_url = (url or '').strip()
    raw = content or title or ''
    # Prefer actual topic/article URLs inside text, not author profile URLs.
    for pattern in [
        r'https?://(?:www\.)?linux\.do/t/\S+',
        r'https?://forum\.naixi\.net/(?:thread|forum|topic|post|t)-[^\s)\]】>]+',
        r'https?://(?:www\.)?[^\s)\]】>]+/(?:thread|topic|post|t)/[^\s)\]】>]+',
    ]:
        m = re.search(pattern, raw)
        if m:
            return m.group(0).rstrip(').,，。]】>')[:1000]
    m = re.search(r'https?://(?:www\.)?linux\.do/\S+', raw)
    if m:
        return m.group(0).rstrip(').,，。]】>')[:1000]
    # Author profile links are not source posts; avoid exposing them as 原帖.
    if re.search(r'forum\.naixi\.net/space-uid-\d+\.html', raw_url):
        return ''
    if 't.me/' in raw_url and ('linux.do' in raw.lower() or '中发帖' in raw):
        first_line = raw.strip().splitlines()[0] if raw.strip() else title
        m2 = re.search(r'在\s+(.+?)\s+中发帖', first_line)
        query = (m2.group(1).strip() if m2 else title.strip())[:120]
        if query:
            return ('https://linux.do/search?q=' + quote(query))[:1000]
    return raw_url[:1000]

def _normalize_source_items(payload: dict[str, Any], mapping: dict[str, str]) -> list[dict[str, Any]]:
    raw_items = _get_mapping_value(payload, mapping.get('items', 'items'), [])
    if not isinstance(raw_items, list):
        raw_items = payload.get('data') if isinstance(payload.get('data'), list) else []
    out: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        content = str(_get_mapping_value(item, mapping.get('content', 'content'), '') or '').strip()
        title = str(_get_mapping_value(item, mapping.get('title', 'title'), '') or '').strip()
        if not content and not title:
            continue
        external_id = str(_get_mapping_value(item, mapping.get('external_id', 'external_id'), '') or '').strip()
        if not external_id:
            external_id = hashlib.sha256((title + '\n' + content).encode('utf-8')).hexdigest()[:24]
        if not title:
            title = content.splitlines()[0][:80] if content else '频道内容'
        external_url_raw = str(_get_mapping_value(item, mapping.get('external_url', 'external_url'), '') or '')
        out.append({
            'external_id': external_id[:200],
            'title': title[:160],
            'content': content or title,
            'author_name': str(_get_mapping_value(item, mapping.get('author_name', 'author_name'), 'TG频道') or 'TG频道')[:80],
            'external_url': _prefer_source_url(external_url_raw, content, title),
            'created_at': _normalize_iso_time(_get_mapping_value(item, mapping.get('created_at', 'created_at'), '') or _get_mapping_value(item, 'message_date', '') or now()),
            'payload': item,
        })
    return out


def _sync_channel_from_source(conn: sqlite3.Connection, ch: sqlite3.Row) -> dict[str, Any]:
    if ch["mode"] != "api" or not ch["endpoint_url"]:
        raise HTTPException(status_code=400, detail="该频道不是接口模式或未配置接口地址")
    payload = _fetch_channel_source(ch)
    mapping = _load_channel_mapping(ch["mapping_json"])
    items = _normalize_source_items(payload, mapping)
    created = 0
    updated = 0
    for item in items:
        existed = conn.execute("SELECT id FROM channel_posts WHERE channel_id=? AND external_id=?", (ch['id'], item['external_id'])).fetchone()
        if existed:
            conn.execute(
                """UPDATE channel_posts SET title=?, content=?, author_name=?, external_url=?, source_payload_json=?, created_at=?, updated_at=? WHERE id=?""",
                (item['title'], item['content'], item['author_name'], item['external_url'], json.dumps(item['payload'], ensure_ascii=False), item['created_at'] or now(), now(), existed['id']),
            )
            updated += 1
        else:
            conn.execute(
                """INSERT INTO channel_posts(channel_id,title,content,author_name,external_id,external_url,source_payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (ch['id'], item['title'], item['content'], item['author_name'], item['external_id'], item['external_url'], json.dumps(item['payload'], ensure_ascii=False), item['created_at'] or now(), now()),
            )
            created += 1
    pruned = prune_channel_posts(conn, ch['id'], 50)
    conn.execute("UPDATE channels SET last_sync_at=?, updated_at=? WHERE id=?", (now(), now(), ch['id']))
    return {"ok": True, "message": f"同步完成：新增 {created} 条，更新 {updated} 条，清理旧数据 {pruned} 条", "created": created, "updated": updated, "pruned": pruned, "total": len(items)}


def _channel_sync_stale(last_sync_at: str | None, max_age_seconds: int = 60) -> bool:
    if not last_sync_at:
        return True
    try:
        last = datetime.fromisoformat(str(last_sync_at).replace('T', ' '))
    except Exception:
        return True
    return datetime.utcnow() - last > timedelta(seconds=max_age_seconds)


def _auto_sync_channel_if_stale(conn: sqlite3.Connection, ch: sqlite3.Row) -> dict[str, Any] | None:
    if ch["mode"] != "api" or not ch["endpoint_url"] or not _channel_sync_stale(ch["last_sync_at"]):
        return None
    try:
        return _sync_channel_from_source(conn, ch)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"频道自动同步失败：{type(exc).__name__}")


@app.post("/api/admin/channels/{channel_id}/test-source")
def admin_test_channel_source(channel_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        ch = conn.execute("SELECT * FROM channels WHERE id=?", (channel_id,)).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="频道不存在")
    if ch["mode"] != "api" or not ch["endpoint_url"]:
        return {"ok": False, "message": "请先配置接口模式和接口地址"}
    payload = _fetch_channel_source(ch)
    mapping = _load_channel_mapping(ch["mapping_json"])
    items = _normalize_source_items(payload, mapping)
    return {"ok": True, "message": f"接口连通，解析到 {len(items)} 条内容", "count": len(items), "sample": items[:3]}


@app.post("/api/admin/channels/{channel_id}/sync")
def admin_sync_channel(channel_id: int, authorization: str | None = Header(default=None)):
    require_admin(current_user(authorization))
    with db() as conn:
        ch = conn.execute("SELECT * FROM channels WHERE id=?", (channel_id,)).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="频道不存在")
        return _sync_channel_from_source(conn, ch)


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


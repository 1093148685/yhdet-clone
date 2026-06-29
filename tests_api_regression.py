#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    tmp = tempfile.TemporaryDirectory()
    os.environ["YHDET_DB_PATH"] = str(Path(tmp.name) / "test-community.db")
    seed_password = os.getenv("YHDET_SEED_USER_PASSWORD", "change-me")

    # Import after env is set. The app supports DB path override for tests.
    mod = importlib.import_module("backend.main")
    client = TestClient(mod.app)

    health = client.get("/api/health")
    assert_true(health.status_code == 200 and health.json()["ok"] is True, "health failed")

    home = client.get("/api/home")
    assert_true(home.status_code == 200, "home failed")
    home_json = home.json()
    assert_true(len(home_json["posts"]) >= 5, "seed posts missing")
    assert_true(home_json["stats"]["users"] >= 1, "seed users missing")

    suffix = int(time.time() * 1000)
    username = f"质检用户{suffix}"
    reg = client.post("/api/register", json={"username": username, "email": f"qa{suffix}@example.com", "password": "123456"})
    assert_true(reg.status_code == 200, f"register failed: {reg.text}")
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/me", headers=headers)
    assert_true(me.status_code == 200 and me.json()["user"]["username"] == username, "me failed")

    title = f"质检发帖 {suffix}"
    post = client.post("/api/posts", json={"title": title, "content": "这是一条自动化质检帖子。\n用于验证真实写入。"}, headers=headers)
    assert_true(post.status_code == 200, f"create post failed: {post.text}")
    post_id = post.json()["id"]

    detail = client.get(f"/api/posts/{post_id}")
    assert_true(detail.status_code == 200 and detail.json()["post"]["title"] == title, "post detail failed")

    comment = client.post(f"/api/posts/{post_id}/comments", json={"content": "自动化质检评论"}, headers=headers)
    assert_true(comment.status_code == 200, f"comment failed: {comment.text}")

    detail2 = client.get(f"/api/posts/{post_id}")
    assert_true(any(c["content"] == "自动化质检评论" for c in detail2.json()["comments"]), "comment not persisted")

    search_posts = client.get("/api/search", params={"q": title, "type": "posts"})
    assert_true(any(p["id"] == post_id for p in search_posts.json()["items"]), "post search failed")

    search_users = client.get("/api/search", params={"q": username, "type": "users"})
    assert_true(any(u["username"] == username for u in search_users.json()["items"]), "user search failed")

    bad = client.post("/api/posts", json={"title": "未登录", "content": "应失败"})
    assert_true(bad.status_code == 401, "unauthorized post should fail")

    not_found = client.get("/api/posts/99999999")
    assert_true(not_found.status_code == 404, "missing post should 404")

    for path in ["/", "/login", "/register", "/new", f"/post/{post_id}", f"/user/{reg.json()['user']['id']}", "/games", "/music", "/admin"]:
        r = client.get(path)
        assert_true(r.status_code == 200 and "易聊社区" in r.text, f"SPA route failed: {path}")

    # Admin API requires admin role and supports dashboard/content operations.
    forbidden = client.get("/api/admin/overview", headers=headers)
    assert_true(forbidden.status_code == 403, "normal user should not access admin")
    admin_login = client.post("/api/login", json={"username": "水鱼PyLab", "password": seed_password})
    assert_true(admin_login.status_code == 200, f"admin login failed: {admin_login.text}")
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}
    overview = client.get("/api/admin/overview", headers=admin_headers)
    assert_true(overview.status_code == 200 and "stats" in overview.json(), "admin overview failed")
    admin_posts = client.get("/api/admin/posts", headers=admin_headers)
    assert_true(admin_posts.status_code == 200 and len(admin_posts.json()["items"]) >= 1, "admin posts failed")
    pin = client.patch(f"/api/admin/posts/{post_id}", json={"pinned": True}, headers=admin_headers)
    assert_true(pin.status_code == 200, f"admin pin failed: {pin.text}")
    ann = client.post("/api/admin/announcements", json={"content": "自动化后台公告"}, headers=admin_headers)
    assert_true(ann.status_code == 200, f"admin announcement failed: {ann.text}")
    donor = client.post("/api/admin/donors", json={"name": "质检捐赠者", "amount": "1元", "donated_at": "2026.6.29"}, headers=admin_headers)
    assert_true(donor.status_code == 200, f"admin donor failed: {donor.text}")

    tmp.cleanup()
    print("PASS api regression: health/home/register/login/me/post/detail/comment/search/auth/spa/admin")


if __name__ == "__main__":
    main()

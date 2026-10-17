# -*- coding: utf-8 -*-
"""
张函瑞17岁生日应援 - 粉丝寄语后端服务
功能: 静态文件服务 + 寄语 REST API (增删改查), 启动时自动在 hanrui 库建表
运行: python server.py
访问: http://localhost:8080/birthday.html
"""
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# ===== 数据库配置 =====
# 线上部署: 在平台环境变量中设置 HR_DB_HOST/HR_DB_PORT/HR_DB_USER/HR_DB_PASSWORD/HR_DB_NAME
# 本地开发: 在 db_local.py 中覆盖(该文件不上传)
DB_CONFIG = {
    "host": os.environ.get("HR_DB_HOST", "localhost"),
    "port": int(os.environ.get("HR_DB_PORT", "3306")),
    "user": os.environ.get("HR_DB_USER", "root"),
    "password": os.environ.get("HR_DB_PASSWORD", ""),
    "database": os.environ.get("HR_DB_NAME", "hanrui"),
    "charset": "utf8mb4",
}

try:
    from db_local import DB_LOCAL
    DB_CONFIG.update(DB_LOCAL)
except ImportError:
    pass

# 云数据库(如 Aiven)强制 SSL; 本地 MySQL 不需要
if DB_CONFIG["host"] not in ("localhost", "127.0.0.1"):
    import ssl as _ssl
    DB_CONFIG["ssl"] = {"check_hostname": False, "verify_mode": _ssl.CERT_NONE}

PORT = int(os.environ.get("PORT", "8000"))  # 云平台会自动注入 PORT

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fan_messages (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nickname VARCHAR(32) NOT NULL DEFAULT '神秘粉丝',
  content VARCHAR(200) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_WISH_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS wish_stats (
  id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
  wish_count INT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def get_conn():
    import pymysql
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """启动时自动建表; 失败仅提示, 不影响静态页面"""
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_WISH_TABLE_SQL)
            cur.execute(
                "INSERT IGNORE INTO wish_stats (id, wish_count) VALUES (1, 0)")
        conn.commit()
        conn.close()
        print("[DB] 已连接 hanrui 数据库, fan_messages / wish_stats 表就绪")
    except Exception as e:
        print("[DB] 连接失败: %s" % e)
        print("[DB] 请检查 server.py 顶部的 DB_CONFIG; 页面将以本地模式运行(寄语不保存到数据库)")


class Handler(SimpleHTTPRequestHandler):
    # ---------- 工具 ----------
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8-sig"))
        except Exception:
            return {}

    def _msg_id(self):
        try:
            return int(self.path.rsplit("/", 1)[-1])
        except ValueError:
            return None

    # ---------- 路由 ----------
    def do_OPTIONS(self):
        """跨域预检请求: 允许任何来源的页面调用 API"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/wishes":
            self.api_wish_get()
        elif self.path.startswith("/api/messages"):
            self.api_list()
        else:
            super().do_GET()  # 静态文件

    def do_POST(self):
        if self.path == "/api/messages":
            self.api_create()
        elif self.path == "/api/wishes":
            self.api_wish_incr()
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_PUT(self):
        mid = self._msg_id() if self.path.startswith("/api/messages/") else None
        if mid is None:
            self._json(404, {"ok": False, "error": "not found"})
        else:
            self.api_update(mid)

    def do_DELETE(self):
        mid = self._msg_id() if self.path.startswith("/api/messages/") else None
        if mid is None:
            self._json(404, {"ok": False, "error": "not found"})
        else:
            self.api_delete(mid)

    # ---------- CRUD ----------
    def api_list(self):
        """查: 最新200条寄语"""
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nickname, content, created_at "
                    "FROM fan_messages ORDER BY id DESC LIMIT 200")
                rows = cur.fetchall()
            conn.close()
            data = [{"id": r[0], "nickname": r[1], "content": r[2],
                     "created_at": str(r[3])} for r in rows]
            self._json(200, {"ok": True, "data": data})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    def api_create(self):
        """增: 保存一条寄语"""
        b = self._body()
        nickname = (b.get("nickname") or "").strip()[:32] or "神秘粉丝"
        content = (b.get("content") or "").strip()[:200]
        if not content:
            return self._json(400, {"ok": False, "error": "内容不能为空"})
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO fan_messages (nickname, content) VALUES (%s, %s)",
                    (nickname, content))
                conn.commit()
                new_id = cur.lastrowid
            conn.close()
            self._json(200, {"ok": True, "data": {
                "id": new_id, "nickname": nickname, "content": content}})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    def api_update(self, mid):
        """改: 修改寄语内容/昵称"""
        b = self._body()
        nickname = (b.get("nickname") or "").strip()[:32]
        content = (b.get("content") or "").strip()[:200]
        if not content:
            return self._json(400, {"ok": False, "error": "内容不能为空"})
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                if nickname:
                    cur.execute(
                        "UPDATE fan_messages SET nickname=%s, content=%s WHERE id=%s",
                        (nickname, content, mid))
                else:
                    cur.execute(
                        "UPDATE fan_messages SET content=%s WHERE id=%s",
                        (content, mid))
                conn.commit()
                n = cur.rowcount
            conn.close()
            self._json(200, {"ok": True, "changed": n})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    def api_delete(self, mid):
        """删: 删除一条寄语"""
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fan_messages WHERE id=%s", (mid,))
                conn.commit()
                n = cur.rowcount
            conn.close()
            self._json(200, {"ok": True, "changed": n})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    # ---------- 许愿计数 ----------
    def api_wish_get(self):
        """查: 总许愿次数(所有访客共享)"""
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT wish_count FROM wish_stats WHERE id=1")
                row = cur.fetchone()
            conn.close()
            self._json(200, {"ok": True, "count": row[0] if row else 0})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    def api_wish_incr(self):
        """增: 许愿次数 +1, 返回最新总数"""
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE wish_stats SET wish_count = wish_count + 1 WHERE id=1")
                conn.commit()
                cur.execute("SELECT wish_count FROM wish_stats WHERE id=1")
                count = cur.fetchone()[0]
            conn.close()
            self._json(200, {"ok": True, "count": count})
        except Exception as e:
            self._json(503, {"ok": False, "error": str(e)})

    # 只打印 API 请求日志, 静态资源不刷屏
    def log_message(self, fmt, *args):
        if getattr(self, "path", "").startswith("/api/"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    init_db()
    print("服务已启动: http://localhost:%d/birthday.html" % PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

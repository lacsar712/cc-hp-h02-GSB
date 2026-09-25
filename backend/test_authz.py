"""越权核对：质检三处不得越权，炮制员够线清炒必须成功。

同时覆盖三条验收：
  1. 质检提交后行数不增（接口 403，列表不涨行）；
  2. 炮制员递交够线清炒必须成功（201，行数加一，结论放行）；
  3. 质检首页无表单（form-flag 开关关闭，炮制员开启）。

本环境没有 PostgreSQL，用内存表桩掉 app.connect；SQL 与真实路径一致。
运行：python3 test_authz.py
"""

import json

from fastapi.testclient import TestClient

import app as app_module


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class FakeConn:
    """内存版 batches 表，只认 app.py 里那几条 SQL。"""

    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        if sql.strip().startswith("CREATE TABLE"):
            return FakeResult([])
        if "SELECT COUNT(*)" in sql:
            return FakeResult([{"n": len(self.store)}])
        if "ORDER BY id DESC" in sql:
            ordered = sorted(self.store, key=lambda r: r["id"], reverse=True)
            cols = ("id", "herb", "doc", "verdict", "reason", "created_by")
            return FakeResult([{k: r[k] for k in cols} for r in ordered])
        if sql.strip().startswith("INSERT"):
            herb, doc_json, verdict, reason, created_by, created_at = params
            row = {
                "id": len(self.store) + 1,
                "herb": herb,
                "doc": json.loads(doc_json),
                "verdict": verdict,
                "reason": reason,
                "created_by": created_by,
                "created_at": created_at,
            }
            self.store.append(row)
            if "RETURNING" in sql:
                cols = ("id", "herb", "doc", "verdict", "reason", "created_by")
                return FakeResult([{k: row[k] for k in cols}])
            return FakeResult([])
        raise AssertionError(f"未预期的 SQL: {sql}")

    def commit(self):
        pass


def main():
    store = []
    app_module.connect = lambda: FakeConn(store)

    with TestClient(app_module.app) as client:
        assert len(store) == 2, "启动应写入甘草、黄芩两条样例"

        def login(username, password):
            res = client.post("/api/auth/login", json={"username": username, "password": password})
            assert res.status_code == 200, res.text
            return {"Authorization": f"Bearer {res.json()['access_token']}"}

        checker = login("checker", "check123456")
        processor = login("processor", "herb123456")

        def row_count(auth):
            res = client.get("/api/batches", headers=auth)
            assert res.status_code == 200, res.text
            return len(res.json())

        in_spec = {"herb": "白芍", "steps": [{"name": "清炒", "temp_c": 110, "minutes": 10}]}

        # 验收三：质检首页无表单（开关关闭），炮制员开启
        flag = client.get("/api/auth/form-flag", headers=checker)
        assert flag.status_code == 200 and flag.json() == {"show_form": False}, flag.text
        flag = client.get("/api/auth/form-flag", headers=processor)
        assert flag.status_code == 200 and flag.json() == {"show_form": True}, flag.text

        # 验收一：质检提交后行数不增
        before = row_count(checker)
        res = client.post("/api/batches", headers=checker, json=in_spec)
        assert res.status_code == 403, res.text
        assert res.json()["detail"] == "仅炮制员可写入记录", res.text
        assert row_count(checker) == before, "质检提交后行数不应增加"

        # 验收二：炮制员递交够线清炒必须成功，行数加一
        before = row_count(processor)
        res = client.post("/api/batches", headers=processor, json=in_spec)
        assert res.status_code == 201, res.text
        assert res.json()["verdict"] == "放行", res.text
        assert row_count(processor) == before + 1, "炮制员提交后行数应加一"

        # 兜底：未登录一律 401
        res = client.post("/api/batches", json=in_spec)
        assert res.status_code == 401, res.text
        res = client.get("/api/auth/form-flag")
        assert res.status_code == 401, res.text

    print("OK: 质检提交行数不增 / 炮制员提交行数加一 / 质检首页无表单")


if __name__ == "__main__":
    main()

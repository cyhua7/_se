"""E2E tests for nqu-student-system - start the real Express server (server.js)
against a temporary copy of the project data, then exercise every API and the
static pages like a real user would.
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 3000
BASE = f"http://{HOST}:{PORT}"
SERVER_PACKAGES = ("server.js", "public", "data")


def _port_is_busy(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _wait_until_ready(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("伺服器沒有在期限內啟動完成")


class TestSchoolE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if _port_is_busy(HOST, PORT):
            raise RuntimeError(
                f"Port {PORT} 已被佔用，請先關閉 http://localhost:{PORT} 的伺服器再測試"
            )

        node_modules = PROJECT_ROOT / "node_modules"
        if not node_modules.is_dir():
            raise RuntimeError("找不到 node_modules，請先在 02_school 執行 npm install")

        cls._tmp = Path(tempfile.mkdtemp(prefix="nqu-school-e2e-"))
        try:
            for name in SERVER_PACKAGES:
                src = PROJECT_ROOT / name
                dst = cls._tmp / name
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        except Exception:
            shutil.rmtree(cls._tmp, ignore_errors=True)
            raise

        env = dict(os.environ)
        env["NODE_PATH"] = str(node_modules)

        cls._proc = subprocess.Popen(
            ["node", "server.js"],
            cwd=str(cls._tmp),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            _wait_until_ready()
        except Exception as exc:
            output = ""
            if cls._proc.poll() is not None and cls._proc.stdout:
                output = cls._proc.stdout.read()
            cls._proc.kill()
            shutil.rmtree(cls._tmp, ignore_errors=True)
            raise RuntimeError(f"伺服器啟動失敗（{exc}）：{output}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_proc") and cls._proc.poll() is None:
            cls._proc.terminate()
            try:
                cls._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls._proc.kill()
        if hasattr(cls, "_tmp"):
            shutil.rmtree(cls._tmp, ignore_errors=True)

    # ---- 請求輔助方法 ----

    def get(self, path):
        return requests.get(BASE + path, timeout=10)

    def post(self, path, payload):
        return requests.post(BASE + path, json=payload, timeout=10)

    def put(self, path, payload):
        return requests.put(BASE + path, json=payload, timeout=10)

    def assert_success(self, response):
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"), data)
        return data

    # ---- 登入 ----

    def test_login_success(self):
        data = self.assert_success(self.post("/api/login", {
            "studentId": "A123456789",
            "password": "123456",
        }))
        self.assertEqual(data["user"]["name"], "陳小明")
        self.assertEqual(data["user"]["studentId"], "A123456789")
        self.assertNotIn("password", data["user"])

    def test_login_wrong_password(self):
        resp = self.post("/api/login", {"studentId": "A123456789", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "帳號或密碼錯誤")

    def test_login_unknown_student(self):
        resp = self.post("/api/login", {"studentId": "NOBODY", "password": "123456"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["success"])

    # ---- 靜態頁面 ----

    def test_index_page_served(self):
        resp = self.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("國立金門大學", resp.text)
        self.assertIn("login-form", resp.text)

    def test_dashboard_page_served(self):
        resp = self.get("/dashboard.html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("系統首頁", resp.text)

    def test_static_css_served(self):
        resp = self.get("/css/style.css")
        self.assertEqual(resp.status_code, 200)

    # ---- 成績查詢 ----

    def test_grades_success(self):
        data = self.assert_success(self.get("/api/grades?studentId=A123456789"))
        semesters = data["semesters"]
        self.assertEqual(
            set(semesters.keys()), {"113-1", "113-2", "114-1", "114-2"}
        )
        first = semesters["113-1"][0]
        self.assertEqual(first["courseId"], "CS001")
        self.assertEqual(first["score"], 82)

    def test_grades_missing_student_id(self):
        resp = self.get("/api/grades")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "缺少學號")

    def test_grades_unknown_student(self):
        resp = self.get("/api/grades?studentId=NOBODY")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["message"], "查無此學生的成績資料")

    # ---- 我的課表 ----

    def test_schedule_success(self):
        data = self.assert_success(self.get("/api/schedule?studentId=A123456789"))
        courses = data["courses"]
        self.assertGreaterEqual(len(courses), 10)
        program = next(c for c in courses if c["courseName"] == "計算機程式設計")
        self.assertEqual((program["day"], program["period"]), ("星期一", 3))

        data2 = self.assert_success(self.get("/api/schedule?studentId=A987654321"))
        names = [c["courseName"] for c in data2["courses"]]
        self.assertIn("微積分", names)

    def test_schedule_missing_student_id(self):
        resp = self.get("/api/schedule")
        self.assertEqual(resp.json()["message"], "缺少學號")

    # ---- 選課系統 ----

    def test_courses_list_with_enrollment_flags(self):
        data = self.assert_success(self.get("/api/courses?studentId=A123456789"))
        self.assertEqual(len(data["courses"]), 12)
        self.assertEqual(
            data["myCourseIds"], ["CS401", "GE202", "CS202", "CS102"]
        )
        for course in data["courses"]:
            expected = course["courseId"] in data["myCourseIds"]
            self.assertEqual(course["isEnrolled"], expected)
        cs101 = next(c for c in data["courses"] if c["courseId"] == "CS101")
        self.assertTrue(cs101["isFull"])
        self.assertTrue(cs101["status"], "已額滿")

    def test_courses_missing_student_id(self):
        resp = self.get("/api/courses")
        self.assertEqual(resp.json()["message"], "缺少學號")

    def test_enroll_and_duplicate_and_full(self):
        # 先確認 CS301 目前可選
        before = self.assert_success(self.get("/api/courses?studentId=A987654321"))
        cs301_before = next(c for c in before["courses"] if c["courseId"] == "CS301")
        self.assertFalse(cs301_before["isEnrolled"])
        original_enrolled = cs301_before["enrolled"]

        # 選課成功
        data = self.assert_success(self.post("/api/enroll", {
            "studentId": "A987654321",
            "courseId": "CS301",
        }))
        self.assertEqual(data["message"], "已成功選修：演算法")

        # 資料真的有寫入：enrolled 人數 +1、狀態變已選
        after = self.assert_success(self.get("/api/courses?studentId=A987654321"))
        cs301_after = next(c for c in after["courses"] if c["courseId"] == "CS301")
        self.assertEqual(cs301_after["enrolled"], original_enrolled + 1)
        self.assertTrue(cs301_after["isEnrolled"])
        self.assertIn("CS301", after["myCourseIds"])

        # 重複選課被拒絕
        resp = self.post("/api/enroll", {
            "studentId": "A987654321",
            "courseId": "CS301",
        })
        self.assertEqual(resp.json()["message"], "你已經選過這門課了")

        # 額滿課程無法選課
        full_course = next(
            c for c in after["courses"]
            if c["isFull"] and not c["isEnrolled"]
        )
        resp = self.post("/api/enroll", {
            "studentId": "A987654321",
            "courseId": full_course["courseId"],
        })
        self.assertFalse(resp.json()["success"])
        self.assertEqual(resp.json()["message"], "這門課已額滿，無法選課")

    def test_enroll_unknown_student_or_course(self):
        resp = self.post("/api/enroll", {"studentId": "NOBODY", "courseId": "CS301"})
        self.assertFalse(resp.json()["success"])
        self.assertEqual(resp.json()["message"], "查無此學生")

        resp = self.post("/api/enroll", {"studentId": "A123456789", "courseId": "NOPE"})
        self.assertFalse(resp.json()["success"])
        self.assertEqual(resp.json()["message"], "查無此課程")

    def test_drop_flow(self):
        # A987654321 原本就選了 MA201
        before = self.assert_success(self.get("/api/courses?studentId=A987654321"))
        ma201 = next(c for c in before["courses"] if c["courseId"] == "MA201")
        self.assertTrue(ma201["isEnrolled"])
        original_enrolled = ma201["enrolled"]

        # 退選成功
        data = self.assert_success(self.post("/api/drop", {
            "studentId": "A987654321",
            "courseId": "MA201",
        }))
        self.assertEqual(data["message"], "已退選：微積分")

        # 資料真的有寫入：enrolled 人數 -1、狀態變成未選
        after = self.assert_success(self.get("/api/courses?studentId=A987654321"))
        ma201_after = next(c for c in after["courses"] if c["courseId"] == "MA201")
        self.assertEqual(ma201_after["enrolled"], original_enrolled - 1)
        self.assertFalse(ma201_after["isEnrolled"])
        self.assertNotIn("MA201", after["myCourseIds"])

        # 沒有選的課退選會被拒絕
        resp = self.post("/api/drop", {
            "studentId": "A987654321",
            "courseId": "MA201",
        })
        self.assertFalse(resp.json()["success"])
        self.assertEqual(resp.json()["message"], "你沒有選這門課，無法退選")

    # ---- 畢業學分 ----

    def test_graduation_success(self):
        data = self.assert_success(self.get("/api/graduation?studentId=A123456789"))
        graduation = data["graduation"]
        self.assertEqual(graduation["totalRequired"], 128)
        self.assertEqual(set(graduation["categories"]), {
            "通識必修", "專業必修", "專業選修", "自由選修",
        })
        self.assertEqual(graduation["categories"]["通識必修"]["completed"], 8)

    def test_graduation_unknown_student(self):
        resp = self.get("/api/graduation?studentId=NOBODY")
        self.assertEqual(resp.json()["message"], "查無此學生")

    # ---- 校務公告 ----

    def test_announcements(self):
        data = self.assert_success(self.get("/api/announcements"))
        announcements = data["announcements"]
        self.assertEqual(len(announcements), 8)
        self.assertEqual(announcements[0]["title"], "114學年度第二學期註冊預告")
        self.assertTrue(any(a["important"] for a in announcements))

    # ---- 個人資料 ----

    def test_profile_get(self):
        data = self.assert_success(self.get("/api/profile?studentId=A123456789"))
        user = data["user"]
        self.assertEqual(user["name"], "陳小明")
        self.assertEqual(user["studentId"], "A123456789")
        self.assertNotIn("password", user)

    def test_profile_update_and_reload(self):
        original = self.assert_success(
            self.get("/api/profile?studentId=A123456789")
        )["user"]

        payload = {
            "studentId": "A123456789",
            "email": "e2e.test@example.com",
            "phone": "0912-345-678",
            "address": "金門縣金寧鄉（E2E 測試地址）",
            "note": "E2E 測試備註",
        }
        data = self.assert_success(self.put("/api/profile", payload))
        self.assertEqual(data["message"], "個人資料已更新")
        self.assertEqual(data["user"]["email"], "e2e.test@example.com")

        reloaded = self.assert_success(
            self.get("/api/profile?studentId=A123456789")
        )["user"]
        self.assertEqual(reloaded["email"], "e2e.test@example.com")
        self.assertEqual(reloaded["phone"], "0912-345-678")
        self.assertEqual(reloaded["address"], "金門縣金寧鄉（E2E 測試地址）")
        self.assertEqual(reloaded["note"], "E2E 測試備註")

        # 還原成原始資料，讓資料檔維持乾淨
        self.assert_success(self.put("/api/profile", {
            "studentId": "A123456789",
            "email": original["email"],
            "phone": original["phone"] or "",
            "address": original["address"] or "",
            "note": original["note"] or "",
        }))

    def test_profile_update_invalid_email(self):
        resp = self.put("/api/profile", {
            "studentId": "A123456789",
            "email": "not-an-email",
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Email 格式不正確")

    def test_profile_update_missing_student_id(self):
        resp = self.put("/api/profile", {"email": "a@b.com"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["message"], "缺少學號")

    def test_profile_update_unknown_student(self):
        resp = self.put("/api/profile", {
            "studentId": "NOBODY",
            "email": "a@b.com",
        })
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["message"], "查無此學生")

    def test_profile_missing_student_id(self):
        resp = self.get("/api/profile")
        self.assertEqual(resp.json()["message"], "缺少學號")


if __name__ == "__main__":
    unittest.main()
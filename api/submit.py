"""Hàm serverless nhận phiếu khảo sát và ghi một dòng vào Google Sheets.

Vercel chạy hàm này khi có POST tới /api/submit, xong thì tắt. Ổ đĩa của Vercel là
tạm và bị xoá sau mỗi lần chạy, nên dữ liệu bắt buộc phải đi ra ngoài, ở đây là Sheet.

Hai biến môi trường cần đặt trong bảng điều khiển Vercel:
  GOOGLE_SERVICE_ACCOUNT_JSON  nội dung file khoá JSON của service account
  SHEET_ID                     mã của Google Sheet, lấy trong đường dẫn của Sheet
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

from quality import assess

SHEET_ID = os.environ.get("SHEET_ID", "")
TAB = os.environ.get("SHEET_TAB", "responses")
VN = timezone(timedelta(hours=7))

# Thứ tự cột trong Sheet. Giữ cố định để các dòng luôn thẳng hàng nhau.
META = ["ts", "rid", "verdict", "flags", "total_min", "sec_per_item",
        "nudges", "irv", "msd", "straight_run"]
BLOCKS = {"EFF": 4, "REL": 4, "SEC": 4, "STF": 3, "PCT": 4,
          "PRK": 5, "TAX": 4, "CI": 3, "WOM": 3, "SAT": 4}
ITEMS = ["%s%d" % (b, i) for b, n in BLOCKS.items() for i in range(1, n + 1)]
QC_CODES = ["AC1", "AC2", "BOG", "SYN1", "SYN2", "ANT1", "ANT2"]
DEMO = ["screen", "gender", "age", "edu", "freq", "systype", "retailer", "spend"]
ERRQ = ["err_exp", "err_type", "err_fix", "open_good", "open_bad"]
COLUMNS = META + ITEMS + QC_CODES + DEMO + ERRQ


def access_token():
    """Đổi khoá service account lấy access token của Google."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("thieu bien moi truong GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    creds.refresh(Request())
    return creds.token


def sheet_call(method, path, token, body=None):
    url = "https://sheets.googleapis.com/v4/spreadsheets/%s%s" % (SHEET_ID, path)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def ensure_header(token):
    """Ghi hàng tiêu đề nếu Sheet còn trống. Chỉ xảy ra ở phiếu đầu tiên."""
    got = sheet_call("GET", "/values/%s!A1:A1" % TAB, token)
    if got.get("values"):
        return
    sheet_call("POST",
               "/values/%s!A1:append?valueInputOption=RAW"
               "&insertDataOption=INSERT_ROWS" % TAB,
               token, {"values": [COLUMNS]})


def to_row(rec):
    ans = rec.get("answers", {})
    q = rec.get("quality", {})
    flat = {
        "ts": rec.get("ts", ""),
        "rid": rec.get("rid", ""),
        "verdict": q.get("verdict", ""),
        "flags": " | ".join(q.get("flags", [])),
        "total_min": round(q.get("total_ms", 0) / 60000, 2),
        "sec_per_item": q.get("sec_per_item", ""),
        "nudges": q.get("nudges", 0),
        "irv": q.get("irv", ""),
        "msd": q.get("msd", ""),
        "straight_run": q.get("straight_run", ""),
    }
    row = []
    for col in COLUMNS:
        v = flat[col] if col in flat else ans.get(col, "")
        if isinstance(v, list):
            v = " | ".join(v)
        elif isinstance(v, float):
            # Ghi số bằng dấu chấm. Nếu để Sheet tự hiểu, bản tiếng Việt đọc "7,83"
            # thành chuỗi chữ và mọi phép lọc hay tính trung bình đều sai.
            v = repr(v)
        row.append(v)
    return row


class handler(BaseHTTPRequestHandler):
    def _json(self, payload, code=200):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            rec = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return self._json({"ok": False, "error": "bad json"}, 400)

        rec["ts"] = datetime.now(VN).isoformat(timespec="seconds")
        rec["quality"] = assess(rec)

        try:
            token = access_token()
            ensure_header(token)
            sheet_call("POST",
                       "/values/%s!A1:append?valueInputOption=RAW"
                       "&insertDataOption=INSERT_ROWS" % TAB,
                       token, {"values": [to_row(rec)]})
        except Exception as e:
            # Không để người trả lời thấy lỗi kỹ thuật, nhưng in ra log Vercel
            # kèm nguyên phiếu để nhóm còn cứu lại được nếu Sheet hỏng.
            print("LOI GHI SHEET:", repr(e), file=sys.stderr)
            print("PHIEU CHUA LUU:", json.dumps(rec, ensure_ascii=False), file=sys.stderr)
            return self._json({"ok": False, "error": "storage"}, 500)

        return self._json({"ok": True, "rid": rec.get("rid")})

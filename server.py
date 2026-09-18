"""Server khảo sát chạy local, chỉ dùng thư viện chuẩn.

    python server.py            -> http://localhost:8000
    python server.py 8080       -> đổi cổng

Dữ liệu ghi vào responses.jsonl (mỗi dòng một phiếu).
Theo dõi chất lượng: http://localhost:8000/admin
Xuất CSV:            http://localhost:8000/export.csv
"""
import csv, io, json, sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "responses.jsonl"

from quality import assess  # logic cham diem dung chung voi api/submit.py


def load():
    if not DATA.exists():
        return []
    out = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def _send(self, body, ctype="application/json", code=200):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/submit":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            rec = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return self._send(json.dumps({"ok": False, "error": "bad json"}), code=400)

        rec["ts"] = datetime.now().isoformat(timespec="seconds")
        rec["quality"] = assess(rec)
        with DATA.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        q = rec["quality"]
        print("  -> phieu %s  %s  %ss/cau  %s" % (
            (rec.get("rid") or "?")[:8], q["verdict"], q["sec_per_item"],
            "; ".join(q["flags"]) or "sach"))
        return self._send(json.dumps({"ok": True, "rid": rec.get("rid")}))

    def do_GET(self):
        if self.path.startswith("/admin"):
            return self._send(self.admin(), "text/html")
        if self.path.startswith("/export.csv"):
            return self._send(self.csv(), "text/csv")
        return super().do_GET()

    def admin(self):
        rows = load()
        tally = {"PASS": 0, "REVIEW": 0, "FAIL": 0}
        for r in rows:
            tally[r.get("quality", {}).get("verdict", "REVIEW")] += 1
        colour = {"PASS": "#1d7a4c", "REVIEW": "#b35309", "FAIL": "#b3261e"}
        trs = ""
        for r in reversed(rows):
            q = r.get("quality", {})
            v = q.get("verdict", "?")
            trs += ("<tr><td>%s</td><td><code>%s</code></td>"
                    "<td style='color:%s;font-weight:600'>%s</td><td>%s ph</td>"
                    "<td>%ss</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                        r.get("ts", ""), (r.get("rid") or "")[:8],
                        colour.get(v, "#666"), v,
                        round(q.get("total_ms", 0) / 60000, 1), q.get("sec_per_item", ""),
                        q.get("straight_run", ""), q.get("irv", ""), q.get("msd", ""),
                        "; ".join(q.get("flags", [])) or "-"))
        return """<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Theo dõi chất lượng phiếu</title><style>
body{font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;max-width:1100px;
margin:30px auto;padding:0 16px;color:#15181d}
table{width:100%%;border-collapse:collapse;font-size:13.5px;margin-top:14px}
th,td{padding:8px 10px;border-bottom:1px solid #e3e6ea;text-align:left;vertical-align:top}
th{background:#f4f6f8;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#5c6470}
.k{display:inline-block;margin-right:22px}.k b{font-size:26px;display:block}
code{background:#f1f3f5;padding:1px 5px;border-radius:4px}a{color:#1f5fa8}
</style></head><body>
<h1>Theo dõi chất lượng phiếu</h1>
<p><span class="k"><b>%d</b>tổng phiếu</span>
<span class="k" style="color:#1d7a4c"><b>%d</b>dùng được</span>
<span class="k" style="color:#b35309"><b>%d</b>cần xem lại</span>
<span class="k" style="color:#b3261e"><b>%d</b>loại</span></p>
<p><a href="/export.csv">Tải CSV cho SPSS / SmartPLS</a> &nbsp;·&nbsp;
<a href="/">Mở bảng hỏi</a></p>
<p style="font-size:12.5px;color:#5c6470"><b>IRV</b> = độ phân tán đáp án của một người.
Quá thấp (&lt;0,45) là điền một cột; quá cao (&gt;1,40) là bấm ngẫu nhiên.
<b>MSD</b> = bước nhảy trung bình giữa hai câu liền nhau; cao là kiểu zigzag.</p>
<table><tr><th>Thời điểm</th><th>Mã</th><th>Kết luận</th><th>Tổng</th><th>Giây/câu</th>
<th>Chuỗi lặp</th><th>IRV</th><th>MSD</th><th>Cờ cảnh báo</th></tr>%s</table>
</body></html>""" % (len(rows), tally["PASS"], tally["REVIEW"], tally["FAIL"],
                     trs or '<tr><td colspan="9">Chưa có phiếu nào.</td></tr>')

    def csv(self):
        rows = load()
        if not rows:
            return "﻿"
        keys = []
        for r in rows:
            for k in r.get("answers", {}):
                if k not in keys:
                    keys.append(k)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["rid", "ts", "verdict", "flags", "total_min", "sec_per_item"] + keys)
        for r in rows:
            q = r.get("quality", {})
            a = r.get("answers", {})
            w.writerow([r.get("rid", ""), r.get("ts", ""), q.get("verdict", ""),
                        "|".join(q.get("flags", [])),
                        round(q.get("total_ms", 0) / 60000, 2), q.get("sec_per_item", "")] +
                       ["|".join(a[k]) if isinstance(a.get(k), list) else a.get(k, "")
                        for k in keys])
        return "﻿" + buf.getvalue()   # BOM để Excel mở đúng tiếng Việt


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print("Bảng hỏi     http://localhost:%d/" % port)
    print("Theo dõi     http://localhost:%d/admin" % port)
    print("Xuất CSV     http://localhost:%d/export.csv" % port)
    print("Ctrl+C để dừng.\n")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

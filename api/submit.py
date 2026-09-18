"""Hàm serverless nhận phiếu khảo sát và ghi một dòng vào Google Sheets.

Vercel chạy hàm này khi có POST tới /api/submit, xong thì tắt. Ổ đĩa của Vercel là
tạm và bị xoá sau mỗi lần chạy, nên dữ liệu bắt buộc phải đi ra ngoài, ở đây là Sheet.

Hai biến môi trường cần đặt trong bảng điều khiển Vercel:
  GOOGLE_SERVICE_ACCOUNT_JSON  nội dung file khoá JSON của service account
  SHEET_ID                     mã của Google Sheet, lấy trong đường dẫn của Sheet
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler


# ---------------------------------------------------------------------------
# Logic cham diem. Nhung thang vao day thay vi de file rieng: Vercel dong goi
# moi file trong api/ thanh mot ham doc lap, nen import chéo giua chung se hong.
# ---------------------------------------------------------------------------
# Đáp án đúng của câu bẫy trực tiếp; phải khớp QC_ITEMS trong survey.js
QC = {"AC1": (2, 0), "AC2": (4, 0), "BOG": (1, 1)}
# Cặp đồng nghĩa / trái nghĩa (psychometric synonyms & antonyms, Meade & Craig 2012)
SYN_PAIR = ("SYN1", "SYN2")   # phải gần nhau
ANT_PAIR = ("ANT1", "ANT2")   # phải ngược nhau

MIN_TOTAL_MS = 150_000    # dưới 2,5 phút cho ~45 câu là không đọc
MIN_PER_ITEM_MS = 1_200
MAX_STRAIGHT = 12         # chuỗi đáp án giống nhau liên tiếp tối đa

# Ngưỡng trên thang 1-5. SD của trả lời hoàn toàn ngẫu nhiên trên 1-5 xấp xỉ 1,41.
IRV_LOW = 0.45            # dưới mức này: gần như điền một cột
IRV_HIGH = 1.40           # trên mức này: đáp án như bốc ngẫu nhiên
MSD_HIGH = 1.90           # nhảy giữa các mức quá lớn: kiểu zigzag
WITHIN_SD_HIGH = 1.25     # trong cùng một khái niệm mà đáp án tán loạn
SYN_GAP = 3               # cặp đồng nghĩa lệch nhau từ 3 mức trở lên
MIN_PAGE_MS = 8_000       # một trang thang đo dưới 8 giây là lướt

SCALE_ITEM = re.compile(r"^(EFF|REL|SEC|STF|PCT|PRK|TAX|CI|WOM|SAT)\d+$")


def scale_answers(ans):
    """Item thang đo thực, bỏ câu kiểm soát và câu nhân khẩu."""
    return {k: v for k, v in ans.items() if SCALE_ITEM.match(k) and isinstance(v, int)}


def display_order(rec):
    """Đáp án xếp theo đúng thứ tự người trả lời NHÌN THẤY trên màn hình.
    Cần cho longstring và zigzag: thứ tự trong dict là thứ tự bấm, không phải thứ tự hiện."""
    ans, order = rec.get("answers", {}), rec.get("order", {})
    seq = []
    for items in order.values():
        for it in items:
            v = ans.get(it.get("code"))
            if isinstance(v, int):
                seq.append(v)
    for k in ("SAT1", "SAT2", "SAT3", "SAT4"):
        if isinstance(ans.get(k), int):
            seq.append(ans[k])
    return seq or list(scale_answers(ans).values())


def stdev(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5


def msd(seq):
    """Mean successive difference: trung bình bước nhảy giữa hai câu liền nhau.
    Rất thấp = điền một cột. Rất cao = zigzag / bấm loạn."""
    if len(seq) < 2:
        return 0.0
    return sum(abs(seq[i] - seq[i - 1]) for i in range(1, len(seq))) / (len(seq) - 1)


def cycle_len(seq, max_period=6):
    """Phát hiện chuỗi lặp theo chu kỳ, ví dụ 1,2,3,4,5,1,2,3,4,5 hoặc 1,2,1,2.
    Trả về độ dài chu kỳ nếu chuỗi lặp phủ phần lớn phiếu, ngược lại 0."""
    n = len(seq)
    for p in range(2, min(max_period, n // 3) + 1):
        if all(seq[i] == seq[i % p] for i in range(n)) and len(set(seq[:p])) > 1:
            return p
    return 0


def by_construct(scale):
    g = {}
    for k, v in scale.items():
        g.setdefault(re.match(r"^[A-Z]+", k).group(), []).append(v)
    return g


def longest_run(seq):
    best = run = 1 if seq else 0
    for i in range(1, len(seq)):
        run = run + 1 if seq[i] == seq[i - 1] else 1
        best = max(best, run)
    return best


def assess(rec):
    """Chấm chất lượng một phiếu."""
    ans = rec.get("answers", {})
    timing = rec.get("timing", {})
    behav = rec.get("behaviour", {})
    scale = scale_answers(ans)
    vals = list(scale.values())
    seq = display_order(rec)          # theo thứ tự nhìn thấy trên màn hình
    n = len(vals)

    failed_qc = [c for c, (exp, tol) in QC.items()
                 if c in ans and abs(int(ans[c]) - exp) > tol]

    total = timing.get("total_ms", 0)
    per_item = total / n if n else 0
    straight = longest_run(seq)
    irv = stdev(vals)                 # độ phân tán đáp án của cá nhân
    jump = msd(seq)                   # bước nhảy trung bình giữa hai câu liền nhau
    cyc = cycle_len(seq)              # chuỗi lặp theo chu kỳ

    # Trong cùng một khái niệm, đáp án lẽ ra phải nhất quán
    groups = by_construct(scale)
    inconsistent = [g for g, v in groups.items() if len(v) >= 3 and stdev(v) > WITHIN_SD_HIGH]

    # Cặp đồng nghĩa: phải gần nhau. Cặp trái nghĩa: phải ngược nhau.
    syn_gap = ant_gap = None
    a, b = (ans.get(SYN_PAIR[0]), ans.get(SYN_PAIR[1]))
    if isinstance(a, int) and isinstance(b, int):
        syn_gap = abs(a - b)
    a, b = (ans.get(ANT_PAIR[0]), ans.get(ANT_PAIR[1]))
    if isinstance(a, int) and isinstance(b, int):
        ant_gap = abs(a - b)         # ngược nhau thì chênh lệch phải LỚN

    # CI3 đảo chiều: đồng ý cao ở cả CI1 lẫn CI3 là tự mâu thuẫn
    contradiction = scale.get("CI1", 0) >= 4 and scale.get("CI3", 0) >= 4

    fast_pages = [p for p, ms in (timing.get("page_ms") or {}).items()
                  if p.startswith("g") and ms < MIN_PAGE_MS]

    flags = []
    if failed_qc:                        flags.append("qc_failed:" + ",".join(failed_qc))
    if total < MIN_TOTAL_MS:             flags.append("too_fast_total")
    if per_item < MIN_PER_ITEM_MS:       flags.append("too_fast_per_item")
    if fast_pages:                       flags.append("fast_pages:%d" % len(fast_pages))
    if straight > MAX_STRAIGHT:          flags.append("straightlining:%d" % straight)
    if n and irv < IRV_LOW:              flags.append("no_variance")
    if irv > IRV_HIGH:                   flags.append("random_responding:%.2f" % irv)
    if jump > MSD_HIGH:                  flags.append("zigzag:%.2f" % jump)
    if cyc:                              flags.append("repeating_pattern:%d" % cyc)
    if inconsistent:                     flags.append("within_inconsistent:" + ",".join(inconsistent))
    if syn_gap is not None and syn_gap >= SYN_GAP:  flags.append("synonym_gap:%d" % syn_gap)
    if ant_gap is not None and ant_gap <= 1:        flags.append("antonym_same:%d" % ant_gap)
    if contradiction:                    flags.append("contradiction_CI")
    if behav.get("blur_count", 0) > 15:  flags.append("many_tab_switches")

    # Cờ đủ nặng để loại thẳng. contradiction_CI KHÔNG nằm ở đây: CI3 là item thang đo
    # thật, người trả lời thật vẫn có thể phân vân. ANT1/ANT2 thì thuần là bẫy nên nặng.
    hard = {"too_fast_total", "no_variance"}
    hard_hit = [f for f in flags if f.split(":")[0] in hard or
                f.startswith(("random_responding", "zigzag", "repeating_pattern", "antonym_same"))]
    if len(failed_qc) >= 2 or hard_hit or len(flags) >= 4:
        verdict = "FAIL"
    elif flags:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    # Trang web đã nhắc tại chỗ trong lúc điền. Người được nhắc rồi sửa lại là tín hiệu
    # TỐT, không phải xấu, họ chịu đọc. Người bị nhắc mà vẫn để nguyên mới đáng ngại.
    nud = rec.get("nudges") or {}
    n_nudge = nud.get("count", 0)
    if n_nudge:
        if not flags:
            flags.append("nudged_then_fixed:%d" % n_nudge)   # ghi nhận, không hạ bậc
        elif n_nudge >= 3 and verdict == "REVIEW":
            verdict = "FAIL"                                  # nhắc nhiều lần mà không sửa
            flags.append("ignored_nudges:%d" % n_nudge)

    return {"verdict": verdict, "flags": flags, "n_items": n, "total_ms": total,
            "sec_per_item": round(per_item / 1000, 2), "straight_run": straight,
            "irv": round(irv, 3), "msd": round(jump, 2), "cycle": cyc,
            "syn_gap": syn_gap, "ant_gap": ant_gap, "nudges": n_nudge,
            "within_inconsistent": inconsistent, "failed_qc": failed_qc}


# ---------------------------------------------------------------------------
# Ghi vao Google Sheets
# ---------------------------------------------------------------------------
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


def diagnose():
    """Kiem tra tung khau ket noi Google Sheets. Chi tra ve trang thai va ten loi,
    khong bao gio in ra noi dung khoa. Go bo sau khi da chay on."""
    out = {}
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    out["co_bien_GOOGLE_SERVICE_ACCOUNT_JSON"] = bool(raw)
    out["do_dai_khoa"] = len(raw)
    out["co_bien_SHEET_ID"] = bool(SHEET_ID)
    out["do_dai_sheet_id"] = len(SHEET_ID)
    out["ten_tab"] = TAB

    try:
        import google.auth  # noqa: F401
        out["thu_vien_google_auth"] = "da cai"
    except Exception as e:
        out["thu_vien_google_auth"] = "THIEU: %s" % type(e).__name__
        return out

    try:
        info = json.loads(raw) if raw else {}
        out["client_email"] = info.get("client_email", "(khong doc duoc)")
    except Exception as e:
        out["doc_khoa"] = "LOI: %s" % type(e).__name__
        return out

    try:
        tok = access_token()
        out["lay_token"] = "OK, dai %d" % len(tok)
    except Exception as e:
        out["lay_token"] = "LOI: %s: %s" % (type(e).__name__, str(e)[:160])
        return out

    try:
        got = sheet_call("GET", "/values/%s!A1:A1" % TAB, tok)
        out["doc_sheet"] = "OK, hang dau: %s" % (got.get("values") or "(trong)")
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode()[:260]
            except Exception:
                pass
        out["doc_sheet"] = "LOI: %s: %s %s" % (type(e).__name__, str(e)[:120], body)
    return out


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        return self._json({"chan_doan": diagnose()})

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

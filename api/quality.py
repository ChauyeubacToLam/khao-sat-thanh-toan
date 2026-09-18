"""Chấm chất lượng phiếu khảo sát.

Module dùng chung cho cả server chạy máy (server.py) và hàm serverless trên
Vercel (api/submit.py), để hai nơi không bao giờ chấm lệch nhau.
"""
import re

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

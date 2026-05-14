
import io
import re
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="統合 直線ロジック×鉄板⭐️アプリ", layout="wide")


HEADERLESS_TARGET_COLUMNS = [
    "日付", "競馬場", "R", "レース名", "芝ダ", "距離", "馬番", "馬名",
    "種牡馬", "父タイプ名", "母父名", "母父タイプ名",
    "性別", "年齢", "斤量", "頭数",
    "前走馬場状態", "前走芝ダ", "前走距離", "前走斤量",
    "休み明け〜戦目", "所属", "調教師", "騎手", "前走騎手",
    "前走着順", "前走着差", "前走頭数",
    "前走通過順1", "前走通過順2", "前走通過順3", "前走通過順4",
    "前走上り3F順", "前走脚質", "前走場所", "前走場所区分"
]

def looks_like_headerless_target(df):
    cols = [str(c).strip() for c in df.columns]
    if len(cols) < 8:
        return False
    date_like = bool(re.fullmatch(r"\d{3,8}", cols[0]))
    place_like = cols[1] in ["札", "函", "福", "新", "東", "中", "名", "京", "阪", "小",
                             "札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
    r_like = bool(re.search(r"\d+", cols[2]))
    return date_like and place_like and r_like


def read_csv_smart(obj):
    encodings = ["utf-8-sig", "utf-8", "cp932", "shift_jis"]
    last_err = None
    for enc in encodings:
        try:
            if isinstance(obj, (str, Path)):
                df = pd.read_csv(obj, encoding=enc)
                if looks_like_headerless_target(df):
                    raw = pd.read_csv(obj, encoding=enc, header=None)
                    raw = raw.iloc[:, :len(HEADERLESS_TARGET_COLUMNS)]
                    raw.columns = HEADERLESS_TARGET_COLUMNS[:len(raw.columns)]
                    return raw
                return df

            obj.seek(0)
            df = pd.read_csv(obj, encoding=enc)
            if looks_like_headerless_target(df):
                obj.seek(0)
                raw = pd.read_csv(obj, encoding=enc, header=None)
                raw = raw.iloc[:, :len(HEADERLESS_TARGET_COLUMNS)]
                raw.columns = HEADERLESS_TARGET_COLUMNS[:len(raw.columns)]
                return raw
            return df
        except Exception as e:
            last_err = e
    raise last_err



def norm_text(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().replace("\u3000", " ")
    s = re.sub(r"\s+", "", s)
    if s.endswith(".0"):
        s = s[:-2]
    return s


def norm_col(c):
    s = str(c).strip().replace("\u3000", "")
    s = s.replace("Ｒ", "R").replace("芝・ダ", "芝ダ").replace("芝ダ・距離", "芝ダ距離")
    s = s.replace("～", "〜")
    return re.sub(r"\s+", "", s)


def to_int(x):
    try:
        if x is None or pd.isna(x):
            return None
        m = re.search(r"-?\d+", str(x))
        return int(m.group(0)) if m else None
    except Exception:
        return None


def to_float(x):
    try:
        if x is None or pd.isna(x):
            return None
        s = str(x).strip()
        if "勝" in s or "同" in s:
            return 0.0
        s = s.replace("秒", "").replace("+", "")
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        return float(m.group(0)) if m else None
    except Exception:
        return None


def parse_date(v):
    s = norm_text(v)
    if not s:
        return ""
    if re.fullmatch(r"\d{6}", s):
        return f"20{s[:2]}.{s[2:4]}.{s[4:6]}"
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}.{s[4:6]}.{s[6:8]}"
    s = s.replace("/", ".").replace("-", ".")
    parts = s.split(".")
    if len(parts) == 3:
        return f"{parts[0]}.{parts[1].zfill(2)}.{parts[2].zfill(2)}"
    return s


def esc(s):
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")



def html_escape(s):
    return esc(s)


def normalize_target(df):
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]

    rename = {
        "場所": "競馬場", "場": "競馬場", "場R": "R", "レース": "R", "レース番号": "R",
        "馬番号": "馬番", "芝ダ距離": "距離", "レース名(クラス)": "レース名",
        "父系統": "父タイプ名", "母父系統": "母父タイプ名",
        "前馬場状態": "前走馬場状態", "前走馬場": "前走馬場状態",
        "前距離": "前走距離", "前芝ダ": "前走芝ダ", "前芝・ダ": "前走芝ダ",
        "前走着": "前走着順", "前着順": "前走着順", "前差": "前走着差",
        "前走上がり3F順": "前走上り3F順", "前走上り順位": "前走上り3F順",
        "前走4角": "前走通過順4", "前4角": "前走通過順4",
        "前走3角": "前走通過順3", "前3角": "前走通過順3", "前頭数": "前走頭数",
    }
    for old, new in rename.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    pmap = {"札": "札幌", "函": "函館", "福": "福島", "新": "新潟", "東": "東京", "中": "中山", "名": "中京", "京": "京都", "阪": "阪神", "小": "小倉"}
    if "競馬場" in df.columns:
        df["競馬場"] = df["競馬場"].apply(lambda x: pmap.get(norm_text(x), norm_text(x)))
    else:
        df["競馬場"] = ""

    df["R"] = df["R"].apply(to_int) if "R" in df.columns else None

    if "距離" in df.columns:
        raw = df["距離"].astype(str)
        if "芝ダ" not in df.columns:
            df["芝ダ"] = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
        else:
            miss = df["芝ダ"].map(norm_text).eq("")
            ext = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
            df.loc[miss, "芝ダ"] = ext[miss]
        df["距離"] = raw.str.extract(r"(\d+)", expand=False).fillna("").apply(to_int)
    else:
        df["距離"] = None
        df["芝ダ"] = df.get("芝ダ", "")

    if "前走距離" in df.columns:
        raw = df["前走距離"].astype(str)
        if "前走芝ダ" not in df.columns:
            df["前走芝ダ"] = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
        else:
            miss = df["前走芝ダ"].map(norm_text).eq("")
            ext = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
            df.loc[miss, "前走芝ダ"] = ext[miss]
        df["前走距離"] = raw.str.extract(r"(\d+)", expand=False).fillna("").apply(to_int)
    else:
        df["前走距離"] = None
        df["前走芝ダ"] = df.get("前走芝ダ", "")

    if "日付" in df.columns:
        df["日付"] = df["日付"].map(parse_date)
    else:
        df["日付"] = ""

    for c in ["レース名", "芝ダ", "馬名", "父タイプ名", "母父タイプ名", "前走芝ダ", "前走脚質", "前走場所"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].map(norm_text)

    for c in ["頭数", "馬番", "前走頭数", "前走着順", "前走着差", "前走通過順3", "前走通過順4", "前走上り3F順"]:
        if c not in df.columns:
            df[c] = ""

    return df


def get_corner_category(pos, field_size):
    pos = to_int(pos)
    field_size = to_int(field_size)
    if pos is None:
        return ""
    if pos == 1:
        return "1番手"
    if field_size is None or field_size <= 0:
        if pos <= 3: return "2〜3番手"
        if pos <= 6: return "4〜6番手"
        if pos <= 10: return "7〜10番手"
        return "11番手以下"
    ratio = pos / field_size
    if pos <= 3 or ratio <= 0.20: return "2〜3番手"
    if pos <= 6 or ratio <= 0.40: return "4〜6番手"
    if pos <= 10 or ratio <= 0.70: return "7〜10番手"
    return "11番手以下"


def score_prev_result(row):
    score = 0
    rank = to_int(row.get("前走着順"))
    margin = to_float(row.get("前走着差"))
    if rank == 1: score += 18
    elif rank in [2, 3]: score += 22
    elif rank in [4, 5]: score += 14
    elif rank is not None and 6 <= rank <= 9: score += 7
    if margin is not None:
        if margin <= 0: score += 5
        elif 0.1 <= margin <= 0.3: score += 8
        elif 0.4 <= margin <= 0.5: score += 5
        elif 0.6 <= margin <= 0.9: score += 2
    return min(score, 25)


def score_corner_style(row):
    score = 0
    prev_field = to_int(row.get("前走頭数"))
    c3 = to_int(row.get("前走通過順3"))
    c4 = to_int(row.get("前走通過順4"))
    style = str(row.get("前走脚質", ""))
    cat4 = get_corner_category(c4, prev_field)
    score += {"2〜3番手": 12, "4〜6番手": 14, "7〜10番手": 8, "11番手以下": 5, "1番手": 4}.get(cat4, 0)
    if "先" in style or "好位" in style: score += 4
    elif "差" in style: score += 3
    elif "追" in style: score += 1
    if c3 is not None and c4 is not None:
        if c4 < c3: score += 4
        elif abs(c4 - c3) <= 1: score += 3
    return min(score, 20)


def score_agari(row):
    score = 0
    ag = to_int(row.get("前走上り3F順"))
    cat4 = get_corner_category(row.get("前走通過順4"), row.get("前走頭数"))
    if ag == 1: score += 15
    elif ag in [2, 3]: score += 12
    elif ag in [4, 5]: score += 8
    elif ag is not None and 6 <= ag <= 9: score += 4
    if ag is not None:
        if cat4 in ["2〜3番手", "4〜6番手"] and ag <= 5: score += 3
        if cat4 in ["7〜10番手", "11番手以下"] and ag <= 3: score += 3
    return min(score, 15)


def score_condition_change(row):
    score = 0
    prev_dist = to_int(row.get("前走距離"))
    cur_dist = to_int(row.get("距離"))
    prev_surface = str(row.get("前走芝ダ", ""))
    cur_surface = str(row.get("芝ダ", ""))
    if prev_dist is not None and cur_dist is not None:
        diff = cur_dist - prev_dist
        ad = abs(diff)
        if ad == 0: score += 6
        elif diff < 0 and ad <= 200: score += 5
        elif diff > 0 and ad <= 200: score += 4
        elif diff < 0 and ad <= 400: score += 3
        elif diff > 0 and ad <= 400: score += 2
        elif diff < 0: score += 1
        if 1400 <= cur_dist <= 2000: score += 4
        elif cur_dist >= 2200: score += 3
        elif cur_dist <= 1200: score += 2
    if prev_surface and cur_surface:
        if "芝" in prev_surface and "芝" in cur_surface: score += 5
        elif "ダ" in prev_surface and "ダ" in cur_surface: score += 4
        elif ("芝" in prev_surface and "ダ" in cur_surface) or ("ダ" in prev_surface and "芝" in cur_surface): score += 1
    return min(score, 15)


def straight_type(place):
    place = str(place)
    if any(x in place for x in ["東京", "新潟"]): return "長直線"
    if any(x in place for x in ["中京", "京都", "阪神"]): return "長直線寄り"
    if any(x in place for x in ["中山", "福島", "小倉", "札幌", "函館"]): return "短直線"
    return ""


def score_straight_change(row):
    prev_type = straight_type(row.get("前走場所"))
    cur_type = straight_type(row.get("競馬場"))
    if not prev_type or not cur_type: return 0
    prev_field = to_int(row.get("前走頭数"))
    c4 = to_int(row.get("前走通過順4"))
    ag = to_int(row.get("前走上り3F順"))
    rank = to_int(row.get("前走着順"))
    cat4 = get_corner_category(c4, prev_field)
    prev_good = rank is not None and rank <= 5
    good_agari = ag is not None and ag <= 3
    front = cat4 in ["1番手", "2〜3番手", "4〜6番手"]
    back = cat4 in ["7〜10番手", "11番手以下"]
    if "長直線" in prev_type and front and prev_good and "短直線" in cur_type: return 10
    if "短直線" in prev_type and back and good_agari and "長直線" in cur_type: return 10
    if "長直線" in prev_type and back and good_agari and "長直線" in cur_type: return 8
    if "短直線" in prev_type and front and prev_good and "短直線" in cur_type: return 8
    if prev_type == cur_type and prev_good: return 6
    if "長直線" in prev_type and back and "短直線" in cur_type: return 3
    return 2


def score_field_change(row):
    prev_field = to_int(row.get("前走頭数"))
    cur_field = to_int(row.get("頭数"))
    if prev_field is None or cur_field is None: return 3
    diff = prev_field - cur_field
    if diff >= 4: return 10
    if 1 <= diff <= 3: return 6
    if diff == 0: return 3
    if -3 <= diff <= -1: return 1
    return 0


def danger_penalty(row):
    p = 0
    cur_field = to_int(row.get("頭数"))
    prev_field = to_int(row.get("前走頭数"))
    c4 = to_int(row.get("前走通過順4"))
    rank = to_int(row.get("前走着順"))
    margin = to_float(row.get("前走着差"))
    ag = to_int(row.get("前走上り3F順"))
    prev_dist = to_int(row.get("前走距離"))
    cur_dist = to_int(row.get("距離"))
    cur_surface = str(row.get("芝ダ", ""))
    prev_surface = str(row.get("前走芝ダ", ""))
    style = str(row.get("前走脚質", ""))
    if cur_field is not None and cur_field >= 16: p -= 4
    if "逃" in style: p -= 5
    if c4 == 1: p -= 5
    if rank == 1 and c4 == 1: p -= 6
    if prev_field is not None and cur_field is not None and cur_field - prev_field >= 4: p -= 6
    if cur_dist is not None and "ダ" in cur_surface and cur_dist <= 1400: p -= 4
    if prev_dist is not None and cur_dist is not None and cur_dist - prev_dist >= 500: p -= 5
    if ag is not None and ag >= 10: p -= 5
    if margin is not None:
        if margin >= 2.0: p -= 10
        elif margin >= 1.0: p -= 6
    if prev_surface and cur_surface:
        if ("芝" in prev_surface and "ダ" in cur_surface) or ("ダ" in prev_surface and "芝" in cur_surface): p -= 4
    return max(p, -20)


def calc_prev_straight_score(row):
    score = score_prev_result(row) + score_corner_style(row) + score_agari(row) + score_condition_change(row) + score_straight_change(row) + score_field_change(row) + danger_penalty(row)
    return round(max(0, min(100, score)))


def trust_count(row):
    cnt = 0
    rank = to_int(row.get("前走着順"))
    margin = to_float(row.get("前走着差"))
    cat4 = get_corner_category(row.get("前走通過順4"), row.get("前走頭数"))
    style = str(row.get("前走脚質", ""))
    prev_dist = to_int(row.get("前走距離"))
    cur_dist = to_int(row.get("距離"))
    cur_surface = str(row.get("芝ダ", ""))
    if rank in [2, 3]: cnt += 1
    if margin is not None and 0.1 <= margin <= 0.3: cnt += 1
    if cat4 in ["2〜3番手", "4〜6番手"]: cnt += 1
    if "先" in style or "好位" in style: cnt += 1
    if prev_dist is not None and cur_dist is not None and prev_dist == cur_dist: cnt += 1
    if "芝" in cur_surface: cnt += 1
    if cur_dist is not None and cur_dist >= 1600: cnt += 1
    return cnt


def trust_score(cnt):
    return {0: 40, 1: 50, 2: 60, 3: 70, 4: 80, 5: 90, 6: 96, 7: 100}.get(cnt, 40)


def field_score(row):
    prev_field = to_int(row.get("前走頭数"))
    cur_field = to_int(row.get("頭数"))
    if prev_field is None or cur_field is None: return 70
    diff = prev_field - cur_field
    if diff >= 4: return 100
    if 1 <= diff <= 3: return 85
    if diff == 0: return 70
    if -3 <= diff <= -1: return 55
    return 35


def danger_count(row):
    return max(0, abs(danger_penalty(row)) // 4)


def danger_adj(cnt):
    if cnt <= 0: return 0
    if cnt == 1: return 3
    if cnt == 2: return 6
    if cnt == 3: return 10
    return 15


def calc_composite_score(row):
    ps = calc_prev_straight_score(row)
    tc = trust_count(row)
    fs = field_score(row)
    dc = danger_count(row)
    score = ps * 0.70 + trust_score(tc) * 0.20 + fs * 0.10 - danger_adj(dc)
    return round(max(0, min(100, score)))


def classify(score, tc, dc):
    if score >= 95 and tc >= 5 and dc <= 2: return "軸候補"
    if score >= 90 and tc >= 4: return "相手筆頭"
    if score >= 85: return "単穴"
    if score >= 80: return "連下"
    if score >= 75 and tc >= 3: return "強穴"
    if score >= 70: return "押さえ"
    return "軽視"


def build_straight_results(target_df, min_score=90):
    df = normalize_target(target_df)
    df = df[df["R"].isin([7, 8, 9, 10, 11, 12])].copy()
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    df["前走直線ロジック点"] = df.apply(calc_prev_straight_score, axis=1)
    df["信頼条件一致数"] = df.apply(trust_count, axis=1)
    df["危険条件数"] = df.apply(danger_count, axis=1)
    df["複合スコア"] = df.apply(calc_composite_score, axis=1)
    df["信頼度"] = df["複合スコア"]
    df["分類"] = df.apply(lambda r: classify(r["複合スコア"], r["信頼条件一致数"], r["危険条件数"]), axis=1)
    df["R_num"] = df["R"].map(to_int)
    df["馬番_num"] = df["馬番"].map(to_int)
    df = df.sort_values(["競馬場", "R_num", "複合スコア", "馬番_num"], ascending=[True, True, False, True]).copy()
    df["印"] = ""
    for _, g in df.groupby(["競馬場", "R_num"], sort=False):
        cand = g[g["信頼度"] >= min_score].head(6)
        marks = ["◎", "○", "▲", "△", "△", "△"]
        for idx, mark in zip(cand.index, marks): df.loc[idx, "印"] = mark
    detail_cols = ["日付", "競馬場", "芝ダ", "距離", "R", "レース名", "頭数", "馬番", "馬名", "前走直線ロジック点", "信頼条件一致数", "危険条件数", "複合スコア", "信頼度", "分類", "印"]
    for c in detail_cols:
        if c not in df.columns: df[c] = ""
    detail = df[detail_cols].copy()
    rows = []
    for _, g in df.groupby(["日付", "競馬場", "R_num"], sort=False):
        main_df = g[g["印"] == "◎"]
        if main_df.empty: continue
        main = main_df.iloc[0]
        opp = g[g["印"] == "○"]
        ana = g[g["印"] == "▲"]
        ren = g[g["印"] == "△"]
        taikou = str(int(opp.iloc[0]["馬番"])) if not opp.empty and pd.notna(opp.iloc[0]["馬番"]) else ""
        tanketsu = str(int(ana.iloc[0]["馬番"])) if not ana.empty and pd.notna(ana.iloc[0]["馬番"]) else ""
        ren_nums = [str(int(x)) for x in ren["馬番"].tolist() if pd.notna(x)]
        parts = []
        if taikou: parts.append(f"○{taikou}")
        if tanketsu: parts.append(f"▲{tanketsu}")
        if ren_nums: parts.append("△" + "・".join(ren_nums))
        rows.append({
            "日付": main["日付"], "競馬場": main["競馬場"], "R": int(main["R"]), "レース名": main["レース名"],
            "馬番": int(main["馬番"]) if pd.notna(main["馬番"]) else "", "馬名": main["馬名"], "信頼度": int(main["信頼度"]), "印": "◎",
            "対抗": taikou, "対抗馬名": opp.iloc[0]["馬名"] if not opp.empty else "",
            "単穴": tanketsu, "単穴馬名": ana.iloc[0]["馬名"] if not ana.empty else "",
            "連下": ren_nums[0] if len(ren_nums) > 0 else "", "連下馬名": ren.iloc[0]["馬名"] if len(ren_nums) > 0 else "",
            "他1": ren_nums[1] if len(ren_nums) > 1 else "", "他2": ren_nums[2] if len(ren_nums) > 2 else "", "相手表示": " / ".join(parts),
        })
    return detail, pd.DataFrame(rows)


# =========================================================
# 鉄板ロジック
# =========================================================
def csv_files():
    return sorted(Path(".").glob("*.csv"), key=lambda p: p.name)


def detect_teppan_files():
    logic_path, course_path = None, None
    for f in csv_files():
        try:
            df = read_csv_smart(f); df.columns = [norm_col(c) for c in df.columns]; cols = set(df.columns)
            is_logic = {"競馬場", "距離", "芝ダ"}.issubset(cols) and ("最終対象系統" in cols or "対象系統" in cols or "条件1項目" in cols)
            is_course = {"競馬場", "距離", "芝ダ"}.issubset(cols) and "判定" in cols and ("リフト" in cols or "複勝率%" in cols or "該当頭数" in cols)
            if is_logic: logic_path = f
            if is_course: course_path = f
        except Exception:
            pass
    return logic_path, course_path


def target_systems_list(rule):
    raw = ""
    for c in ["最終対象系統", "対象系統", "残留系統"]:
        if c in rule.index and norm_text(rule.get(c, "")):
            raw = str(rule.get(c, "")); break
    return [norm_text(p) for p in re.split(r"[、,/／・\s]+", raw) if norm_text(p)] if raw else []


def match_value(row, item, expected):
    item, expected = norm_text(item), norm_text(expected)
    if not item or not expected: return True
    imap = {"芝・ダ": "芝ダ", "前芝ダ": "前走芝ダ", "前芝・ダ": "前走芝ダ", "前距離": "前走距離", "場所": "競馬場"}
    lookup = imap.get(item, item)
    if lookup not in row.index:
        return True if lookup in ["天気", "馬場状態", "前走調教師", "前走所属"] else False
    actual = norm_text(row.get(lookup, ""))
    if actual == "":
        return True if lookup in ["天気", "馬場状態", "前走調教師", "前走所属"] else False
    return actual == expected


def condition_pairs(rule, max_n=12):
    pairs = []
    for i in range(1, max_n + 1):
        item, content = norm_text(rule.get(f"条件{i}項目", "")), norm_text(rule.get(f"条件{i}内容", ""))
        if item and content: pairs.append((item, content))
    return pairs


def teppan_rank(row):
    prev_rank = to_int(row.get("前走着順"))
    margin = to_float(row.get("前走着差"))
    rank_ok = prev_rank is not None and prev_rank <= 5
    margin_ok = margin is not None and margin <= 0.5
    if rank_ok and margin_ok: return "超鉄板⭐️"
    if rank_ok or margin_ok: return "強鉄板⭐️"
    return "鉄板⭐️"


def build_teppan_results(target_df, logic_df, course_df, use_statuses):
    inp = normalize_target(target_df); inp = inp[inp["R"].isin([7,8,9,10,11,12])].copy()
    logic, course = logic_df.copy(), course_df.copy()
    logic.columns = [norm_col(c) for c in logic.columns]; course.columns = [norm_col(c) for c in course.columns]
    for df in [inp, logic, course]:
        for c in ["競馬場", "芝ダ"]:
            if c in df.columns: df[c] = df[c].map(norm_text)
        if "距離" in df.columns: df["距離"] = df["距離"].map(to_int)
    course_use = course[course["判定"].map(norm_text).isin([norm_text(x) for x in use_statuses])].copy() if "判定" in course.columns else course.copy()
    results = []
    for _, h in inp.iterrows():
        key = (norm_text(h["競馬場"]), norm_text(h["芝ダ"]), to_int(h["距離"]))
        cm = course_use[(course_use["競馬場"].map(norm_text)==key[0]) & (course_use["芝ダ"].map(norm_text)==key[1]) & (course_use["距離"].map(to_int)==key[2])]
        if cm.empty: continue
        lm = logic[(logic["競馬場"].map(norm_text)==key[0]) & (logic["芝ダ"].map(norm_text)==key[1]) & (logic["距離"].map(to_int)==key[2])]
        if lm.empty: continue
        father_sys, mb_sys = norm_text(h.get("父タイプ名","")), norm_text(h.get("母父タイプ名",""))
        for _, rule in lm.iterrows():
            blood_type = norm_text(rule.get("血統区分","")); systems = target_systems_list(rule)
            hit = (father_sys in systems) if blood_type == "父系" else (mb_sys in systems) if blood_type == "母父系" else (father_sys in systems or mb_sys in systems)
            if not hit: continue
            if all(match_value(h, item, content) for item, content in condition_pairs(rule)):
                results.append({"日付": h["日付"], "競馬場": h["競馬場"], "R": int(h["R"]), "レース名": h["レース名"], "馬番": int(h["馬番"]) if pd.notna(h["馬番"]) else "", "馬名": h["馬名"], "鉄板ランク": teppan_rank(h), "判定": cm.iloc[0].get("判定","採用")})
    out = pd.DataFrame(results)
    if out.empty: return out
    out["R_num"] = out["R"].map(to_int); out["rank_pri"] = out["鉄板ランク"].map(lambda x: 1 if x=="超鉄板⭐️" else 2 if x=="強鉄板⭐️" else 3); out["馬番_num"] = out["馬番"].map(to_int)
    out = out.sort_values(["競馬場","R_num","rank_pri","馬番_num"]).drop_duplicates(subset=["日付","競馬場","R","馬番","馬名"], keep="first").copy()
    marks = ["◎","○","▲","△","☆","注"]; out["印"] = ""
    for _, idxs in out.groupby(["日付","競馬場","R"]).groups.items():
        for i, idx in enumerate(list(idxs)): out.loc[idx, "印"] = marks[i] if i < len(marks) else "他"
    return out[["日付","競馬場","R","レース名","馬番","馬名","鉄板ランク","判定","印"]].copy()



# =========================================================
# 消寄ロジック
# =========================================================
def detect_keshiyose_file():
    candidates = []
    for f in csv_files():
        if "消寄" in f.name and f.suffix.lower() == ".csv":
            candidates.append(f)
    # 実用版を優先
    for f in candidates:
        if "コース別上位20" in f.name:
            return f
    return candidates[0] if candidates else None


def build_feature_map(row):
    cur_surface = norm_text(row.get("芝ダ", ""))
    prev_surface = norm_text(row.get("前走芝ダ", ""))
    cur_dist = to_int(row.get("距離"))
    prev_dist = to_int(row.get("前走距離"))
    cur_field = to_int(row.get("頭数"))
    prev_field = to_int(row.get("前走頭数"))
    margin = to_float(row.get("前走着差"))
    rank = to_int(row.get("前走着順"))
    ag = to_int(row.get("前走上り3F順"))
    c4cat = get_corner_category(row.get("前走通過順4"), row.get("前走頭数"))
    style = norm_text(row.get("前走脚質", ""))
    rest = norm_text(row.get("休み明け〜戦目", ""))

    surface_change = ""
    if prev_surface and cur_surface:
        surface_change = f"{prev_surface}→{cur_surface}" if prev_surface != cur_surface else "同芝ダ"

    dist_band = ""
    if cur_dist is not None and prev_dist is not None:
        diff = cur_dist - prev_dist
        ad = abs(diff)
        if diff == 0:
            dist_band = "同距離"
        elif diff < 0 and ad <= 200:
            dist_band = "短縮100-200m"
        elif diff > 0 and ad <= 200:
            dist_band = "延長100-200m"
        elif diff < 0 and ad <= 400:
            dist_band = "短縮300-400m"
        elif diff > 0 and ad <= 400:
            dist_band = "延長300-400m"
        elif diff < 0:
            dist_band = "短縮500m以上"
        else:
            dist_band = "延長500m以上"

    if margin is None:
        margin_band = ""
    elif margin >= 2.0:
        margin_band = "2.0秒以上負け"
    elif margin >= 1.0:
        margin_band = "1.0秒以上負け"
    elif margin >= 0.6:
        margin_band = "0.6-0.9秒負け"
    elif margin >= 0.4:
        margin_band = "0.4-0.5秒負け"
    elif margin >= 0.1:
        margin_band = "0.1-0.3秒負け"
    else:
        margin_band = "勝ち/同タイム"

    if rank is None:
        rank_band = ""
    elif rank == 1:
        rank_band = "1着"
    elif rank <= 3:
        rank_band = "2-3着"
    elif rank <= 5:
        rank_band = "4-5着"
    elif rank <= 9:
        rank_band = "6-9着"
    else:
        rank_band = "10着以下"

    if ag is None:
        ag_band = ""
    elif ag == 1:
        ag_band = "1位"
    elif ag <= 3:
        ag_band = "2-3位"
    elif ag <= 5:
        ag_band = "4-5位"
    elif ag <= 9:
        ag_band = "6-9位"
    else:
        ag_band = "10位以下"

    if cur_field is None:
        cur_field_band = ""
    elif cur_field >= 16:
        cur_field_band = "16頭以上"
    elif cur_field >= 14:
        cur_field_band = "14-15頭"
    elif cur_field >= 10:
        cur_field_band = "10-13頭"
    else:
        cur_field_band = "9頭以下"

    if prev_field is None or cur_field is None:
        field_change = ""
    else:
        diff = prev_field - cur_field
        if diff >= 4:
            field_change = "今回かなり頭数減"
        elif diff >= 1:
            field_change = "今回頭数減"
        elif diff == 0:
            field_change = "同頭数"
        elif diff >= -3:
            field_change = "今回頭数増"
        else:
            field_change = "今回かなり頭数増"

    if "逃" in style:
        style_band = "逃げ"
    elif "先" in style or "好位" in style:
        style_band = "先行/好位"
    elif "差" in style:
        style_band = "差し"
    elif "追" in style:
        style_band = "追込"
    else:
        style_band = ""

    return {
        "芝ダ替わり": surface_change,
        "距離変化帯": dist_band,
        "前走着差帯": margin_band,
        "前走着順帯": rank_band,
        "前走上り順帯": ag_band,
        "前走4角位置": c4cat,
        "前走脚質帯": style_band,
        "頭数変化": field_change,
        "今回頭数帯": cur_field_band,
        "休み明け区分": rest,
    }


def build_keshiyose_results(target_df, keshi_df):
    inp = normalize_target(target_df)
    inp = inp[inp["R"].isin([7, 8, 9, 10, 11, 12])].copy()
    if inp.empty or keshi_df is None or keshi_df.empty:
        return pd.DataFrame()

    kd = keshi_df.copy()
    kd.columns = [norm_col(c) for c in kd.columns]
    for c in ["競馬場", "芝ダ", "消寄項目1", "消寄条件1", "消寄項目2", "消寄条件2", "消寄項目3", "消寄条件3", "消寄ランク", "消寄理由"]:
        if c not in kd.columns:
            kd[c] = ""
        kd[c] = kd[c].map(norm_text)
    kd["距離"] = kd["距離"].map(to_int)

    rows = []
    for _, h in inp.iterrows():
        rules = kd[
            (kd["競馬場"] == norm_text(h["競馬場"]))
            & (kd["芝ダ"] == norm_text(h["芝ダ"]))
            & (kd["距離"] == to_int(h["距離"]))
        ]
        if rules.empty:
            continue

        fmap = build_feature_map(h)
        hit_reasons = []
        hit_ranks = []
        for _, r in rules.iterrows():
            ok = True
            for i in [1, 2, 3]:
                item = norm_text(r.get(f"消寄項目{i}", ""))
                cond = norm_text(r.get(f"消寄条件{i}", ""))
                if not item or not cond:
                    continue
                if fmap.get(item, "") != cond:
                    ok = False
                    break
            if ok:
                hit_reasons.append(norm_text(r.get("消寄理由", "")) or f"{r.get('消寄項目1')}={r.get('消寄条件1')}")
                hit_ranks.append(norm_text(r.get("消寄ランク", "")))

        if hit_reasons:
            a_count = sum(1 for r in hit_ranks if r == "消寄A")
            label = "強消寄" if len(hit_reasons) >= 2 or a_count >= 1 else "消寄"
            rows.append({
                "日付": h["日付"],
                "競馬場": h["競馬場"],
                "R": int(h["R"]),
                "レース名": h["レース名"],
                "馬番": int(h["馬番"]) if pd.notna(h["馬番"]) else "",
                "馬名": h["馬名"],
                "消寄判定": label,
                "消寄該当数": len(hit_reasons),
                "消寄理由": " / ".join(hit_reasons[:3]),
            })
    return pd.DataFrame(rows)


# =========================================================
# HTML/CSS表示
# =========================================================
def flag_from_rank(rank):
    rank = norm_text(rank)
    if rank == "超鉄板⭐️": return "激", "flag-geki"
    if rank in ["強鉄板⭐️", "鉄板⭐️"]: return "熱", "flag-netsu"
    return "", ""


def strongest_rank(ranks):
    ranks = [r for r in ranks if norm_text(r)]
    if not ranks: return ""
    return sorted(ranks, key=lambda r: 3 if r=="超鉄板⭐️" else 2 if r=="強鉄板⭐️" else 1, reverse=True)[0]


def find_html_teppan_rank(t_race, num):
    if t_race.empty: return ""
    x = t_race[t_race["馬番"].map(norm_text) == norm_text(num)]
    return strongest_rank(x["鉄板ランク"].tolist()) if not x.empty else ""


def normalize_html_straight(df):
    df = df.copy()
    if df.empty: return df
    df.columns = [norm_col(c) for c in df.columns]
    rename = {"○":"対抗","◯":"対抗","▲":"単穴","△":"連下"}
    for old, new in rename.items():
        if old in df.columns and new not in df.columns: df = df.rename(columns={old:new})
    for c in ["日付","競馬場","R","レース名","馬番","馬名","対抗","対抗馬名","単穴","単穴馬名","連下","連下馬名","他1","他2","他"]:
        if c in df.columns: df[c] = df[c].map(norm_text)
    if "日付" in df.columns: df["日付"] = df["日付"].map(parse_date)
    return df


def normalize_html_teppan(df):
    df = df.copy()
    if df.empty: return df
    df.columns = [norm_col(c) for c in df.columns]
    for c in ["日付","競馬場","R","レース名","馬番","馬名","鉄板ランク","印"]:
        if c in df.columns: df[c] = df[c].map(norm_text)
    if "日付" in df.columns: df["日付"] = df["日付"].map(parse_date)
    return df


def find_keshi(k_race, num):
    if k_race is None or k_race.empty:
        return ""
    x = k_race[k_race["馬番"].map(norm_text) == norm_text(num)]
    if x.empty:
        return ""
    return "消寄"


def build_cards(straight_csv, teppan_csv, keshi_csv=None):
    s = normalize_html_straight(straight_csv)
    t = normalize_html_teppan(teppan_csv)
    k = keshi_csv.copy() if keshi_csv is not None and not keshi_csv.empty else pd.DataFrame()

    for df in [s, t, k]:
        if df is not None and not df.empty:
            df.columns = [norm_col(c) for c in df.columns]
            if "R" in df.columns:
                df["R_num"] = df["R"].map(to_int)
            for c in ["日付", "競馬場", "馬番", "馬名", "レース名"]:
                if c in df.columns:
                    df[c] = df[c].map(norm_text)

    venues = []
    for df in [s, t, k]:
        if df is None or df.empty or "競馬場" not in df.columns:
            continue
        for v in df["競馬場"].tolist():
            if v not in venues:
                venues.append(v)
    venue_order = {v: i for i, v in enumerate(venues)}

    keys = set()
    for df in [s, t, k]:
        if df is None or df.empty:
            continue
        for _, r in df.iterrows():
            keys.add((r.get("日付", ""), r.get("競馬場", ""), int(r.get("R_num", 999))))
    keys = sorted(keys, key=lambda x: (venue_order.get(x[1], 999), x[2]))

    cards = []
    for date, place, rnum in keys:
        sr = s[(s["日付"] == date) & (s["競馬場"] == place) & (s["R_num"] == rnum)].copy() if not s.empty else pd.DataFrame()
        tr = t[(t["日付"] == date) & (t["競馬場"] == place) & (t["R_num"] == rnum)].copy() if not t.empty else pd.DataFrame()
        kr = k[(k["日付"] == date) & (k["競馬場"] == place) & (k["R_num"] == rnum)].copy() if not k.empty else pd.DataFrame()

        lines, race_name = [], ""
        if not sr.empty:
            main = sr.iloc[0]
            race_name = main.get("レース名", "")
            rank = find_html_teppan_rank(tr, main.get("馬番", ""))
            fl, cls = flag_from_rank(rank)
            keshi = find_keshi(kr, main.get("馬番", ""))
            lines.append({"mark": "◎", "num": main.get("馬番", ""), "name": main.get("馬名", ""), "flag": fl, "flag_class": cls, "keshi": keshi})

            for mark, num_col, name_col in [("○", "対抗", "対抗馬名"), ("▲", "単穴", "単穴馬名"), ("△", "連下", "連下馬名")]:
                num = norm_text(main.get(num_col, ""))
                if num:
                    rank = find_html_teppan_rank(tr, num)
                    fl, cls = flag_from_rank(rank)
                    keshi = find_keshi(kr, num)
                    lines.append({"mark": mark, "num": num, "name": main.get(name_col, ""), "flag": fl, "flag_class": cls, "keshi": keshi})

            others = []
            for c in ["他", "他1", "他2", "他3"]:
                v = norm_text(main.get(c, ""))
                if v:
                    others.append(v)
            if others:
                lines.append({"mark": "他", "num": "", "name": ", ".join(others), "flag": "", "flag_class": "", "keshi": ""})
        else:
            if not tr.empty:
                race_name = tr.iloc[0].get("レース名", "")
            for _, row in tr.iterrows():
                fl, cls = flag_from_rank(row.get("鉄板ランク", ""))
                keshi = find_keshi(kr, row.get("馬番", ""))
                lines.append({"mark": "", "num": row.get("馬番", ""), "name": row.get("馬名", ""), "flag": fl, "flag_class": cls, "keshi": keshi})

        cards.append({"date": date, "venue": place, "race_no": f"{rnum}R", "race_name": race_name, "lines": lines})
    return cards


def render_line(line):
    return f'''<div class="pick-line"><span class="mark">{html_escape(line.get("mark",""))}</span><span class="num">{html_escape(line.get("num",""))}</span><span class="horse-name">{html_escape(line.get("name",""))}</span><span class="flag {html_escape(line.get("flag_class",""))}">{html_escape(line.get("flag",""))}</span><span class="keshi">{html_escape(line.get("keshi",""))}</span></div>'''


def render_card(card, idx):
    venue, race_no, race_name = html_escape(card["venue"]), html_escape(card["race_no"]), html_escape(card.get("race_name",""))
    serial = f"{venue[:1]}{re.sub(r'[^0-9]','',race_no).zfill(2)}-000000-{idx:03d}"
    return f'''<div class="ticket-card"><div class="ticket-head"><div class="race-title">{venue} {race_no}</div><div class="race-name">{race_name}</div></div><div class="ticket-body">{"".join(render_line(x) for x in card["lines"])}</div><div class="ticket-footer"><div class="footer-label">TODAY’S PICKS</div><div class="footer-divider"></div><div class="barcode"></div><div class="serial">{serial}</div></div></div>'''


def render_html(cards, image_date):
    date = parse_date(image_date) if image_date else (cards[0]["date"] if cards else "")
    cards_html = "".join(render_card(card, i+1) for i, card in enumerate(cards))
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><style>
:root{{--bg:#031226;--gold:#e5bc4b;--gold2:#b9871e;--paper:#f6f0dd;--ink:#111;--navy:#0b2c59;--red:#d8212d;--yellow:#c88d00;--line:#d5c7a0;}}
*{{box-sizing:border-box;}}body{{margin:0;background:var(--bg);font-family:"Noto Sans CJK JP","Noto Sans JP","Hiragino Sans","Yu Gothic",sans-serif;}}
.poster{{width:1080px;margin:0 auto;padding:34px;background:linear-gradient(180deg,#031226,#020f20);border:4px solid var(--gold2);outline:1px solid var(--gold2);outline-offset:-14px;}}
.header{{height:170px;position:relative;}}.title{{position:absolute;left:36px;top:5px;font-size:78px;line-height:1;color:var(--gold);font-weight:900;letter-spacing:.04em;}}
.subtitle{{position:absolute;left:235px;top:103px;color:var(--gold);font-weight:900;font-size:32px;letter-spacing:.12em;}}
.subtitle:before,.subtitle:after{{content:"";display:inline-block;width:150px;height:2px;background:var(--gold);vertical-align:middle;margin:0 16px;}}
.date{{position:absolute;right:32px;top:8px;color:var(--gold);font-size:34px;letter-spacing:.08em;}}.legend{{position:absolute;right:22px;top:68px;color:#fff;font-size:22px;font-weight:800;line-height:1.45;}}.red{{color:var(--red);}}.yellow{{color:var(--yellow);}}
.cards{{display:grid;grid-template-columns:1fr 1fr;gap:18px 22px;}}.ticket-card{{background:var(--paper);border:2px solid var(--gold2);border-radius:16px;overflow:hidden;min-height:235px;box-shadow:0 0 0 2px rgba(255,255,255,.15) inset;}}
.ticket-head{{margin:8px 8px 0;height:68px;background:var(--navy);border:2px solid var(--gold2);border-radius:12px 12px 4px 4px;color:white;text-align:center;padding-top:10px;}}
.race-title{{font-size:34px;font-weight:900;line-height:1;letter-spacing:.06em;}}.race-name{{margin-top:6px;font-size:14px;color:#f4efe0;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.ticket-body{{padding:14px 20px 6px;}}.pick-line{{display:grid;grid-template-columns:34px 52px 1fr 34px 48px;align-items:center;height:39px;border-bottom:1px solid var(--line);font-weight:800;color:var(--ink);font-size:22px;letter-spacing:.02em;}}
.pick-line:last-child{{border-bottom:none;}}.mark{{font-size:24px;}}.num{{font-size:23px;}}.horse-name{{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}}.flag{{font-weight:900;text-align:right;font-size:24px;}}.flag-geki{{color:var(--red);}}.flag-netsu{{color:var(--yellow);}}
.ticket-footer{{height:44px;display:grid;grid-template-columns:130px 14px 1fr;align-items:center;padding:0 18px;color:var(--ink);position:relative;}}.footer-label{{font-size:15px;font-weight:900;}}.footer-divider{{height:24px;width:1px;background:var(--gold2);}}.barcode{{width:150px;height:22px;margin-left:20px;background:repeating-linear-gradient(90deg,#111 0,#111 3px,transparent 3px,transparent 6px,#111 6px,#111 8px,transparent 8px,transparent 13px);}}.serial{{position:absolute;left:210px;bottom:2px;font-size:13px;letter-spacing:.04em;}}
</style></head><body><div class="poster"><div class="header"><div class="title">本日の推奨馬</div><div class="subtitle">TODAY’S PICKS</div><div class="date">{html_escape(date)}</div><div class="legend"><div><span class="red">激</span>=超鉄板　<span class="yellow">熱</span>=鉄板</div><div>印=直線ロジック　消寄=消し警告</div></div></div><div class="cards">{cards_html}</div></div></body></html>'''


st.title("統合 直線ロジック×鉄板⭐️×消寄アプリ")
st.caption("TARGET/JRA-VAN由来CSVを1つ読み込み、直線採点・鉄板判定・消寄判定・馬券風HTML画像を作成します。")

with st.expander("必要な配置ファイル", expanded=False):
    st.write("鉄板判定を使う場合は、app.pyと同じ場所に以下の2CSVを置いてください。")
    st.code("鉄板血統_TOP5並列_修正版_最終ロジック辞書.csv\n鉄板血統_コース別_採用保留除外判定.csv\n消寄_コース別上位20.csv")

with st.expander("TARGETから抜く推奨項目", expanded=True):
    st.text("日付 / 場所 / 場R / レース名(クラス) / 芝ダ・距離 / 馬番 / 馬名 / 種牡馬 / 父タイプ名 / 母父名 / 母父タイプ名 / 性齢 / 斤量 / 頭数 / 前馬場状態 / 前距離 / 前走斤量 / 休み明け〜戦目 / 調教師 / 騎手 / 前走騎手 / 前走着順 / 前走着差 / 前走頭数 / 前走通過順3 / 前走通過順4 / 前走上り3F順 / 前走上り3F / 前走脚質 / 前走場所")

mode = st.radio("TARGET CSV入力方法", ["ファイル読み込み", "貼り付け"], horizontal=True)

if mode == "ファイル読み込み":
    uploaded = st.file_uploader("TARGET/JRA-VAN由来CSV", type=["csv"])
    pasted = ""
else:
    uploaded = None
    pasted = st.text_area("TARGET/JRA-VAN由来CSVを貼り付け", height=300)

col1, col2 = st.columns(2)
with col1:
    image_date = st.text_input("画像に表示する日付", value=datetime.now().strftime("%Y.%m.%d"))
with col2:
    use_status = st.multiselect("使用する鉄板コース判定", ["採用", "保留", "除外"], default=["採用"])

min_score = st.selectbox(
    "直線ロジックの最低表示基準",
    [75, 80, 85, 90],
    index=0,
    help="まずは75以上で表示確認し、実戦では80/85/90へ上げて調整できます。"
)

if st.button("統合処理を実行", type="primary", use_container_width=True):
    try:
        if mode == "ファイル読み込み":
            if uploaded is None:
                st.warning("CSVファイルを選択してください。")
                st.stop()
            target_df = read_csv_smart(uploaded)
        else:
            if not pasted.strip():
                st.warning("CSV本文を貼り付けてください。")
                st.stop()
            target_df = read_csv_smart(io.StringIO(pasted))

        straight_detail, straight_composite = build_straight_results(target_df, min_score)

        logic_path, course_path = detect_teppan_files()
        if logic_path and course_path:
            logic_df = read_csv_smart(logic_path)
            course_df = read_csv_smart(course_path)
            teppan_result = build_teppan_results(target_df, logic_df, course_df, use_status)
        else:
            teppan_result = pd.DataFrame()
            st.warning("鉄板ロジックCSVまたはコース判定CSVが見つからないため、鉄板判定なしで処理しました。")

        keshi_path = detect_keshiyose_file()
        if keshi_path:
            keshi_df = read_csv_smart(keshi_path)
            keshi_result = build_keshiyose_results(target_df, keshi_df)
        else:
            keshi_result = pd.DataFrame()
            st.warning("消寄辞書CSVが見つからないため、消寄判定なしで処理しました。")

        if straight_composite.empty and teppan_result.empty:
            st.warning("直線・鉄板ともに該当馬がありませんでした。")
            st.stop()

        cards = build_cards(straight_composite, teppan_result, keshi_result)
        html = render_html(cards, image_date)

        st.success(f"直線基準{min_score}以上 / 直線詳細 {len(straight_detail)}頭 / 直線推奨 {len(straight_composite)}レース / 鉄板 {len(teppan_result)}頭 / 消寄 {len(keshi_result)}頭 / 表示 {len(cards)}レース")

        st.subheader("① 直線アプリ用・詳細ランキングCSV")
        st.dataframe(straight_detail, use_container_width=True, hide_index=True)
        st.download_button("直線詳細CSVをダウンロード", straight_detail.to_csv(index=False, encoding="utf-8-sig"), file_name="straight_logic_detail.csv", mime="text/csv", use_container_width=True)

        st.subheader("② 直線 複合アプリ用CSV")
        st.dataframe(straight_composite, use_container_width=True, hide_index=True)
        st.download_button("直線複合CSVをダウンロード", straight_composite.to_csv(index=False, encoding="utf-8-sig"), file_name="straight_for_composite.csv", mime="text/csv", use_container_width=True)

        st.subheader("③ 鉄板 複合アプリ用CSV")
        st.dataframe(teppan_result, use_container_width=True, hide_index=True)
        st.download_button("鉄板複合CSVをダウンロード", teppan_result.to_csv(index=False, encoding="utf-8-sig") if not teppan_result.empty else "", file_name="teppan_for_composite.csv", mime="text/csv", use_container_width=True)

        st.subheader("④ 消寄 判定CSV")
        st.dataframe(keshi_result, use_container_width=True, hide_index=True)
        st.download_button("消寄CSVをダウンロード", keshi_result.to_csv(index=False, encoding="utf-8-sig") if not keshi_result.empty else "", file_name="keshiyose_result.csv", mime="text/csv", use_container_width=True)

        st.subheader("⑤ SNS画像プレビュー")
        components.html(html, height=1200, scrolling=True)
        st.download_button("HTMLをダウンロード", data=html.encode("utf-8"), file_name="integrated_composite_ticket.html", mime="text/html", use_container_width=True)
        st.info("PNG保存は、HTMLプレビューをスクショする運用が最も安定します。")

    except Exception as e:
        st.error("処理中にエラーが出ました。")
        st.exception(e)

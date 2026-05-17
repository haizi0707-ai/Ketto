import io
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="重賞⭐️極端条件アプリ", layout="wide")

APP_TITLE = "重賞⭐️極端条件アプリ"
CONDITION_FILE = "jusho_extreme_conditions_age_sex_axis.csv"

REQUIRED_COLUMNS_CORE = [
    "レース名", "馬名", "性別", "年齢", "斤量", "馬齢斤量差", "頭数", "枠番", "馬番", "所属",
    "馬場状態", "距離", "種牡馬", "父タイプ名", "母父馬", "母父タイプ名",
    "間隔", "前走場所", "前走レース名", "前クラス名", "替", "前走斤量", "前走頭数", "前走着順",
    "前芝・ダ", "前距離", "前走馬場状態", "前走着差タイム", "前3角", "前4角",
    "前走脚質", "前走決め手", "前走上り3F順", "前走所属",
]


TARGET_HEADERLESS_COLUMNS = [
    "レース名", "性別", "年齢", "斤量", "馬齢斤量差", "頭数", "枠番", "馬番", "所属",
    "芝ダ", "距離", "距離2", "種牡馬", "父タイプ名", "母父馬", "母父タイプ名",
    "間隔", "前走場所", "同場別場", "未使用19", "前クラス名", "替",
    "前走斤量", "前走頭数", "前走着順", "前芝・ダ", "未使用26", "未使用27",
    "前距離", "前走馬場状態", "前走着差タイム", "前1角", "前2角", "前3角", "前4角",
    "前走決め手", "前走脚質", "前走上り3F順", "馬名",
]

CONDITION_COLUMNS = ["重賞名", "基準軸", "基準値", "条件1", "条件2", "条件内容", "該当数", "複勝数", "複勝率", "条件タイプ", "採用ランク"]

COLUMN_ALIASES = {
    "レース名": ["レース名", "重賞名", "対象レース"],
    "馬名": ["馬名", "馬名S"],
    "性別": ["性別", "性"],
    "年齢": ["年齢", "齢"],
    "斤量": ["斤量"],
    "馬齢斤量差": ["馬齢斤量差"],
    "頭数": ["頭数", "出走頭数"],
    "枠番": ["枠番"],
    "馬番": ["馬番"],
    "所属": ["所属"],
    "馬場状態": ["馬場状態", "今回馬場", "馬場"],
    "距離": ["距離"],
    "種牡馬": ["種牡馬", "父名"],
    "父タイプ名": ["父タイプ名", "父系統", "種牡馬系統"],
    "母父馬": ["母父馬", "母父名"],
    "母父タイプ名": ["母父タイプ名", "母父系統"],
    "間隔": ["間隔"],
    "前走場所": ["前走場所", "前場所"],
    "前走レース名": ["前走レース名", "前レース名"],
    "前クラス名": ["前クラス名", "前走クラス", "前走クラス名"],
    "替": ["替", "騎手替"],
    "前走斤量": ["前走斤量", "前斤量"],
    "前走頭数": ["前走頭数", "前走出走頭数"],
    "前走着順": ["前走着順", "前走確定着順", "前着順"],
    "前芝・ダ": ["前芝・ダ", "前走芝ダ", "前走芝・ダ"],
    "前距離": ["前距離", "前走距離", "前走距離数値"],
    "前走馬場状態": ["前走馬場状態", "前走馬場"],
    "前走着差タイム": ["前走着差タイム", "前走着差", "前着差"],
    "前3角": ["前3角", "前3角通過順"],
    "前4角": ["前4角", "前4角通過順"],
    "前走脚質": ["前走脚質", "前脚質"],
    "前走決め手": ["前走決め手", "前決め手"],
    "前走上り3F順": ["前走上り3F順", "前走上がり順位", "前上り3F順", "前走上り順位"],
    "前走所属": ["前走所属", "前所属"],
}


def normalize_text(x):
    if pd.isna(x):
        return ""
    s = unicodedata.normalize("NFKC", str(x)).strip()
    s = re.sub(r"\s+", "", s)
    return s


def _recognized_column_count(df):
    keys = set()
    for std, aliases in COLUMN_ALIASES.items():
        for a in aliases + [std]:
            keys.add(normalize_text(a))
    return sum(1 for c in df.columns if normalize_text(c) in keys)


def _condition_column_count(df):
    keys = {normalize_text(c) for c in CONDITION_COLUMNS}
    return sum(1 for c in df.columns if normalize_text(c) in keys)


def _assign_headerless_columns(df):
    df = df.copy()
    if df.shape[1] == len(TARGET_HEADERLESS_COLUMNS):
        df.columns = TARGET_HEADERLESS_COLUMNS
    else:
        cols = TARGET_HEADERLESS_COLUMNS[:df.shape[1]]
        if len(cols) < df.shape[1]:
            cols += [f"未使用{i}" for i in range(len(cols), df.shape[1])]
        df.columns = cols
    return df


def read_csv_smart(file_or_path):
    if hasattr(file_or_path, "read"):
        raw = file_or_path.getvalue()
    else:
        raw = Path(file_or_path).read_bytes()

    last_err = None
    for enc in ["utf-8-sig", "cp932", "shift_jis", "utf-8"]:
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, low_memory=False)
            # 条件CSVはそのまま読む
            if _condition_column_count(df) >= 5:
                return df
            # TARGETのヘッダーなしCSVを普通に読むと、1行目が列名扱いになります。
            # 必要列がほぼ認識できない場合は、ヘッダーなしとして読み直します。
            if _recognized_column_count(df) < 3:
                df2 = pd.read_csv(io.BytesIO(raw), encoding=enc, header=None, low_memory=False)
                return _assign_headerless_columns(df2)
            return df
        except Exception as e:
            last_err = e

    raise last_err


def standardize_columns(df):
    rename = {}
    cols_norm = {normalize_text(c): c for c in df.columns}
    for std, aliases in COLUMN_ALIASES.items():
        if std in df.columns:
            continue
        for a in aliases:
            key = normalize_text(a)
            if key in cols_norm:
                rename[cols_norm[key]] = std
                break
    return df.rename(columns=rename)


def to_num(x):
    if pd.isna(x):
        return None
    s = unicodedata.normalize("NFKC", str(x)).strip()
    s = s.replace(",", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except Exception:
        return None


def to_int_str(x):
    n = to_num(x)
    if n is None:
        return ""
    return str(int(n))


def sex_value(x):
    s = normalize_text(x)
    if "牝" in s:
        return "牝馬"
    if "セ" in s or "セン" in s or "騙" in s:
        return "セン馬"
    if "牡" in s:
        return "牡馬"
    return s


def age_axis(x):
    n = to_num(x)
    if n is None:
        return ""
    return f"年齢={int(n)}歳"


def surface_value(x):
    s = normalize_text(x)
    if s.startswith("芝") or s == "芝":
        return "芝"
    if s.startswith("ダ") or s == "ダート" or s == "ダ":
        return "ダ"
    return s[:1]


def going_value(x):
    s = normalize_text(x)
    if not s:
        return ""
    if s.startswith("稍"):
        return "稍"
    if s.startswith("良"):
        return "良"
    if s.startswith("重"):
        return "重"
    if s.startswith("不"):
        return "不"
    return s[:1]


def weight_band(x, prefix):
    n = to_num(x)
    if n is None:
        return ""
    if n <= 52:
        return f"{prefix}52以下"
    if n <= 54:
        return f"{prefix}53-54"
    if n <= 56:
        return f"{prefix}55-56"
    if n < 58:
        return f"{prefix}57"
    if n < 59:
        return f"{prefix}58"
    return f"{prefix}59以上"


def age_weight_diff_band(x):
    n = to_num(x)
    if n is None:
        return ""
    if n <= -2:
        return "馬齢斤量差-2以下"
    if n <= 0:
        return "馬齢斤量差-1〜0"
    if n <= 2:
        return "馬齢斤量差+1〜+2"
    return "馬齢斤量差+3以上"


def frame_band(x):
    n = to_num(x)
    if n is None:
        return ""
    n = int(n)
    if n <= 2:
        return "内枠1-2"
    if n <= 5:
        return "中枠3-5"
    return "外枠6-8"


def horse_no_band(no, field_size):
    n = to_num(no)
    h = to_num(field_size)
    if n is None or h is None or h <= 0:
        return ""
    r = n / h
    if r <= 1/3:
        return "内目"
    if r <= 2/3:
        return "中目"
    return "外目"


def interval_band(x):
    n = to_num(x)
    if n is None:
        return ""
    if n <= 2:
        return "間隔中2週以下"
    if n <= 4:
        return "間隔中3-4週"
    if n <= 8:
        return "間隔中5-8週"
    if n <= 12:
        return "間隔中9-12週"
    if n <= 24:
        return "間隔中13-24週"
    return "間隔半年以上"


def finish_band(x):
    n = to_num(x)
    if n is None:
        return ""
    n = int(n)
    if n <= 1:
        return "前走着順=1着"
    if n <= 3:
        return "前走着順2-3着"
    if n <= 5:
        return "前走着順4-5着"
    if n <= 9:
        return "前走着順6-9着"
    return "前走着順10着以下"


def margin_band(x):
    n = to_num(x)
    if n is None:
        return ""
    if n < 0:
        return "前走着差勝ち切り"
    if abs(n) < 1e-9:
        return "前走着差0.0"
    if n <= 0.3:
        return "前走着差0.1-0.3"
    if n <= 0.5:
        return "前走着差0.4-0.5"
    if n <= 1.0:
        return "前走着差0.6-1.0"
    return "前走着差1.1以上"


def agari_band(x):
    n = to_num(x)
    if n is None:
        return ""
    n = int(n)
    if n <= 1:
        return "前走上り1位"
    if n <= 3:
        return "前走上り2-3位"
    if n <= 5:
        return "前走上り4-5位"
    if n <= 9:
        return "前走上り6-9位"
    return "前走上り10位以下"


def field_size_band(x):
    n = to_num(x)
    if n is None:
        return ""
    n = int(n)
    if n <= 9:
        return "前走頭数9頭以下"
    if n <= 13:
        return "前走頭数10-13頭"
    if n <= 15:
        return "前走頭数14-15頭"
    if n <= 17:
        return "前走頭数16-17頭"
    return "前走頭数18頭以上"


def corner_band(pos, field_size, prefix):
    p = to_num(pos)
    h = to_num(field_size)
    if p is None or h is None or h <= 0:
        return ""
    if int(p) == 1:
        return f"{prefix}1番手"
    r = p / h
    if r <= 0.25:
        return f"{prefix}2-25%"
    if r <= 0.45:
        return f"{prefix}25-45%"
    if r <= 0.70:
        return f"{prefix}45-70%"
    return f"{prefix}70%以降"


def distance_change(cur, prev):
    c = to_num(cur)
    p = to_num(prev)
    if c is None or p is None:
        return ""
    d = c - p
    if d == 0:
        return "同距離"
    if d >= 400:
        return "大幅延長"
    if d > 0:
        return "延長"
    if d <= -400:
        return "大幅短縮"
    return "短縮"


def clean_category(x):
    return normalize_text(x) if not pd.isna(x) else ""


def derive_features(df):
    df = standardize_columns(df.copy())
    for c in REQUIRED_COLUMNS_CORE:
        if c not in df.columns:
            df[c] = pd.NA

    out = df.copy()
    out["重賞名_norm"] = out["レース名"].map(normalize_text)
    out["年齢軸値"] = out["年齢"].map(age_axis)
    out["性別軸値"] = out["性別"].map(sex_value)

    out["今回馬場"] = out["馬場状態"].map(going_value)
    out["前走馬場"] = out["前走馬場状態"].map(going_value)
    out["前走芝ダ"] = out["前芝・ダ"].map(surface_value)
    out["騎手替"] = out["替"].map(lambda x: "*" if normalize_text(x) == "*" else "")
    out["馬齢斤量差帯"] = out["馬齢斤量差"].map(age_weight_diff_band)
    out["前走着順帯"] = out["前走着順"].map(finish_band)
    out["前走着差帯"] = out["前走着差タイム"].map(margin_band)
    out["所属"] = out["所属"].map(clean_category)
    out["前走所属"] = out["前走所属"].map(clean_category)
    out["間隔帯"] = out["間隔"].map(interval_band)
    out["枠番帯"] = out["枠番"].map(frame_band)
    out["馬番帯"] = [horse_no_band(n, h) for n, h in zip(out["馬番"], out["頭数"])]
    out["前走上り順位帯"] = out["前走上り3F順"].map(agari_band)
    out["距離変化"] = [distance_change(c, p) for c, p in zip(out["距離"], out["前距離"])]
    out["前走場所"] = out["前走場所"].map(clean_category)
    out["前走クラス"] = out["前クラス名"].map(clean_category)
    out["前走頭数帯"] = out["前走頭数"].map(field_size_band)
    out["前走脚質"] = out["前走脚質"].map(clean_category).replace("", "不明")
    out["前走決め手"] = out["前走決め手"].map(clean_category).replace("", "不明")
    out["前3角位置帯"] = [corner_band(p, h, "前3角") for p, h in zip(out["前3角"], out["前走頭数"])]
    out["前4角位置帯"] = [corner_band(p, h, "前4角") for p, h in zip(out["前4角"], out["前走頭数"])]
    out["前走斤量帯"] = out["前走斤量"].map(lambda x: weight_band(x, "前走斤量"))
    out["斤量帯"] = out["斤量"].map(lambda x: weight_band(x, "斤量"))
    out["父系統"] = out["父タイプ名"].map(clean_category)
    out["母父系統"] = out["母父タイプ名"].map(clean_category)
    out["前走距離"] = out["前距離"].map(to_int_str)
    out["前走レース"] = out["前走レース名"].map(clean_category)
    return out


def load_conditions(file_or_path):
    cond = read_csv_smart(file_or_path)
    needed = ["重賞名", "基準軸", "基準値", "条件1", "条件2", "条件内容", "該当数", "複勝数", "複勝率", "条件タイプ", "採用ランク"]
    missing = [c for c in needed if c not in cond.columns]
    if missing:
        raise ValueError("条件CSVに必要列がありません: " + ", ".join(missing))
    cond = cond.copy()
    cond["重賞名_norm"] = cond["重賞名"].map(normalize_text)
    cond["条件1_prefix"] = cond["条件1"].astype(str).str.split("=", n=1).str[0]
    cond["条件2_prefix"] = cond["条件2"].astype(str).str.split("=", n=1).str[0]
    cond["条件グループ"] = (
        cond["基準軸"].astype(str) + ":" + cond["基準値"].astype(str) + ":" +
        cond["条件タイプ"].astype(str) + ":" + cond["採用ランク"].astype(str) + ":" +
        cond[["条件1_prefix", "条件2_prefix"]].apply(lambda r: "+".join(sorted([str(r.iloc[0]), str(r.iloc[1])])), axis=1)
    )
    return cond


def condition_matches(row, cond_row):
    if cond_row["基準軸"] == "年齢":
        if row.get("年齢軸値", "") != str(cond_row["基準値"]):
            return False
    elif cond_row["基準軸"] == "性別":
        if row.get("性別軸値", "") != str(cond_row["基準値"]):
            return False
    else:
        return False

    for cond_col in ["条件1", "条件2"]:
        txt = str(cond_row[cond_col])
        if "=" not in txt:
            return False
        key, val = txt.split("=", 1)
        actual = row.get(key, "")
        if str(actual) != val:
            return False
    return True


def judge_horse(matched):
    if matched.empty:
        return "通常"
    buy = matched[matched["条件タイプ"] == "買い100"]
    keshi = matched[matched["条件タイプ"] == "消し0"]
    buy_s = buy[buy["採用ランク"] == "強買いS"]
    keshi_s = keshi[keshi["採用ランク"] == "強消しS"]

    buy_group = buy["条件グループ"].nunique()
    keshi_group = keshi["条件グループ"].nunique()
    buy_s_group = buy_s["条件グループ"].nunique()
    keshi_s_group = keshi_s["条件グループ"].nunique()

    if buy_s_group >= 1 and keshi_group == 0:
        return "超有力"
    if buy_group >= 1 and keshi_group == 0:
        return "有力"
    if keshi_s_group >= 1 and buy_group == 0:
        return "危険"
    if keshi_group >= 1 and buy_group == 0:
        return "消し候補"
    if buy_group >= 1 and keshi_group >= 1:
        return "保留"
    return "通常"


def analyze(df_horses, cond, only_race_norm=None):
    horses = derive_features(df_horses)
    if only_race_norm:
        horses = horses[horses["重賞名_norm"] == only_race_norm].copy()
    results = []
    details = []

    cond_by_race = {k: v for k, v in cond.groupby("重賞名_norm")}
    for idx, row in horses.iterrows():
        race_norm = row.get("重賞名_norm", "")
        race_cond = cond_by_race.get(race_norm, cond.iloc[0:0])
        matched_rows = []
        for _, cr in race_cond.iterrows():
            if condition_matches(row, cr):
                matched_rows.append(cr)
        matched = pd.DataFrame(matched_rows)

        if not matched.empty:
            buy = matched[matched["条件タイプ"] == "買い100"]
            keshi = matched[matched["条件タイプ"] == "消し0"]
            buy_s = buy[buy["採用ランク"] == "強買いS"]
            keshi_s = keshi[keshi["採用ランク"] == "強消しS"]
            buy_group = buy["条件グループ"].nunique()
            keshi_group = keshi["条件グループ"].nunique()
            buy_s_group = buy_s["条件グループ"].nunique()
            keshi_s_group = keshi_s["条件グループ"].nunique()
            buy_text = " / ".join(buy.sort_values(["採用ランク", "該当数"], ascending=[True, False])["条件内容"].head(8).astype(str))
            keshi_text = " / ".join(keshi.sort_values(["採用ランク", "該当数"], ascending=[True, False])["条件内容"].head(8).astype(str))
        else:
            buy_group = keshi_group = buy_s_group = keshi_s_group = 0
            buy_text = keshi_text = ""

        judge = judge_horse(matched)
        results.append({
            "レース名": row.get("レース名", ""),
            "馬番": row.get("馬番", ""),
            "馬名": row.get("馬名", ""),
            "性別": row.get("性別", ""),
            "年齢": row.get("年齢", ""),
            "判定": judge,
            "買いSグループ": buy_s_group,
            "買い全グループ": buy_group,
            "消しSグループ": keshi_s_group,
            "消し全グループ": keshi_group,
            "買い条件例": buy_text,
            "消し条件例": keshi_text,
        })

        if not matched.empty:
            tmp = matched.copy()
            tmp.insert(0, "馬名", row.get("馬名", ""))
            tmp.insert(0, "馬番", row.get("馬番", ""))
            tmp.insert(0, "レース名", row.get("レース名", ""))
            details.append(tmp)

    res = pd.DataFrame(results)
    det = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    if not res.empty:
        order = {"超有力": 1, "有力": 2, "保留": 3, "通常": 4, "消し候補": 5, "危険": 6}
        res["表示順"] = res["判定"].map(order).fillna(9)
        res = res.sort_values(["レース名", "表示順", "消しSグループ", "買いSグループ", "馬番"], ascending=[True, True, True, False, True]).drop(columns=["表示順"])
    return res, det


def csv_bytes(df):
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


st.title(APP_TITLE)
st.caption("重賞別に保存した『年齢/牡馬/牝馬 × 追加2条件』の複勝率100%・0%条件を、今年の出走馬CSVへ照合します。")

with st.expander("予想CSVに必要な項目", expanded=False):
    st.write("TARGETから以下の項目を出してください。列名は完全一致でなくても、近い列名ならアプリ側で自動対応します。")
    st.code("\n".join(REQUIRED_COLUMNS_CORE), language="text")
    st.info("最低限重要なのは、レース名・馬名・性別・年齢・前走着順・前走着差タイム・前距離・前芝ダ・前走場所・前クラス名・間隔・枠番・馬番・斤量・血統系統です。TARGETのヘッダーなしCSVにも対応しています。馬場状態・前走所属がなくても、その条件だけ未該当扱いで動きます。")

col1, col2 = st.columns(2)
with col1:
    cond_upload = st.file_uploader("条件CSVをアップロード", type=["csv"], help=f"例：{CONDITION_FILE}")
with col2:
    horse_upload = st.file_uploader("今年の重賞出走馬CSVをアップロード", type=["csv"])

cond = None
try:
    if cond_upload is not None:
        cond = load_conditions(cond_upload)
    elif Path(CONDITION_FILE).exists():
        cond = load_conditions(CONDITION_FILE)
    elif Path("data") .joinpath(CONDITION_FILE).exists():
        cond = load_conditions(Path("data") / CONDITION_FILE)
except Exception as e:
    st.error(f"条件CSVの読み込みに失敗しました: {e}")

if cond is not None:
    st.success(f"条件CSV読込完了：{len(cond):,} 条件 / {cond['重賞名'].nunique():,} 重賞")
    with st.expander("条件CSVサマリー", expanded=False):
        summary = cond.pivot_table(index="重賞名", columns="採用ランク", values="条件内容", aggfunc="count", fill_value=0).reset_index()
        st.dataframe(summary, use_container_width=True)
else:
    st.warning("条件CSVをアップロードしてください。")

if horse_upload is not None and cond is not None:
    try:
        horses_raw = read_csv_smart(horse_upload)
        horses_raw = standardize_columns(horses_raw)

        only_grade = st.checkbox("重賞のみ自動抽出する（レース名にG1/G2/G3を含む行）", value=True)
        if only_grade and "レース名" in horses_raw.columns:
            grade_mask = horses_raw["レース名"].astype(str).str.contains(r"G1|G2|G3|Ｇ１|Ｇ２|Ｇ３", regex=True, na=False)
            horses_raw = horses_raw[grade_mask].copy()

        horses_tmp = derive_features(horses_raw)
        race_options = sorted(horses_tmp["重賞名_norm"].dropna().unique().tolist())
        race_label_map = {normalize_text(r): r for r in horses_raw.get("レース名", pd.Series(dtype=str)).dropna().unique()}
        selected = st.selectbox("対象重賞", ["すべて"] + race_options, format_func=lambda x: "すべて" if x == "すべて" else race_label_map.get(x, x))
        race_norm = None if selected == "すべて" else selected

        result_df, detail_df = analyze(horses_raw, cond, race_norm)
        st.subheader("判定結果")
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("判定結果CSVを保存", data=csv_bytes(result_df), file_name="jusho_extreme_judgement.csv", mime="text/csv")
        with c2:
            if not detail_df.empty:
                st.download_button("該当条件詳細CSVを保存", data=csv_bytes(detail_df), file_name="jusho_extreme_matched_conditions.csv", mime="text/csv")

        st.subheader("見やすいまとめ")
        for judge in ["超有力", "有力", "保留", "危険", "消し候補", "通常"]:
            part = result_df[result_df["判定"] == judge]
            if part.empty:
                continue
            st.markdown(f"### {judge}")
            for _, r in part.iterrows():
                st.markdown(f"**{r.get('馬番','')} {r.get('馬名','')}**　買いS:{r['買いSグループ']} / 買い:{r['買い全グループ']} / 消しS:{r['消しSグループ']} / 消し:{r['消し全グループ']}")
                if r.get("買い条件例"):
                    st.caption("買い条件例：" + str(r["買い条件例"]))
                if r.get("消し条件例"):
                    st.caption("消し条件例：" + str(r["消し条件例"]))

    except Exception as e:
        st.error(f"出走馬CSVの分析に失敗しました: {e}")
else:
    st.info("条件CSVと今年の重賞出走馬CSVを入れると、判定結果が表示されます。")

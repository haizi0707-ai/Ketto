import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="TARGET読み込み確認アプリ", layout="wide")

APP_VERSION = "target_reader_step1_v1_2026-05-15"

HEADERLESS_TARGET_COLUMNS = [
    "日付", "場所", "場R", "レース名", "芝ダ", "距離", "馬番", "馬名",
    "種牡馬", "父タイプ名", "母父名", "母父タイプ名",
    "性別", "年齢", "斤量", "頭数",
    "前走馬場状態", "前芝ダ", "前距離", "前走斤量",
    "休み明け〜戦目", "所属", "調教師", "騎手", "前走騎手",
    "前走着順", "前走着差", "前走頭数",
    "前走通過順1", "前走通過順2", "前走通過順3", "前走通過順4",
    "前走上り3F順", "前走脚質", "前走場所", "前走場所区分",
]

REQUIRED_FOR_CURRENT_PLAN = [
    "日付", "場所", "R", "レース名", "芝ダ", "距離", "馬番", "馬名",
    "種牡馬", "父タイプ名", "母父名", "母父タイプ名",
    "性別", "年齢", "斤量", "頭数",
    "前走馬場状態", "前芝ダ", "前距離", "前走斤量",
    "休み明け〜戦目", "調教師", "騎手", "前走騎手",
    "前走着順", "前走着差", "前走頭数",
    "前走通過順3", "前走通過順4",
    "前走上り3F順", "前走脚質", "前走場所",
]


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
    s = s.replace("Ｒ", "R")
    s = s.replace("芝・ダ", "芝ダ")
    s = s.replace("芝ダ・距離", "芝ダ距離")
    s = s.replace("～", "〜")
    return re.sub(r"\s+", "", s)


def to_int(x):
    try:
        if x is None or pd.isna(x):
            return None
        m = re.search(r"\d+", str(x))
        return int(m.group(0)) if m else None
    except Exception:
        return None


def parse_date(v):
    s = norm_text(v)
    if not s:
        return ""
    if re.fullmatch(r"\d{4}", s):
        return f"2026.{s[:2]}.{s[2:4]}"
    if re.fullmatch(r"\d{6}", s):
        return f"20{s[:2]}.{s[2:4]}.{s[4:6]}"
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}.{s[4:6]}.{s[6:8]}"
    s = s.replace("/", ".").replace("-", ".")
    parts = s.split(".")
    if len(parts) == 3:
        return f"{parts[0]}.{parts[1].zfill(2)}.{parts[2].zfill(2)}"
    return s


def looks_like_headerless_target(df):
    cols = [str(c).strip() for c in df.columns]
    if len(cols) < 8:
        return False
    date_like = bool(re.fullmatch(r"\d{3,8}", cols[0]))
    place_like = cols[1] in [
        "札", "函", "福", "新", "東", "中", "名", "京", "阪", "小",
        "札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉",
    ]
    r_like = bool(re.search(r"\d+", cols[2]))
    return date_like and place_like and r_like


def read_csv_smart(uploaded_file):
    encodings = ["cp932", "shift_jis", "utf-8-sig", "utf-8"]
    last_err = None

    for enc in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=enc)

            if looks_like_headerless_target(df):
                uploaded_file.seek(0)
                raw = pd.read_csv(uploaded_file, encoding=enc, header=None)
                raw = raw.iloc[:, :len(HEADERLESS_TARGET_COLUMNS)]
                raw.columns = HEADERLESS_TARGET_COLUMNS[:len(raw.columns)]
                return raw, enc, "ヘッダーなしCSVとして読み込み"

            return df, enc, "ヘッダーありCSVとして読み込み"

        except Exception as e:
            last_err = e

    raise last_err


def normalize_target(df):
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]

    rename_map = {
        "場": "場所",
        "場R": "R",
        "レース": "R",
        "レース番号": "R",
        "馬番号": "馬番",
        "芝ダ距離": "距離",
        "レース名(クラス)": "レース名",
        "前走馬場状態": "前走馬場状態",
        "前馬場状態": "前走馬場状態",
        "前距離": "前走距離",
        "前芝ダ": "前走芝ダ",
        "前芝・ダ": "前走芝ダ",
        "前着順": "前走着順",
        "前走着": "前走着順",
        "前差": "前走着差",
        "前頭数": "前走頭数",
        "前3角": "前走通過順3",
        "前4角": "前走通過順4",
        "前走3角": "前走通過順3",
        "前走4角": "前走通過順4",
        "前走上り順位": "前走上り3F順",
        "前走上がり順位": "前走上り3F順",
        "前走上がり3F順": "前走上り3F順",
        "前走上がり3F": "前走上り3F",
        "父系統": "父タイプ名",
        "母父系統": "母父タイプ名",
        "母父": "母父名",
    }

    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    place_map = {
        "札": "札幌", "函": "函館", "福": "福島", "新": "新潟", "東": "東京",
        "中": "中山", "名": "中京", "京": "京都", "阪": "阪神", "小": "小倉",
    }

    if "場所" in df.columns:
        df["場所"] = df["場所"].apply(lambda x: place_map.get(norm_text(x), norm_text(x)))
    else:
        df["場所"] = ""

    if "R" in df.columns:
        df["R"] = df["R"].apply(to_int)
    else:
        df["R"] = None

    if "距離" in df.columns:
        raw = df["距離"].astype(str)

        if "芝ダ" not in df.columns:
            df["芝ダ"] = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
        else:
            miss = df["芝ダ"].map(norm_text).eq("")
            ext = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
            df.loc[miss, "芝ダ"] = ext[miss]

        df["距離"] = raw.str.extract(r"(\d+)", expand=False).apply(to_int)
    else:
        df["距離"] = None
        if "芝ダ" not in df.columns:
            df["芝ダ"] = ""

    if "前走距離" in df.columns:
        raw = df["前走距離"].astype(str)

        if "前走芝ダ" not in df.columns:
            df["前走芝ダ"] = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
        else:
            miss = df["前走芝ダ"].map(norm_text).eq("")
            ext = raw.str.extract(r"([芝ダ])", expand=False).fillna("")
            df.loc[miss, "前走芝ダ"] = ext[miss]

        df["前走距離"] = raw.str.extract(r"(\d+)", expand=False).apply(to_int)

    if "日付" in df.columns:
        df["日付"] = df["日付"].map(parse_date)
    else:
        df["日付"] = ""

    return df


def missing_columns_report(df, required_cols):
    missing = [c for c in required_cols if c not in df.columns]
    existing = [c for c in required_cols if c in df.columns]
    return existing, missing


st.title("TARGET読み込み確認アプリ")
st.caption(f"バージョン: {APP_VERSION}")
st.write("まずはTARGET/JRA-VAN由来CSVを正しく読み込めるかだけを確認します。予想・鉄板・消寄・画像生成はまだ行いません。")

with st.expander("この段階で確認すること", expanded=True):
    st.write(
        "1. CSVが読み込めるか\n"
        "2. ヘッダーあり/なしを正しく判定できるか\n"
        "3. 列名を統一できるか\n"
        "4. 7〜12Rだけ抽出できるか\n"
        "5. 場所・R・芝ダ・距離・馬名などが正しく表示されるか"
    )

uploaded = st.file_uploader("TARGET/JRA-VAN由来CSVを選択", type=["csv"])

if uploaded is not None:
    try:
        raw_df, encoding, read_mode = read_csv_smart(uploaded)
        normalized_df = normalize_target(raw_df)
        target_df = normalized_df[normalized_df["R"].isin([7, 8, 9, 10, 11, 12])].copy()

        st.success("CSVを読み込みました。")

        c1, c2, c3 = st.columns(3)
        c1.metric("読み込み方式", read_mode)
        c2.metric("文字コード", encoding)
        c3.metric("元データ行数", len(normalized_df))

        c4, c5, c6 = st.columns(3)
        c4.metric("7〜12R行数", len(target_df))
        c5.metric("列数", len(normalized_df.columns))
        c6.metric("対象R数", target_df["R"].nunique() if not target_df.empty else 0)

        st.subheader("競馬場一覧")
        if "場所" in normalized_df.columns:
            st.write(sorted([x for x in normalized_df["場所"].dropna().unique().tolist() if str(x).strip() != ""]))
        else:
            st.warning("場所列がありません。")

        st.subheader("R一覧")
        if "R" in normalized_df.columns:
            st.write(sorted([int(x) for x in normalized_df["R"].dropna().unique().tolist() if pd.notna(x)]))
        else:
            st.warning("R列がありません。")

        st.subheader("必要列チェック")
        existing, missing = missing_columns_report(normalized_df, REQUIRED_FOR_CURRENT_PLAN)

        col_a, col_b = st.columns(2)
        with col_a:
            st.write("存在する列")
            st.code("\n".join(existing) if existing else "なし")
        with col_b:
            st.write("不足している列")
            if missing:
                st.error("\n".join(missing))
            else:
                st.success("不足列なし")

        st.subheader("列名一覧")
        st.code("\n".join([str(c) for c in normalized_df.columns.tolist()]))

        st.subheader("7〜12R 先頭30行")
        preview_cols = [
            "日付", "場所", "R", "レース名", "芝ダ", "距離", "馬番", "馬名",
            "父タイプ名", "母父タイプ名",
            "前走場所", "前走芝ダ", "前走距離", "前走着順", "前走着差",
            "前走頭数", "前走通過順3", "前走通過順4", "前走上り3F順", "前走脚質",
        ]
        available_preview_cols = [c for c in preview_cols if c in target_df.columns]

        if target_df.empty:
            st.warning("7〜12Rのデータがありません。")
        else:
            st.dataframe(target_df[available_preview_cols].head(30), use_container_width=True, hide_index=True)

        st.subheader("正規化済みCSVダウンロード")
        csv_out = normalized_df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "正規化済みCSVをダウンロード",
            csv_out,
            file_name="target_normalized_check.csv",
            mime="text/csv",
            use_container_width=True,
        )

    except Exception as e:
        st.error("読み込み中にエラーが出ました。")
        st.exception(e)
else:
    st.info("CSVファイルを選択してください。")

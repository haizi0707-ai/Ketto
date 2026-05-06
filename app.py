# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "地方・海外向け 血統適性プロンプト作成アプリ"
BASE_DIR = Path(__file__).parent

st.set_page_config(page_title=APP_TITLE, page_icon="🧬", layout="wide")

CSV_FILES = {
    "top": "分類別_TOP条件抜粋.csv",
    "summary": "分類別_強い系統血統サマリー.csv",
    "course_summary": "コースタイプ別_強い血統まとめ.csv",
    "map": "中央競馬場タイプ_地方変換マップ.csv",
    "sire_line": "競馬場_父系統_枠馬場成績.csv",
    "bms_line": "競馬場_母父系統_枠馬場成績.csv",
    "sire": "競馬場_父_枠馬場成績.csv",
    "bms": "競馬場_母父_枠馬場成績.csv",
}

def normalize_filename(name: str) -> str:
    return unicodedata.normalize("NFKC", str(name)).replace(" ", "").replace("　", "").lower()

def find_csv_fuzzy(key: str) -> Path | None:
    """iPhone/GitHubアップロード時のファイル名ゆれ対策。完全一致しなくても探す。"""
    candidates = sorted(BASE_DIR.glob("*.csv"))
    if not candidates:
        return None

    wanted = normalize_filename(CSV_FILES.get(key, ""))
    for p in candidates:
        if normalize_filename(p.name) == wanted:
            return p

    rules = {
        "top": ["分類別", "top", "条件", "抜粋"],
        "summary": ["分類別", "強い", "系統", "サマリー"],
        "course_summary": ["コースタイプ", "強い", "血統", "まとめ"],
        "map": ["中央競馬場", "地方", "変換", "マップ"],
        "sire_line": ["父系統", "枠馬場", "成績"],
        "bms_line": ["母父系統", "枠馬場", "成績"],
        "sire": ["競馬場", "父", "枠馬場", "成績"],
        "bms": ["競馬場", "母父", "枠馬場", "成績"],
    }
    words = [normalize_filename(w) for w in rules.get(key, [])]
    scored = []
    for p in candidates:
        n = normalize_filename(p.name)
        # 父と父系統、母父と母父系統の取り違えを防ぐ
        if key == "sire" and "父系統" in n:
            continue
        if key == "bms" and "母父系統" in n:
            continue
        if key == "sire_line" and "父系統" not in n:
            continue
        if key == "bms_line" and "母父系統" not in n:
            continue
        score = sum(1 for w in words if w in n)
        if score:
            scored.append((score, p))
    if scored:
        return sorted(scored, key=lambda x: x[0], reverse=True)[0][1]
    return None

CENTRAL_TRACK_TYPES = {
    "東京": "直線長め・持続型",
    "中京": "直線長め・持続型",
    "新潟": "直線長め・平坦型",
    "中山": "坂あり・パワー型",
    "阪神": "坂あり・パワー型",
    "京都": "平坦・スピード型",
    "福島": "小回り・機動型",
    "小倉": "小回り・機動型",
    "札幌": "小回り・持続型",
    "函館": "小回り・持続型",
}

LOCAL_TRACK_TYPES = {
    "大井": "直線長め・持続型",
    "門別": "直線長め・平坦型",
    "船橋": "平坦・スピード型",
    "川崎": "小回り・機動型",
    "浦和": "小回り・機動型",
    "園田": "小回り・持続型",
    "名古屋": "小回り・機動型",
    "笠松": "小回り・機動型",
    "金沢": "坂あり・パワー型",
    "高知": "坂あり・パワー型",
    "佐賀": "小回り・機動型",
    "水沢": "小回り・持続型",
    "盛岡": "直線長め・持続型",
    "帯広": "坂あり・パワー型",
}

OVERSEAS_TRACK_TYPES = {
    "メイダン": "直線長め・持続型",
    "シャティン": "平坦・スピード型",
    "ロンシャン": "坂あり・パワー型",
    "ドバイ": "直線長め・持続型",
    "香港": "平坦・スピード型",
    "サウジ": "直線長め・持続型",
    "アメリカ小回り": "小回り・機動型",
    "欧州タフ馬場": "坂あり・パワー型",
    "豪州スピード型": "平坦・スピード型",
}

DISTANCE_BANDS = [
    "短距離(1000-1300)",
    "短中距離(1400-1600)",
    "中距離(1700-2000)",
    "中長距離(2100-2400)",
    "長距離(2500-)"
]

SURFACES = ["ダ", "芝"]
GROUND_CHOICES = ["良", "稍", "重不良", "未定"]
FRAME_CHOICES = ["全枠", "内枠(1-2)", "中枠(3-6)", "外枠(7-8)"]


def read_csv_auto(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    raw = path.read_bytes()
    for enc in ["utf-8-sig", "cp932", "utf-8"]:
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc)
            df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
            return df
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_data():
    data = {}
    paths = {}
    for key, fname in CSV_FILES.items():
        path = find_csv_fuzzy(key) or (BASE_DIR / fname)
        paths[key] = path
        data[key] = read_csv_auto(path)
    return data, paths


def norm_text(v) -> str:
    if pd.isna(v):
        return ""
    return unicodedata.normalize("NFKC", str(v)).strip()


def distance_to_band(distance: int | float | str) -> str:
    try:
        d = int(float(str(distance).replace("m", "")))
    except Exception:
        return DISTANCE_BANDS[2]
    if d <= 1300:
        return DISTANCE_BANDS[0]
    if d <= 1600:
        return DISTANCE_BANDS[1]
    if d <= 2000:
        return DISTANCE_BANDS[2]
    if d <= 2400:
        return DISTANCE_BANDS[3]
    return DISTANCE_BANDS[4]


def frame_zone_from_gate(gate) -> str:
    try:
        g = int(float(gate))
    except Exception:
        return ""
    if g <= 2:
        return "内枠(1-2)"
    if g <= 6:
        return "中枠(3-6)"
    return "外枠(7-8)"


def filter_stats(df: pd.DataFrame, course_type: str, surface: str, band: str, ground: str, frame: str, blood_kind: str | None = None, top_n: int = 20) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if "コースタイプ" in out.columns:
        out = out[out["コースタイプ"].astype(str) == course_type]
    if "芝・ダ" in out.columns:
        out = out[out["芝・ダ"].astype(str) == surface]
    if "距離帯" in out.columns:
        out = out[out["距離帯"].astype(str) == band]
    if ground != "未定" and "馬場分類" in out.columns:
        out = out[out["馬場分類"].astype(str) == ground]
    if frame != "全枠" and "枠ゾーン" in out.columns:
        out = out[out["枠ゾーン"].astype(str) == frame]
    if blood_kind and "血統区分" in out.columns:
        out = out[out["血統区分"].astype(str) == blood_kind]
    if out.empty:
        return out
    sort_cols = [c for c in ["評価", "リフト", "複勝率", "母数"] if c in out.columns]
    # 評価はAが文字列なので、補助の数値化
    if "評価" in out.columns:
        order = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
        out["評価順"] = out["評価"].map(order).fillna(0)
        sort_cols = ["評価順"] + [c for c in sort_cols if c != "評価"]
    return out.sort_values(sort_cols, ascending=False).head(top_n).reset_index(drop=True)


def format_condition_lines(df: pd.DataFrame, max_rows: int = 12) -> list[str]:
    lines = []
    if df is None or df.empty:
        return lines
    for _, r in df.head(max_rows).iterrows():
        name = r.get("血統名", "")
        kind = r.get("血統区分", "")
        lift = r.get("リフト", "")
        pr = r.get("複勝率", "")
        n = r.get("母数", "")
        ev = r.get("評価", "")
        try:
            lift = f"{float(lift):.3f}"
        except Exception:
            lift = str(lift)
        try:
            pr = f"{float(pr)*100:.1f}%"
        except Exception:
            pr = str(pr)
        lines.append(f"・{kind}『{name}』：評価{ev} / 母数{n} / 複勝率{pr} / リフト{lift}")
    return lines


def build_prompt(target_label: str, year: str, area_type: str, racecourse: str, course_type: str,
                 surface: str, distance_value: str, band: str, ground: str, frame_mode: str,
                 sire_line_df: pd.DataFrame, bms_line_df: pd.DataFrame, sire_df: pd.DataFrame, bms_df: pd.DataFrame) -> str:
    header = "対象区分,競馬場,年,距離,芝ダ,想定馬場,馬番,枠番,馬名,父,母父,父系統,母父系統,枠ゾーン,父系統適性,母父系統適性,父適性,母父適性,総合血統評価,補足"
    lines = []
    lines.append("あなたは地方・海外向け血統適性CSV作成AIです。")
    lines.append("")
    lines.append(f"【対象】{year}年 {target_label}")
    lines.append(f"【対象区分】{area_type}")
    lines.append(f"【競馬場】{racecourse}")
    lines.append(f"【中央換算コースタイプ】{course_type}")
    lines.append(f"【距離】{distance_value}m / {band}")
    lines.append(f"【芝ダ】{surface}")
    lines.append(f"【想定馬場】{ground}")
    lines.append(f"【枠条件】{frame_mode}")
    lines.append("")
    lines.append("【目的】")
    lines.append("中央15年分の血統×競馬場タイプ×距離帯×馬場×枠データを地方・海外へ横展開し、出走馬の血統適性をCSVで判定してください。")
    lines.append("ランキングではなく、競馬場タイプに血統が合う馬を炙り出すための判定CSVです。")
    lines.append("")
    lines.append("【最重要：出力形式】")
    lines.append("・最終回答は必ずCSV本文のみ")
    lines.append("・Markdown、コードブロック、説明文、箇条書き、表形式は禁止")
    lines.append("・回答の1文字目は必ずCSVヘッダーの『対象区分』から始める")
    lines.append("・全出走馬を1頭1行で出力する")
    lines.append("・列名と列数は下のCSVヘッダーと完全一致させる")
    lines.append("・オッズ、人気、予想印、AI指数は使わない")
    lines.append("・判断不能な血統項目は×、不明な系統は不明と書く")
    lines.append("・補足は短く、カンマを使わない")
    lines.append("")
    lines.append("【今回重視する血統条件】")
    lines.append("■父系統で強い条件")
    lines += format_condition_lines(sire_line_df, 10) or ["・該当データなし"]
    lines.append("■母父系統で強い条件")
    lines += format_condition_lines(bms_line_df, 10) or ["・該当データなし"]
    lines.append("■父個別で強い条件")
    lines += format_condition_lines(sire_df, 10) or ["・該当データなし"]
    lines.append("■母父個別で強い条件")
    lines += format_condition_lines(bms_df, 10) or ["・該当データなし"]
    lines.append("")
    lines.append("【評価基準】")
    lines.append("・父系統適性：今回条件の父系統に該当する場合は○、強く該当する場合は◎、非該当は×")
    lines.append("・母父系統適性：今回条件の母父系統に該当する場合は○、強く該当する場合は◎、非該当は×")
    lines.append("・父適性：父個別が強条件に該当する場合は○または◎、非該当は×")
    lines.append("・母父適性：母父個別が強条件に該当する場合は○または◎、非該当は×")
    lines.append("・総合血統評価は S/A/B/C/D で記入")
    lines.append("・S：父系統・母父系統・父/母父個別のうち複数が強く一致")
    lines.append("・A：系統主軸が明確に一致")
    lines.append("・B：どちらか一方が一致")
    lines.append("・C：平均的")
    lines.append("・D：今回条件とはズレる")
    lines.append("")
    lines.append("【CSVヘッダー】")
    lines.append(header)
    lines.append("")
    lines.append("【出力例：形式だけ参考】")
    lines.append(f"{area_type},{racecourse},{year},{distance_value},{surface},{ground},1,1,サンプルホース,サンプル父,サンプル母父,サンデー系,ミスプロ系,内枠(1-2),○,×,○,×,A,父系統と枠が一致")
    lines.append("")
    lines.append("この依頼への回答は、上記CSVヘッダーから始まるCSV本文のみで返してください。")
    return "\n".join(lines)


def build_app():
    data, loaded_paths = load_data()
    st.title(APP_TITLE)
    st.caption("中央15年分の血統×競馬場×距離帯×馬場×枠データをもとに、地方・海外へ横展開するためのプロンプトを作成します。")

    missing_keys = [key for key, df in data.items() if df is None or df.empty]
    if missing_keys:
        st.error("必要CSVが読み込めません。GitHub上でapp.pyと同じ階層にCSVを置いてください。")
        st.write("読み込みに失敗した項目:", {k: CSV_FILES.get(k, k) for k in missing_keys})
        st.write("現在認識しているCSV:", [p.name for p in BASE_DIR.glob("*.csv")])
        st.write("自動選択したファイル:", {k: (v.name if v else "未検出") for k, v in loaded_paths.items()})
        st.stop()

    with st.sidebar:
        st.header("条件選択")
        area_type = st.selectbox("競馬場区分", ["中央", "地方", "海外"])
        if area_type == "中央":
            racecourse = st.selectbox("競馬場", list(CENTRAL_TRACK_TYPES.keys()))
            course_type = CENTRAL_TRACK_TYPES[racecourse]
        elif area_type == "地方":
            racecourse = st.selectbox("競馬場", list(LOCAL_TRACK_TYPES.keys()))
            default_type = LOCAL_TRACK_TYPES[racecourse]
            course_type = st.selectbox("中央換算コースタイプ", list(dict.fromkeys(LOCAL_TRACK_TYPES.values()).keys()), index=list(dict.fromkeys(LOCAL_TRACK_TYPES.values()).keys()).index(default_type))
        else:
            racecourse = st.selectbox("海外タイプ/競馬場", list(OVERSEAS_TRACK_TYPES.keys()))
            default_type = OVERSEAS_TRACK_TYPES[racecourse]
            course_type = st.selectbox("中央換算コースタイプ", list(dict.fromkeys(OVERSEAS_TRACK_TYPES.values()).keys()), index=list(dict.fromkeys(OVERSEAS_TRACK_TYPES.values()).keys()).index(default_type))

        surface = st.selectbox("芝ダ", SURFACES, index=0)
        distance_value = st.text_input("距離 m", value="1800")
        band = distance_to_band(distance_value)
        st.caption(f"距離帯：{band}")
        ground = st.selectbox("馬場分類", GROUND_CHOICES, index=0)
        frame_mode = st.selectbox("枠ゾーン", FRAME_CHOICES, index=0)
        year = st.text_input("対象年", value="2026")
        target_label = st.text_input("対象レース名", value=f"{racecourse}{distance_value}m")
        top_n = st.slider("表示する条件数", min_value=5, max_value=30, value=15)

    # 中央の場合は具体的な場所、地方/海外はコースタイプで横展開
    if area_type == "中央":
        place_filter = racecourse
    else:
        place_filter = None

    def filtered(table_key, blood_kind=None):
        df = data[table_key]
        out = filter_stats(df, course_type, surface, band, ground, frame_mode, blood_kind=blood_kind, top_n=top_n)
        if place_filter and not out.empty and "場所" in out.columns:
            out2 = out[out["場所"].astype(str) == place_filter].copy()
            # 中央で具体競馬場データが少ない場合はコースタイプ全体にフォールバック
            if len(out2) >= max(3, min(5, top_n // 2)):
                out = out2
        return out

    sire_line_df = filtered("sire_line", "父系統")
    bms_line_df = filtered("bms_line", "母父系統")
    sire_df = filtered("sire", "父")
    bms_df = filtered("bms", "母父")

    st.markdown("### 選択条件")
    st.write(f"**{area_type} / {racecourse}** → 中央換算：**{course_type}**｜{surface}{distance_value}m｜{band}｜馬場：{ground}｜枠：{frame_mode}")

    tab1, tab2, tab3 = st.tabs(["①強い血統確認", "②プロンプト作成", "③データ確認"])

    show_cols = ["場所", "コースタイプ", "芝・ダ", "距離帯", "馬場分類", "枠ゾーン", "血統区分", "血統名", "母数", "勝率", "複勝率", "単勝回収率", "複勝回収率", "基準複勝率", "複勝率差", "リフト", "評価", "特徴コメント"]

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("父系統")
            st.dataframe(sire_line_df[[c for c in show_cols if c in sire_line_df.columns]], use_container_width=True, hide_index=True)
            st.subheader("父")
            st.dataframe(sire_df[[c for c in show_cols if c in sire_df.columns]], use_container_width=True, hide_index=True)
        with c2:
            st.subheader("母父系統")
            st.dataframe(bms_line_df[[c for c in show_cols if c in bms_line_df.columns]], use_container_width=True, hide_index=True)
            st.subheader("母父")
            st.dataframe(bms_df[[c for c in show_cols if c in bms_df.columns]], use_container_width=True, hide_index=True)

    with tab2:
        prompt = build_prompt(target_label, year, area_type, racecourse, course_type, surface, distance_value, band, ground, frame_mode, sire_line_df, bms_line_df, sire_df, bms_df)
        st.subheader("コピペ用プロンプト")
        st.text_area("この内容を別チャットに貼り付け", value=prompt, height=620)
        st.download_button(
            "プロンプトをtxtでダウンロード",
            data=prompt.encode("utf-8"),
            file_name=f"bloodline_prompt_{area_type}_{racecourse}_{distance_value}.txt",
            mime="text/plain",
        )

    with tab3:
        st.subheader("中央競馬場タイプ変換表")
        if not data["map"].empty:
            st.dataframe(data["map"], use_container_width=True, hide_index=True)
        st.subheader("この条件の統合TOP抜粋")
        top = data["top"].copy()
        if not top.empty:
            top_filtered = filter_stats(top, course_type, surface, band, ground, frame_mode, top_n=50)
            st.dataframe(top_filtered[[c for c in show_cols if c in top_filtered.columns]], use_container_width=True, hide_index=True)
            csv = top_filtered.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("この条件のTOP血統CSVをダウンロード", data=csv.encode("utf-8-sig"), file_name="selected_bloodline_top.csv", mime="text/csv")


if __name__ == "__main__":
    build_app()

import io
import re
from html import escape as esc
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title='第3段階：直線＋鉄板判定確認', layout='wide')
APP_VERSION = 'straight_teppan_step3_v1_2026-05-15'
APP_DIR = Path(__file__).resolve().parent

HEADERLESS_TARGET_COLUMNS = [
    '日付','場所','場R','レース名','芝ダ','距離','馬番','馬名',
    '種牡馬','父タイプ名','母父名','母父タイプ名','性別','年齢','斤量','頭数',
    '前走馬場状態','前芝ダ','前距離','前走斤量','休み明け〜戦目','所属','調教師','騎手','前走騎手',
    '前走着順','前走着差','前走頭数','前走通過順1','前走通過順2','前走通過順3','前走通過順4',
    '前走上り3F順','前走脚質','前走場所','前走場所区分'
]

# ---------------------------------------------------------
# 共通関数
# ---------------------------------------------------------
def norm_text(v):
    if pd.isna(v):
        return ''
    s = str(v).strip().replace('\u3000', ' ')
    s = re.sub(r'\s+', '', s)
    return s[:-2] if s.endswith('.0') else s


def norm_col(c):
    s = str(c).strip().replace('\u3000', '')
    s = s.replace('Ｒ', 'R').replace('芝・ダ', '芝ダ').replace('芝ダ・距離', '芝ダ距離').replace('～', '〜')
    return re.sub(r'\s+', '', s)


def to_int(x):
    try:
        if x is None or pd.isna(x):
            return None
        m = re.search(r'-?\d+', str(x))
        return int(m.group(0)) if m else None
    except Exception:
        return None


def to_float(x):
    try:
        if x is None or pd.isna(x):
            return None
        s = str(x).strip()
        if '勝' in s or '同' in s:
            return 0.0
        s = s.replace('秒', '').replace('+', '').replace('▲', '').replace('△', '').replace('◇', '')
        m = re.search(r'-?\d+(?:\.\d+)?', s)
        return float(m.group(0)) if m else None
    except Exception:
        return None


def parse_date(v):
    s = norm_text(v)
    if not s:
        return ''
    if re.fullmatch(r'\d{4}', s):
        return f'2026.{s[:2]}.{s[2:4]}'
    if re.fullmatch(r'\d{6}', s):
        return f'20{s[:2]}.{s[2:4]}.{s[4:6]}'
    if re.fullmatch(r'\d{8}', s):
        return f'{s[:4]}.{s[4:6]}.{s[6:8]}'
    return s.replace('/', '.').replace('-', '.')


def looks_like_headerless_target(df):
    cols = [str(c).strip() for c in df.columns]
    if len(cols) < 8:
        return False
    first_ok = bool(re.fullmatch(r'\d{3,8}', cols[0]))
    third_ok = bool(re.search(r'\d+', cols[2]))
    return first_ok and third_ok


def read_csv_smart(uploaded_file):
    encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
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
                return raw, enc, 'ヘッダーなしCSV'
            return df, enc, 'ヘッダーありCSV'
        except Exception as e:
            last_err = e
    raise last_err


def normalize_target(df):
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]
    rename_map = {
        '場': '場所',
        '場R': 'R',
        'レース': 'R',
        'レース番号': 'R',
        '馬番号': '馬番',
        '芝ダ距離': '距離',
        'レース名(クラス)': 'レース名',
        '前馬場状態': '前走馬場状態',
        '前距離': '前走距離',
        '前芝ダ': '前走芝ダ',
        '前芝・ダ': '前走芝ダ',
        '前着順': '前走着順',
        '前走着': '前走着順',
        '前差': '前走着差',
        '前頭数': '前走頭数',
        '前3角': '前走通過順3',
        '前4角': '前走通過順4',
        '前走3角': '前走通過順3',
        '前走4角': '前走通過順4',
        '前走上り順位': '前走上り3F順',
        '前走上がり順位': '前走上り3F順',
        '前走上がり3F順': '前走上り3F順',
        '父系統': '父タイプ名',
        '母父系統': '母父タイプ名',
        '母父': '母父名',
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    place_map = {'札': '札幌', '函': '函館', '福': '福島', '新': '新潟', '東': '東京', '中': '中山', '名': '中京', '京': '京都', '阪': '阪神', '小': '小倉'}
    if '場所' in df.columns:
        df['場所'] = df['場所'].map(lambda x: place_map.get(norm_text(x), norm_text(x)))
    else:
        df['場所'] = ''
    df['競馬場'] = df['場所']

    if 'R' in df.columns:
        df['R'] = df['R'].map(to_int)
    else:
        df['R'] = None

    if '距離' in df.columns:
        raw = df['距離'].astype(str)
        if '芝ダ' not in df.columns:
            df['芝ダ'] = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
        else:
            miss = df['芝ダ'].map(norm_text).eq('')
            ext = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
            df.loc[miss, '芝ダ'] = ext[miss]
        df['距離'] = raw.str.extract(r'(\d+)', expand=False).map(to_int)
    else:
        df['距離'] = None
        if '芝ダ' not in df.columns:
            df['芝ダ'] = ''

    if '前走距離' in df.columns:
        raw = df['前走距離'].astype(str)
        if '前走芝ダ' not in df.columns:
            df['前走芝ダ'] = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
        else:
            miss = df['前走芝ダ'].map(norm_text).eq('')
            ext = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
            df.loc[miss, '前走芝ダ'] = ext[miss]
        df['前走距離'] = raw.str.extract(r'(\d+)', expand=False).map(to_int)
    else:
        df['前走距離'] = None
        if '前走芝ダ' not in df.columns:
            df['前走芝ダ'] = ''

    if '日付' in df.columns:
        df['日付'] = df['日付'].map(parse_date)
    else:
        df['日付'] = ''

    for c in ['場所', '競馬場', 'レース名', '芝ダ', '馬名', '父タイプ名', '母父タイプ名', '前走場所', '前走芝ダ', '前走脚質', '所属', '前走所属', '天気', '馬場状態', '性別']:
        if c not in df.columns:
            df[c] = ''
        df[c] = df[c].map(norm_text)

    # 追加で数値化しておきたい列
    for c in ['馬番', '頭数', '前走着順', '前走頭数', '前走通過順3', '前走通過順4', '前走上り3F順', '斤量', '前走斤量']:
        if c not in df.columns:
            df[c] = None

    return df

# ---------------------------------------------------------
# 直線ロジック
# ---------------------------------------------------------
def get_corner_category(pos, field_size):
    pos = to_int(pos)
    field_size = to_int(field_size)
    if pos is None:
        return ''
    if pos == 1:
        return '1番手'
    if field_size is None or field_size <= 0:
        if pos <= 3:
            return '2〜3番手'
        elif pos <= 6:
            return '4〜6番手'
        elif pos <= 10:
            return '7〜10番手'
        else:
            return '11番手以下'
    ratio = pos / field_size
    if pos <= 3 or ratio <= 0.20:
        return '2〜3番手'
    elif pos <= 6 or ratio <= 0.40:
        return '4〜6番手'
    elif pos <= 10 or ratio <= 0.70:
        return '7〜10番手'
    else:
        return '11番手以下'


def get_straight_type(place):
    place = norm_text(place)
    if '東京' in place:
        return '長直線'
    if '新潟' in place:
        return '長直線'
    if '中京' in place:
        return '長直線寄り'
    if '京都' in place:
        return '長直線寄り'
    if '阪神' in place:
        return '長直線寄り'
    if '中山' in place:
        return '短直線'
    if any(x in place for x in ['福島', '小倉', '札幌', '函館']):
        return '短直線'
    return ''


def calc_prev_straight_logic_score(row):
    score = 0
    rank = to_int(row.get('前走着順'))
    margin = to_float(row.get('前走着差'))
    prev_field = to_int(row.get('前走頭数'))
    c3 = to_int(row.get('前走通過順3'))
    c4 = to_int(row.get('前走通過順4'))
    agari_rank = to_int(row.get('前走上り3F順'))
    prev_dist = to_int(row.get('前走距離'))
    cur_dist = to_int(row.get('距離'))
    prev_surface = norm_text(row.get('前走芝ダ', ''))
    cur_surface = norm_text(row.get('芝ダ', ''))
    style = norm_text(row.get('前走脚質', ''))
    cur_field = to_int(row.get('頭数'))
    cat4 = get_corner_category(c4, prev_field)

    # A
    a = 0
    if rank == 1:
        a += 18
    elif rank in [2, 3]:
        a += 22
    elif rank in [4, 5]:
        a += 14
    elif rank is not None and 6 <= rank <= 9:
        a += 7
    if margin is not None:
        if margin <= 0.0:
            a += 5
        elif 0.1 <= margin <= 0.3:
            a += 8
        elif 0.4 <= margin <= 0.5:
            a += 5
        elif 0.6 <= margin <= 0.9:
            a += 2
    score += min(a, 25)

    # B
    b = {'2〜3番手': 12, '4〜6番手': 14, '7〜10番手': 8, '11番手以下': 5, '1番手': 4}.get(cat4, 0)
    if '先' in style or '好' in style:
        b += 4
    elif '差' in style:
        b += 3
    elif '追' in style:
        b += 1
    if c3 is not None and c4 is not None:
        if c4 < c3:
            b += 4
        elif abs(c4 - c3) <= 1:
            b += 3
    score += min(b, 20)

    # C
    c = 0
    if agari_rank == 1:
        c += 15
    elif agari_rank in [2, 3]:
        c += 12
    elif agari_rank in [4, 5]:
        c += 8
    elif agari_rank is not None and 6 <= agari_rank <= 9:
        c += 4
    if agari_rank is not None:
        if cat4 in ['2〜3番手', '4〜6番手'] and agari_rank <= 5:
            c += 3
        if cat4 in ['7〜10番手', '11番手以下'] and agari_rank <= 3:
            c += 3
    score += min(c, 15)

    # D
    d = 0
    if prev_dist is not None and cur_dist is not None:
        diff = cur_dist - prev_dist
        abs_diff = abs(diff)
        if abs_diff == 0:
            d += 6
        elif diff < 0 and abs_diff <= 200:
            d += 5
        elif diff > 0 and abs_diff <= 200:
            d += 4
        elif diff < 0 and abs_diff <= 400:
            d += 3
        elif diff > 0 and abs_diff <= 400:
            d += 2
        elif diff < 0:
            d += 1
        if 1400 <= cur_dist <= 2000:
            d += 4
        elif cur_dist >= 2200:
            d += 3
        elif cur_dist <= 1200:
            d += 2
    if prev_surface and cur_surface:
        if '芝' in prev_surface and '芝' in cur_surface:
            d += 5
        elif 'ダ' in prev_surface and 'ダ' in cur_surface:
            d += 4
        elif ('芝' in prev_surface and 'ダ' in cur_surface) or ('ダ' in prev_surface and '芝' in cur_surface):
            d += 1
    score += min(d, 15)

    # E
    prev_type = get_straight_type(row.get('前走場所'))
    cur_type = get_straight_type(row.get('場所'))
    if prev_type and cur_type:
        prev_good = rank is not None and rank <= 5
        good_agari = agari_rank is not None and agari_rank <= 3
        front = cat4 in ['1番手', '2〜3番手', '4〜6番手']
        back = cat4 in ['7〜10番手', '11番手以下']
        if '長直線' in prev_type and front and prev_good and '短直線' in cur_type:
            score += 10
        elif '短直線' in prev_type and back and good_agari and '長直線' in cur_type:
            score += 10
        elif '長直線' in prev_type and back and good_agari and '長直線' in cur_type:
            score += 8
        elif '短直線' in prev_type and front and prev_good and '短直線' in cur_type:
            score += 8
        elif prev_type == cur_type and prev_good:
            score += 6
        elif '長直線' in prev_type and back and '短直線' in cur_type:
            score += 3
        else:
            score += 2

    # F
    if prev_field is None or cur_field is None:
        score += 3
    else:
        diff = prev_field - cur_field
        if diff >= 4:
            score += 10
        elif 1 <= diff <= 3:
            score += 6
        elif diff == 0:
            score += 3
        elif -3 <= diff <= -1:
            score += 1

    # danger
    penalty = 0
    if cur_field is not None and cur_field >= 16:
        penalty -= 4
    if '逃' in style:
        penalty -= 5
    if c4 == 1:
        penalty -= 5
    if rank == 1 and c4 == 1:
        penalty -= 6
    if cur_dist is not None and 'ダ' in cur_surface and cur_dist <= 1400:
        penalty -= 4
    if prev_dist is not None and cur_dist is not None and cur_dist - prev_dist >= 500:
        penalty -= 5
    if agari_rank is not None and agari_rank >= 10:
        penalty -= 5
    if margin is not None:
        if margin >= 2.0:
            penalty -= 10
        elif margin >= 1.0:
            penalty -= 6
    if prev_surface and cur_surface and ((('芝' in prev_surface) and ('ダ' in cur_surface)) or (('ダ' in prev_surface) and ('芝' in cur_surface))):
        penalty -= 4

    final_score = score + max(penalty, -20)
    return round(max(0, min(100, final_score)))


def calc_trust_count(row):
    count = 0
    rank = to_int(row.get('前走着順'))
    margin = to_float(row.get('前走着差'))
    prev_field = to_int(row.get('前走頭数'))
    c4 = to_int(row.get('前走通過順4'))
    cat4 = get_corner_category(c4, prev_field)
    style = norm_text(row.get('前走脚質', ''))
    prev_dist = to_int(row.get('前走距離'))
    cur_dist = to_int(row.get('距離'))
    cur_surface = norm_text(row.get('芝ダ', ''))
    if rank in [2, 3]: count += 1
    if margin is not None and 0.1 <= margin <= 0.3: count += 1
    if cat4 in ['2〜3番手', '4〜6番手']: count += 1
    if '先' in style or '好' in style: count += 1
    if prev_dist is not None and cur_dist is not None and prev_dist == cur_dist: count += 1
    if '芝' in cur_surface: count += 1
    if cur_dist is not None and cur_dist >= 1600: count += 1
    return count


def trust_score_from_count(count):
    return {0: 40, 1: 50, 2: 60, 3: 70, 4: 80, 5: 90, 6: 96, 7: 100}.get(count, 40)


def calc_composite_score(row):
    prev_score = calc_prev_straight_logic_score(row)
    trust_count = calc_trust_count(row)
    trust_score = trust_score_from_count(trust_count)
    score = prev_score * 0.75 + trust_score * 0.25
    return round(max(0, min(100, score)))


def build_straight_results(target_df, min_score):
    df = normalize_target(target_df)
    df = df[df['R'].isin([7, 8, 9, 10, 11, 12])].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df['前走直線ロジック点'] = df.apply(calc_prev_straight_logic_score, axis=1)
    df['信頼条件一致数'] = df.apply(calc_trust_count, axis=1)
    df['複合スコア'] = df.apply(calc_composite_score, axis=1)
    df['信頼度'] = df['複合スコア']
    df['印'] = ''

    df['R_num'] = df['R'].map(to_int)
    df['馬番_num'] = df['馬番'].map(to_int)
    df = df.sort_values(['競馬場', 'R_num', '複合スコア', '馬番_num'], ascending=[True, True, False, True]).copy()

    for (_, _, _), g in df.groupby(['日付', '競馬場', 'R_num'], sort=False):
        cand = g[g['信頼度'] >= min_score].head(6)
        marks = ['◎', '○', '▲', '△', '△', '△']
        for idx, mark in zip(cand.index, marks):
            df.loc[idx, '印'] = mark

    detail_cols = ['日付', '競馬場', '芝ダ', '距離', 'R', 'レース名', '頭数', '馬番', '馬名', '前走直線ロジック点', '信頼条件一致数', '複合スコア', '信頼度', '印']
    detail_df = df[detail_cols].copy()

    rows = []
    for (_, _, _), g in df.groupby(['日付', '競馬場', 'R_num'], sort=False):
        main_df = g[g['印'] == '◎']
        if main_df.empty:
            continue
        main = main_df.iloc[0]
        opp = g[g['印'] == '○']
        ana = g[g['印'] == '▲']
        ren = g[g['印'] == '△']
        ren_nums = [str(int(x)) for x in ren['馬番'].tolist() if pd.notna(x)]
        rows.append({
            '日付': main['日付'],
            '競馬場': main['競馬場'],
            'R': int(main['R']),
            'レース名': main['レース名'],
            '馬番': int(main['馬番']) if pd.notna(main['馬番']) else '',
            '馬名': main['馬名'],
            '信頼度': int(main['信頼度']),
            '印': '◎',
            '対抗': str(int(opp.iloc[0]['馬番'])) if not opp.empty and pd.notna(opp.iloc[0]['馬番']) else '',
            '対抗馬名': opp.iloc[0]['馬名'] if not opp.empty else '',
            '単穴': str(int(ana.iloc[0]['馬番'])) if not ana.empty and pd.notna(ana.iloc[0]['馬番']) else '',
            '単穴馬名': ana.iloc[0]['馬名'] if not ana.empty else '',
            '連下': ren_nums[0] if len(ren_nums) > 0 else '',
            '連下馬名': ren.iloc[0]['馬名'] if len(ren_nums) > 0 else '',
            '他1': ren_nums[1] if len(ren_nums) > 1 else '',
            '他2': ren_nums[2] if len(ren_nums) > 2 else '',
            '相手表示': '',
        })
    composite_df = pd.DataFrame(rows)
    return detail_df, composite_df

# ---------------------------------------------------------
# 鉄板判定
# ---------------------------------------------------------
def detect_teppan_files():
    logic_path = APP_DIR / '鉄板血統_TOP5並列_修正版_最終ロジック辞書.csv'
    course_path = APP_DIR / '鉄板血統_コース別_採用保留除外判定.csv'
    if not logic_path.exists():
        # fallback
        cand = sorted(APP_DIR.glob('*TOP5並列*最終ロジック辞書*.csv'))
        if cand:
            logic_path = cand[0]
    if not course_path.exists():
        cand = sorted(APP_DIR.glob('*コース別*採用保留除外判定*.csv'))
        if cand:
            course_path = cand[0]
    return logic_path if logic_path.exists() else None, course_path if course_path.exists() else None


def read_any_csv(path):
    for enc in ['utf-8-sig', 'cp932', 'shift_jis', 'utf-8']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    raise ValueError(f'CSVを読めません: {path}')


def target_systems_list(rule):
    raw = norm_text(rule.get('最終対象系統', ''))
    if not raw:
        return []
    return [norm_text(x) for x in re.split(r'[・、,/／]+', raw) if norm_text(x)]


def get_condition_pairs(rule, max_n=8):
    pairs = []
    for i in range(1, max_n + 1):
        item = norm_text(rule.get(f'条件{i}項目', ''))
        content = norm_text(rule.get(f'条件{i}内容', ''))
        if item and content:
            pairs.append((item, content))
    return pairs


def match_rule_value(row, item, expected):
    item = norm_text(item)
    expected = norm_text(expected)
    if not item or not expected:
        return True

    item_map = {
        '芝・ダ': '芝ダ',
        '前芝・ダ': '前走芝ダ',
        '前芝ダ': '前走芝ダ',
        '前距離': '前走距離',
        '所属': '所属',
        '前走所属': '前走所属',
        '頭数': '頭数',
        '前走頭数': '前走頭数',
        '前走馬場状態': '前走馬場状態',
        '馬場状態': '馬場状態',
        '天気': '天気',
        '性別': '性別',
        '前走斤量': '前走斤量',
        '斤量': '斤量',
        '替': '替',
    }
    col = item_map.get(item, item)
    if col not in row.index:
        return False

    actual = row.get(col, '')
    # 数値条件
    if col in ['距離', '前走距離', '頭数', '前走頭数', '斤量', '前走斤量']:
        a = to_int(actual)
        e = to_int(expected)
        return a is not None and e is not None and a == e
    return norm_text(actual) == expected


def calc_teppan_rank(row):
    rank = to_int(row.get('前走着順'))
    margin = to_float(row.get('前走着差'))
    rank_ok = rank is not None and rank <= 5
    margin_ok = margin is not None and margin <= 0.5
    if rank_ok and margin_ok:
        return '超鉄板⭐️'
    if rank_ok or margin_ok:
        return '強鉄板⭐️'
    return '鉄板⭐️'


def teppan_flag(rank):
    if rank == '超鉄板⭐️':
        return '激'
    if rank in ['強鉄板⭐️', '鉄板⭐️']:
        return '熱'
    return ''


def build_teppan_results(target_df, use_statuses):
    logic_path, course_path = detect_teppan_files()
    if logic_path is None or course_path is None:
        return pd.DataFrame(), logic_path, course_path

    logic_df = read_any_csv(logic_path)
    course_df = read_any_csv(course_path)
    logic_df.columns = [norm_col(c) for c in logic_df.columns]
    course_df.columns = [norm_col(c) for c in course_df.columns]

    inp = normalize_target(target_df)
    inp = inp[inp['R'].isin([7, 8, 9, 10, 11, 12])].copy()
    if inp.empty:
        return pd.DataFrame(), logic_path, course_path

    for df in [inp, logic_df, course_df]:
        if '競馬場' not in df.columns and '場所' in df.columns:
            df['競馬場'] = df['場所']
        if '芝ダ' not in df.columns:
            df['芝ダ'] = ''
        if '距離' in df.columns:
            df['距離'] = df['距離'].map(to_int)
        df['競馬場'] = df['競馬場'].map(norm_text)
        df['芝ダ'] = df['芝ダ'].map(norm_text)

    course_use = course_df[course_df['判定'].map(norm_text).isin([norm_text(x) for x in use_statuses])].copy() if '判定' in course_df.columns else course_df.copy()

    results = []
    for _, horse in inp.iterrows():
        place = norm_text(horse.get('競馬場', ''))
        surface = norm_text(horse.get('芝ダ', ''))
        distance = to_int(horse.get('距離'))

        course_match = course_use[
            (course_use['競馬場'].map(norm_text) == place) &
            (course_use['芝ダ'].map(norm_text) == surface) &
            (course_use['距離'].map(to_int) == distance)
        ]
        if course_match.empty:
            continue

        logic_match = logic_df[
            (logic_df['競馬場'].map(norm_text) == place) &
            (logic_df['芝ダ'].map(norm_text) == surface) &
            (logic_df['距離'].map(to_int) == distance)
        ]
        if logic_match.empty:
            continue

        father_sys = norm_text(horse.get('父タイプ名', ''))
        mb_sys = norm_text(horse.get('母父タイプ名', ''))

        for _, rule in logic_match.iterrows():
            blood_type = norm_text(rule.get('血統区分', ''))
            systems = target_systems_list(rule)
            if blood_type == '父系':
                blood_hit = father_sys in systems
            elif blood_type == '母父系':
                blood_hit = mb_sys in systems
            else:
                blood_hit = father_sys in systems or mb_sys in systems
            if not blood_hit:
                continue

            cond_ok = True
            for item, content in get_condition_pairs(rule):
                if not match_rule_value(horse, item, content):
                    cond_ok = False
                    break
            if not cond_ok:
                continue

            rank_name = calc_teppan_rank(horse)
            results.append({
                '日付': horse.get('日付', ''),
                '競馬場': place,
                'R': int(horse.get('R')),
                'レース名': horse.get('レース名', ''),
                '馬番': int(horse.get('馬番')) if pd.notna(horse.get('馬番')) else '',
                '馬名': horse.get('馬名', ''),
                '鉄板ランク': rank_name,
                '鉄板印': teppan_flag(rank_name),
                '判定': course_match.iloc[0].get('判定', '採用'),
            })

    out = pd.DataFrame(results)
    if out.empty:
        return out, logic_path, course_path

    out['R_num'] = out['R'].map(to_int)
    out['馬番_num'] = out['馬番'].map(to_int)
    out['rank_pri'] = out['鉄板ランク'].map(lambda x: 1 if x == '超鉄板⭐️' else 2 if x == '強鉄板⭐️' else 3)
    out = out.sort_values(['競馬場', 'R_num', 'rank_pri', '馬番_num']).drop_duplicates(subset=['日付', '競馬場', 'R', '馬番', '馬名'], keep='first')
    out = out[['日付', '競馬場', 'R', 'レース名', '馬番', '馬名', '鉄板ランク', '鉄板印', '判定']]
    return out, logic_path, course_path


def merge_straight_teppan(straight_composite, teppan_result):
    base = straight_composite.copy() if not straight_composite.empty else pd.DataFrame()

    if not base.empty:
        base['鉄板印'] = ''
        base['鉄板ランク'] = ''
        if not teppan_result.empty:
            key_cols = ['日付', '競馬場', 'R', '馬番']
            tmp = teppan_result[key_cols + ['鉄板印', '鉄板ランク']].copy()
            base = base.merge(tmp, on=key_cols, how='left', suffixes=('', '_tp'))
            base['鉄板印'] = base['鉄板印_tp'].fillna('')
            base['鉄板ランク'] = base['鉄板ランク_tp'].fillna('')
            base = base.drop(columns=[c for c in ['鉄板印_tp', '鉄板ランク_tp'] if c in base.columns])

    # 直線に出ていない鉄板単独も追加
    if not teppan_result.empty:
        if base.empty:
            extra = teppan_result.copy()
        else:
            existing = set(zip(base['日付'], base['競馬場'], base['R'], base['馬番']))
            extra = teppan_result[~teppan_result.apply(lambda r: (r['日付'], r['競馬場'], r['R'], r['馬番']) in existing, axis=1)].copy()
        if not extra.empty:
            extra['信頼度'] = ''
            extra['印'] = '★'
            extra['対抗'] = ''
            extra['対抗馬名'] = ''
            extra['単穴'] = ''
            extra['単穴馬名'] = ''
            extra['連下'] = ''
            extra['連下馬名'] = ''
            extra['他1'] = ''
            extra['他2'] = ''
            extra['相手表示'] = ''
            base = pd.concat([base, extra], ignore_index=True, sort=False)

    if not base.empty:
        base['R_num'] = base['R'].map(to_int)
        base['馬番_num'] = base['馬番'].map(to_int)
        base = base.sort_values(['競馬場', 'R_num', '馬番_num']).drop(columns=['R_num', '馬番_num'])
    return base

# ---------------------------------------------------------
# HTMLプレビュー
# ---------------------------------------------------------
def render_html_with_teppan(display_df, image_date):
    cards_html = ''
    for _, r in display_df.iterrows():
        flag = norm_text(r.get('鉄板印', ''))
        flag_html = f"<span class='flag {flag}'>{esc(flag)}</span>" if flag else ''
        rows = []
        rows.append(f"<div class='line'><span>{esc(str(r.get('印', '◎')))}</span><span>{esc(str(r.get('馬番', '')))}</span><b>{esc(str(r.get('馬名', '')))}</b>{flag_html}</div>")
        if norm_text(r.get('対抗', '')):
            rows.append(f"<div class='line'><span>○</span><span>{esc(str(r.get('対抗', '')))}</span><b>{esc(str(r.get('対抗馬名', '')))}</b></div>")
        if norm_text(r.get('単穴', '')):
            rows.append(f"<div class='line'><span>▲</span><span>{esc(str(r.get('単穴', '')))}</span><b>{esc(str(r.get('単穴馬名', '')))}</b></div>")
        if norm_text(r.get('連下', '')):
            rows.append(f"<div class='line'><span>△</span><span>{esc(str(r.get('連下', '')))}</span><b>{esc(str(r.get('連下馬名', '')))}</b></div>")
        others = [norm_text(r.get('他1', '')), norm_text(r.get('他2', ''))]
        others = [x for x in others if x]
        if others:
            rows.append(f"<div class='line'><span>他</span><span></span><b>{esc(', '.join(others))}</b></div>")
        card = f"<div class='card'><div class='head'>{esc(str(r.get('競馬場', '')))} {esc(str(r.get('R', '')))}R</div><div class='body'>{''.join(rows)}</div></div>"
        cards_html += card

    html = f"""
    <html><head><meta charset='UTF-8'><style>
    body {{ margin:0; background:#06142a; font-family:'Noto Sans JP','Yu Gothic',sans-serif; }}
    .poster {{ width:1080px; margin:auto; background:#06142a; padding:32px; border:4px solid #d2a841; box-sizing:border-box; }}
    .top {{ height:140px; color:#e5bc4b; position:relative; }}
    .title {{ font-size:72px; font-weight:900; color:#f5efe0; }}
    .date {{ position:absolute; right:24px; top:10px; font-size:34px; color:#e5bc4b; }}
    .legend {{ position:absolute; right:24px; top:70px; font-size:24px; color:#f5efe0; }}
    .cards {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .card {{ background:#f6f0dd; border:2px solid #b9871e; border-radius:14px; overflow:hidden; }}
    .head {{ background:#0b2c59; color:#ffffff; font-size:34px; font-weight:900; text-align:center; padding:12px; }}
    .body {{ padding:14px 20px; }}
    .line {{ display:grid; grid-template-columns:40px 50px 1fr 48px; align-items:center; min-height:40px; border-bottom:1px solid #d5c7a0; font-size:22px; font-weight:800; gap:8px; }}
    .line:last-child {{ border-bottom:none; }}
    .flag {{ text-align:right; font-weight:900; }}
    .激 {{ color:#d8212d; }}
    .熱 {{ color:#c88d00; }}
    </style></head><body>
    <div class='poster'>
      <div class='top'>
        <div class='title'>本日の推奨馬</div>
        <div class='date'>{esc(image_date)}</div>
        <div class='legend'>激=超鉄板　熱=鉄板　印=直線ロジック</div>
      </div>
      <div class='cards'>{cards_html}</div>
    </div>
    </body></html>
    """
    return html

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title('第3段階：直線＋鉄板判定確認アプリ')
st.caption(f'バージョン: {APP_VERSION}')
st.write('TARGET読み込み → 7〜12R抽出 → 直線ロジック採点 → 鉄板判定（激/熱）まで確認します。消寄はまだ入れていません。')

uploaded = st.file_uploader('TARGET/JRA-VAN由来CSVを選択', type=['csv'])
min_score = st.selectbox('直線ロジックの最低表示基準', [75, 80, 85, 90], index=0)
use_statuses = st.multiselect('使用する鉄板コース判定', ['採用', '保留', '除外'], default=['採用'])
image_date = st.text_input('画像に表示する日付', value=datetime.now().strftime('%Y.%m.%d'))

if uploaded is not None:
    try:
        raw_df, encoding, read_mode = read_csv_smart(uploaded)
        straight_detail, straight_composite = build_straight_results(raw_df, min_score)
        teppan_result, logic_path, course_path = build_teppan_results(raw_df, use_statuses)
        display_df = merge_straight_teppan(straight_composite, teppan_result)

        st.success('CSVを読み込み、直線ロジック採点＋鉄板判定を行いました。')
        c1, c2, c3 = st.columns(3)
        c1.metric('読み込み方式', read_mode)
        c2.metric('文字コード', encoding)
        c3.metric('直線詳細頭数', len(straight_detail))
        c4, c5, c6 = st.columns(3)
        c4.metric('直線推奨レース数', len(straight_composite))
        c5.metric('鉄板該当頭数', len(teppan_result))
        c6.metric('表示件数', len(display_df))

        if logic_path is None or course_path is None:
            st.warning('鉄板辞書CSVまたはコース判定CSVが見つかりません。app.pyと同じ場所に配置してください。')
        else:
            st.info(f'鉄板辞書: {logic_path.name} / コース判定: {course_path.name}')

        st.subheader('直線 詳細ランキングCSV')
        st.dataframe(straight_detail, use_container_width=True, hide_index=True, height=320)
        st.download_button('直線 詳細ランキングCSVをダウンロード', straight_detail.to_csv(index=False, encoding='utf-8-sig'), file_name='straight_logic_detail_step3.csv', mime='text/csv', use_container_width=True)

        st.subheader('直線 複合アプリ用CSV')
        st.dataframe(straight_composite, use_container_width=True, hide_index=True, height=220)
        st.download_button('直線 複合アプリ用CSVをダウンロード', straight_composite.to_csv(index=False, encoding='utf-8-sig'), file_name='straight_for_composite_step3.csv', mime='text/csv', use_container_width=True)

        st.subheader('鉄板 複合アプリ用CSV')
        st.dataframe(teppan_result, use_container_width=True, hide_index=True, height=220)
        st.download_button('鉄板 複合アプリ用CSVをダウンロード', teppan_result.to_csv(index=False, encoding='utf-8-sig') if not teppan_result.empty else '', file_name='teppan_for_composite_step3.csv', mime='text/csv', use_container_width=True)

        st.subheader('簡易画像プレビュー')
        html = render_html_with_teppan(display_df, image_date)
        components.html(html, height=1000, scrolling=True)

    except Exception as e:
        st.error('処理中にエラーが出ました。')
        st.exception(e)
else:
    st.info('CSVファイルを選択してください。')

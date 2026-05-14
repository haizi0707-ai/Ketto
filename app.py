import io
import re
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title='統合 直線ロジック確認版', layout='wide')

HEADERLESS_COLS = [
    '日付','場所','場R','レース名','芝ダ','距離','馬番','馬名',
    '種牡馬','父タイプ名','母父名','母父タイプ名','性別','年齢','斤量','頭数',
    '前走馬場状態','前芝ダ','前距離','前走斤量','休み明け〜戦目','所属','調教師','騎手','前走騎手',
    '前走着順','前走着差','前走頭数','前走通過順1','前走通過順2','前走通過順3','前走通過順4',
    '前走上り3F順','前走脚質','前走場所','前走場所区分'
]

def norm_text(v):
    if pd.isna(v):
        return ''
    s = str(v).strip().replace('\u3000', ' ')
    s = re.sub(r'\s+', '', s)
    if s.endswith('.0'):
        s = s[:-2]
    return s

def norm_col(c):
    s = str(c).strip().replace('\u3000', '')
    s = s.replace('Ｒ', 'R').replace('芝・ダ', '芝ダ').replace('芝ダ・距離', '芝ダ距離')
    s = s.replace('～', '〜')
    return re.sub(r'\s+', '', s)

def looks_like_headerless_target(df):
    cols = [str(c).strip() for c in df.columns]
    if len(cols) < 8:
        return False
    date_like = bool(re.fullmatch(r'\d{3,8}', cols[0]))
    place_like = cols[1] in ['札','函','福','新','東','中','名','京','阪','小','札幌','函館','福島','新潟','東京','中山','中京','京都','阪神','小倉']
    r_like = bool(re.search(r'\d+', cols[2]))
    return date_like and place_like and r_like

def read_csv_smart(obj):
    encodings = ['utf-8-sig','utf-8','cp932','shift_jis']
    last_err = None
    for enc in encodings:
        try:
            if hasattr(obj, 'seek'):
                obj.seek(0)
                df = pd.read_csv(obj, encoding=enc)
                if looks_like_headerless_target(df):
                    obj.seek(0)
                    raw = pd.read_csv(obj, encoding=enc, header=None)
                    raw = raw.iloc[:, :len(HEADERLESS_COLS)]
                    raw.columns = HEADERLESS_COLS[:len(raw.columns)]
                    return raw
                return df
            df = pd.read_csv(io.StringIO(str(obj)), encoding=enc)
            if looks_like_headerless_target(df):
                raw = pd.read_csv(io.StringIO(str(obj)), encoding=enc, header=None)
                raw = raw.iloc[:, :len(HEADERLESS_COLS)]
                raw.columns = HEADERLESS_COLS[:len(raw.columns)]
                return raw
            return df
        except Exception as e:
            last_err = e
    raise last_err

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
        s = s.replace('秒','').replace('+','').replace('▲','').replace('△','').replace('◇','')
        m = re.search(r'-?\d+(?:\.\d+)?', s)
        return float(m.group(0)) if m else None
    except Exception:
        return None

def esc(s):
    s = str(s)
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace(chr(34),'&quot;').replace(chr(39),'&#39;')

def normalize_target(df):
    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]
    rename = {
        '場所':'場所','場':'場所','場R':'R','レース':'R','レース番号':'R',
        '馬番号':'馬番','芝ダ距離':'距離','レース名(クラス)':'レース名',
        '前馬場状態':'前走馬場状態','前走馬場':'前走馬場状態',
        '前距離':'前走距離','前走芝ダ':'前走芝ダ','前芝ダ':'前走芝ダ','前芝・ダ':'前走芝ダ',
        '前走着':'前走着順','前着順':'前走着順','前差':'前走着差',
        '前走上がり3F順':'前走上り3F順','前走上り順位':'前走上り3F順',
        '前走4角':'前走通過順4','前4角':'前走通過順4','前走3角':'前走通過順3','前3角':'前走通過順3','前頭数':'前走頭数'
    }
    for old, new in rename.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old:new})
    pmap = {'札':'札幌','函':'函館','福':'福島','新':'新潟','東':'東京','中':'中山','名':'中京','京':'京都','阪':'阪神','小':'小倉'}
    if '場所' in df.columns:
        df['場所'] = df['場所'].apply(lambda x: pmap.get(norm_text(x), norm_text(x)))
    else:
        df['場所'] = ''
    df['R'] = df['R'].apply(to_int) if 'R' in df.columns else None
    if '距離' in df.columns:
        raw = df['距離'].astype(str)
        if '芝ダ' not in df.columns:
            df['芝ダ'] = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
        else:
            miss = df['芝ダ'].map(norm_text).eq('')
            ext = raw.str.extract(r'([芝ダ])', expand=False).fillna('')
            df.loc[miss, '芝ダ'] = ext[miss]
        df['距離'] = raw.str.extract(r'(\d+)', expand=False).fillna('').apply(to_int)
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
        df['前走距離'] = raw.str.extract(r'(\d+)', expand=False).fillna('').apply(to_int)
    else:
        df['前走距離'] = None
        if '前走芝ダ' not in df.columns:
            df['前走芝ダ'] = ''
    for c in ['レース名','芝ダ','馬名','前走芝ダ','前走脚質','前走場所']:
        if c not in df.columns:
            df[c] = ''
        df[c] = df[c].map(norm_text)
    for c in ['頭数','馬番','前走頭数','前走着順','前走着差','前走通過順3','前走通過順4','前走上り3F順']:
        if c not in df.columns:
            df[c] = ''
    return df

def get_corner_category(pos, field_size):
    pos = to_int(pos)
    field_size = to_int(field_size)
    if pos is None:
        return ''
    if pos == 1:
        return '1番手'
    if field_size is None or field_size <= 0:
        if pos <= 3: return '2〜3番手'
        if pos <= 6: return '4〜6番手'
        if pos <= 10: return '7〜10番手'
        return '11番手以下'
    ratio = pos / field_size
    if pos <= 3 or ratio <= 0.20: return '2〜3番手'
    if pos <= 6 or ratio <= 0.40: return '4〜6番手'
    if pos <= 10 or ratio <= 0.70: return '7〜10番手'
    return '11番手以下'

def calc_prev_straight_score(row):
    score = 0
    rank = to_int(row.get('前走着順'))
    margin = to_float(row.get('前走着差'))
    if rank == 1: score += 18
    elif rank in [2,3]: score += 22
    elif rank in [4,5]: score += 14
    elif rank is not None and 6 <= rank <= 9: score += 7
    if margin is not None:
        if margin <= 0: score += 5
        elif 0.1 <= margin <= 0.3: score += 8
        elif 0.4 <= margin <= 0.5: score += 5
        elif 0.6 <= margin <= 0.9: score += 2
    cat4 = get_corner_category(row.get('前走通過順4'), row.get('前走頭数'))
    score += {'2〜3番手':12,'4〜6番手':14,'7〜10番手':8,'11番手以下':5,'1番手':4}.get(cat4,0)
    ag = to_int(row.get('前走上り3F順'))
    if ag == 1: score += 15
    elif ag in [2,3]: score += 12
    elif ag in [4,5]: score += 8
    elif ag is not None and 6 <= ag <= 9: score += 4
    prev_dist = to_int(row.get('前走距離'))
    cur_dist = to_int(row.get('距離'))
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
    prev_field = to_int(row.get('前走頭数'))
    cur_field = to_int(row.get('頭数'))
    if prev_field is None or cur_field is None: score += 3
    else:
        diff = prev_field - cur_field
        if diff >= 4: score += 10
        elif 1 <= diff <= 3: score += 6
        elif diff == 0: score += 3
        elif -3 <= diff <= -1: score += 1
    if cur_field is not None and cur_field >= 16: score -= 4
    if to_int(row.get('前走通過順4')) == 1: score -= 5
    if margin is not None and margin >= 1.0: score -= 6
    return round(max(0, min(100, score)))

def trust_count(row):
    cnt = 0
    rank = to_int(row.get('前走着順'))
    margin = to_float(row.get('前走着差'))
    cat4 = get_corner_category(row.get('前走通過順4'), row.get('前走頭数'))
    if rank in [2,3]: cnt += 1
    if margin is not None and 0.1 <= margin <= 0.3: cnt += 1
    if cat4 in ['2〜3番手','4〜6番手']: cnt += 1
    if to_int(row.get('前走距離')) == to_int(row.get('距離')): cnt += 1
    if '芝' in str(row.get('芝ダ','')): cnt += 1
    if to_int(row.get('距離')) is not None and to_int(row.get('距離')) >= 1600: cnt += 1
    return cnt

def calc_composite_score(row):
    prev = calc_prev_straight_score(row)
    tc = trust_count(row)
    trust_score = {0:40,1:50,2:60,3:70,4:80,5:90,6:96,7:100}.get(tc,40)
    return round(max(0, min(100, prev*0.75 + trust_score*0.25)))

def build_straight_results(target_df, min_score):
    df = normalize_target(target_df)
    df = df[df['R'].isin([7,8,9,10,11,12])].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df['前走直線ロジック点'] = df.apply(calc_prev_straight_score, axis=1)
    df['信頼条件一致数'] = df.apply(trust_count, axis=1)
    df['複合スコア'] = df.apply(calc_composite_score, axis=1)
    df['信頼度'] = df['複合スコア']
    df['R_num'] = df['R'].map(to_int)
    df['馬番_num'] = df['馬番'].map(to_int)
    df = df.sort_values(['場所','R_num','複合スコア','馬番_num'], ascending=[True,True,False,True]).copy()
    df['印'] = ''
    for _, g in df.groupby(['場所','R_num'], sort=False):
        cand = g[g['信頼度'] >= min_score].head(6)
        marks = ['◎','○','▲','△','△','△']
        for idx, mark in zip(cand.index, marks):
            df.loc[idx,'印'] = mark
    detail_cols = ['日付','場所','芝ダ','距離','R','レース名','頭数','馬番','馬名','前走直線ロジック点','信頼条件一致数','複合スコア','信頼度','印']
    for c in detail_cols:
        if c not in df.columns: df[c] = ''
    detail = df[detail_cols].copy()
    rows = []
    for _, g in df.groupby(['日付','場所','R_num'], sort=False):
        main_df = g[g['印']=='◎']
        if main_df.empty: continue
        main = main_df.iloc[0]
        opp = g[g['印']=='○']; ana = g[g['印']=='▲']; ren = g[g['印']=='△']
        taikou = str(int(opp.iloc[0]['馬番'])) if not opp.empty and pd.notna(opp.iloc[0]['馬番']) else ''
        tanketsu = str(int(ana.iloc[0]['馬番'])) if not ana.empty and pd.notna(ana.iloc[0]['馬番']) else ''
        ren_nums = [str(int(x)) for x in ren['馬番'].tolist() if pd.notna(x)]
        rows.append({'日付': main['日付'], '競馬場': main['場所'], 'R': int(main['R']), 'レース名': main['レース名'],
            '馬番': int(main['馬番']) if pd.notna(main['馬番']) else '', '馬名': main['馬名'], '信頼度': int(main['信頼度']), '印': '◎',
            '対抗': taikou, '対抗馬名': opp.iloc[0]['馬名'] if not opp.empty else '',
            '単穴': tanketsu, '単穴馬名': ana.iloc[0]['馬名'] if not ana.empty else '',
            '連下': ren_nums[0] if len(ren_nums)>0 else '', '連下馬名': ren.iloc[0]['馬名'] if len(ren_nums)>0 else '',
            '他1': ren_nums[1] if len(ren_nums)>1 else '', '他2': ren_nums[2] if len(ren_nums)>2 else '', '相手表示': ''})
    return detail, pd.DataFrame(rows)

def render_html(straight_composite, image_date):
    card_html = ''
    for _, r in straight_composite.iterrows():
        lines = [(r.get('印','◎'), r.get('馬番',''), r.get('馬名',''))]
        for mark, ncol, nmcol in [('○','対抗','対抗馬名'),('▲','単穴','単穴馬名'),('△','連下','連下馬名')]:
            if norm_text(r.get(ncol,'')):
                lines.append((mark, r.get(ncol,''), r.get(nmcol,'')))
        others = [norm_text(r.get('他1','')), norm_text(r.get('他2',''))]
        others = [x for x in others if x]
        if others: lines.append(('他','',', '.join(others)))
        rows = ''.join([f'<div class="line"><span>{esc(m)}</span><span>{esc(n)}</span><b>{esc(name)}</b></div>' for m,n,name in lines])
        card_html += f'<div class="card"><div class="head">{esc(r.get("競馬場",""))} {esc(r.get("R",""))}R</div><div class="body">{rows}</div></div>'
    return f'<html><head><meta charset="UTF-8"><style>body{{margin:0;background:#06142a;color:#111;font-family:"Noto Sans JP","Yu Gothic",sans-serif;}}.poster{{width:1080px;margin:auto;background:#06142a;padding:32px;border:4px solid #d2a841;}}.top{{height:140px;color:#e5bc4b;position:relative;}}.title{{font-size:72px;font-weight:900;}}.date{{position:absolute;right:24px;top:10px;font-size:34px;}}.cards{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}.card{{background:#f6f0dd;border:2px solid #b9871e;border-radius:14px;overflow:hidden;}}.head{{background:#0b2c59;color:white;font-size:34px;font-weight:900;text-align:center;padding:12px;}}.body{{padding:14px 20px;}}.line{{display:grid;grid-template-columns:40px 50px 1fr;align-items:center;height:40px;border-bottom:1px solid #d5c7a0;font-size:22px;font-weight:800;}}.line:last-child{{border-bottom:none;}}</style></head><body><div class="poster"><div class="top"><div class="title">本日の推奨馬</div><div class="date">{esc(image_date)}</div></div><div class="cards">{card_html}</div></div></body></html>'

st.title('統合 直線ロジック×鉄板⭐️×消寄アプリ')
st.caption('基準75以上まで下げて、直線ロジックの表示確認を行う版です。画像は1枚で見える簡易版です。')
with st.expander('TARGETから抜く推奨項目', expanded=True):
    st.text('日付 / 場所 / 場R / レース名(クラス) / 芝ダ・距離 / 馬番 / 馬名 / 種牡馬 / 父タイプ名 / 母父名 / 母父タイプ名 / 性齢 / 斤量 / 頭数 / 前馬場状態 / 前距離 / 前走斤量 / 休み明け〜戦目 / 調教師 / 騎手 / 前走騎手 / 前走着順 / 前走着差 / 前走頭数 / 前走通過順3 / 前走通過順4 / 前走上り3F順 / 前走上り3F / 前走脚質 / 前走場所')
mode = st.radio('TARGET CSV入力方法', ['ファイル読み込み', '貼り付け'], horizontal=True)
if mode == 'ファイル読み込み':
    uploaded = st.file_uploader('TARGET/JRA-VAN由来CSV', type=['csv'])
    pasted = ''
else:
    uploaded = None
    pasted = st.text_area('TARGET/JRA-VAN由来CSVを貼り付け', height=300)
col1, col2 = st.columns(2)
with col1:
    image_date = st.text_input('画像に表示する日付', value=datetime.now().strftime('%Y.%m.%d'))
with col2:
    min_score = st.selectbox('直線ロジックの最低表示基準', [75,80,85,90], index=0)
if st.button('統合処理を実行', type='primary', use_container_width=True):
    try:
        if mode == 'ファイル読み込み':
            if uploaded is None:
                st.warning('CSVファイルを選択してください。')
                st.stop()
            target_df = read_csv_smart(uploaded)
        else:
            if not pasted.strip():
                st.warning('CSV本文を貼り付けてください。')
                st.stop()
            target_df = read_csv_smart(io.StringIO(pasted))
        straight_detail, straight_composite = build_straight_results(target_df, min_score)
        if straight_composite.empty:
            st.warning(f'直線ロジック基準{min_score}以上の馬がいませんでした。詳細CSVで点数を確認してください。')
        else:
            st.success(f'直線詳細 {len(straight_detail)}頭 / 直線推奨 {len(straight_composite)}レース を作成しました。')
        st.subheader('① 直線アプリ用・詳細ランキングCSV')
        st.dataframe(straight_detail, use_container_width=True, hide_index=True)
        st.download_button('直線詳細CSVをダウンロード', straight_detail.to_csv(index=False, encoding='utf-8-sig'), file_name='straight_logic_detail.csv', mime='text/csv', use_container_width=True)
        st.subheader('② 直線 複合アプリ用CSV')
        st.dataframe(straight_composite, use_container_width=True, hide_index=True)
        st.download_button('直線複合CSVをダウンロード', straight_composite.to_csv(index=False, encoding='utf-8-sig'), file_name='straight_for_composite.csv', mime='text/csv', use_container_width=True)
        st.subheader('③ SNS画像プレビュー')
        html = render_html(straight_composite, image_date)
        components.html(html, height=1000, scrolling=True)
        st.download_button('HTMLをダウンロード', data=html.encode('utf-8'), file_name='integrated_composite_ticket.html', mime='text/html', use_container_width=True)
    except Exception as e:
        st.error('処理中にエラーが出ました。')
        st.exception(e)

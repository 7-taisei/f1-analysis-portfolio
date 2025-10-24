import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- アプリのタイトル ---
st.title("F1 Data Analysis Dashboard 🏎️")

# --- サイドバー (フィルター) ---
st.sidebar.header("Filter Options ⚙️")

# 1. 年の選択
supported_years = [2025, 2024, 2023, 2022]
selected_year = st.sidebar.selectbox("Select Year:", supported_years)

# 2. ★★★ 新機能 ★★★
# 選択された年に基づいて、動的にレーススケジュール（正式名称）を取得
@st.cache_data
def get_race_schedule(year):
    try:
        # FastF1のイベントスケジュール機能を使用 (テストを除外)
        schedule = ff1.get_event_schedule(year, include_testing=False)
        # 'OfficialEventName' (例: 'Japanese Grand Prix') をリストとして返す
        race_names = schedule['OfficialEventName'].tolist()
        return race_names
    except Exception as e:
        st.error(f"Error fetching {year} schedule: {e}")
        return []

# スケジュールを取得
race_names_list = get_race_schedule(selected_year)

# 3. レースの選択 (動的に取得したリストを使用)
if race_names_list: # リストが空でないことを確認
    default_race_name = 'Japanese Grand Prix' if 'Japanese Grand Prix' in race_names_list else race_names_list[0]
    selected_race = st.sidebar.selectbox(
        "Select Race:", 
        race_names_list,
        index=race_names_list.index(default_race_name)
    )
else:
    st.sidebar.error(f"{selected_year}年のレースデータが見つかりません。")
    selected_race = None # レースが選択されていない状態にする


# --- データ取得 ---
@st.cache_data
def load_session_data(year, race_name, session_type):
    if not race_name: # レースが選択されていない場合は何もしない
        return None
    try:
        # FastF1は正式名称 (selected_race) を認識できる
        session = ff1.get_session(year, race_name, session_type)
        session.load(laps=True, telemetry=False, weather=False)
        laps = session.laps
        return laps
    except Exception as e:
        st.error(f"データ取得エラー: {year}年の {race_name} は存在しないか、データにアクセスできません。")
        st.error(e)
        return None

# --- メイン処理 ---
# 選択された年とレースのデータを読み込む
laps = load_session_data(selected_year, selected_race, 'R')

if laps is not None and not laps.empty:
    
    # 改善点: .pick_accurate() で分析に不要なラップを自動除外
    laps_cleaned = laps.pick_accurate()
    
    if laps_cleaned.empty:
        st.warning("分析可能なクリーンラップデータがありません。")
    else:
        # LapTimeを秒（数値）に変換
        laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
        
        # ドライバーリストの取得
        drivers = laps_cleaned['Driver'].unique()
        drivers.sort()
        
        # ドライバーの選択 (リストが取得できてから表示)
        default_driver = 'TSU' if 'TSU' in drivers else drivers[0]
        selected_driver = st.sidebar.selectbox(
            "Select Driver:", 
            drivers, 
            index=list(drivers).index(default_driver)
        )

        # メイン画面のヘッダーを動的に更新
        st.header(f"{selected_year} {selected_race} - {selected_driver} Lap Time Analysis")

        # 選択されたドライバーのデータを最終抽出
        driver_laps_final = laps_cleaned.pick_driver(selected_driver)

        # グラフ作成
        if driver_laps_final.empty:
            st.warning(f"{selected_driver} は、このレースで分析可能なラップデータがありません。")
        else:
            fig = px.scatter(driver_laps_final, 
                             x='LapNumber',
                             y='LapTimeSeconds',
                             color='Compound',
                             hover_data=['Stint', 'TyreLife'])

            fig.update_layout(title=f"{selected_driver} - Lap Times",
                              xaxis_title="Lap Number",
                              yaxis_title="Lap Time (Seconds)")

            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("サイドバーで分析したい「年」と「レース」を選択してください。")
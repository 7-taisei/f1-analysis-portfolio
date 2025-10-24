import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- タイヤ色の定義 ---
TYRE_COLORS = {
    'SOFT': '#dc143c', 'MEDIUM': '#ffd700', 'HARD': '#f8f8ff',
    'INTERMEDIATE': '#4CAF50', 'WET': '#0D47A1' # 雨用タイヤも追加
}

# --- アプリのタイトル ---
st.title("F1 Data Analysis Dashboard 🏎️")

# --- サイドバー (フィルター) ---
st.sidebar.header("Filter Options ⚙️")

# 1. 年の選択
supported_years = [2024, 2023, 2022]
selected_year = st.sidebar.selectbox("Select Year:", supported_years)

# 2. レーススケジュールの動的取得
@st.cache_data
def get_race_schedule(year):
    try:
        schedule = ff1.get_event_schedule(year, include_testing=False)
        # 正式名称 (OfficialEventName) を返す
        race_names = schedule['OfficialEventName'].tolist()
        return race_names
    except Exception as e:
        st.sidebar.error(f"Error fetching {year} schedule: {e}")
        return []

race_names_list = get_race_schedule(selected_year)
if not race_names_list:
    st.sidebar.error(f"{selected_year}年のレースデータが見つかりません。")
    selected_race = None
else:
    default_race_name = 'Japanese Grand Prix' if 'Japanese Grand Prix' in race_names_list else race_names_list[0]
    selected_race = st.sidebar.selectbox(
        "Select Race:", 
        race_names_list,
        index=race_names_list.index(default_race_name)
    )

# 3. ★★★ 新機能 ★★★ セッションの動的取得
@st.cache_data
def get_event_sessions(year, race_name):
    if not race_name:
        return []
    try:
        # get_event を使ってGPの詳細情報を取得
        event = ff1.get_event(year, race_name)
        # セッション名 ('Practice 1', 'Qualifying', 'Race', 'Sprint'など) のリストを返す
        # .iloc[1:6] は時々ある'Practice 0'などを除外するためのおまじない
        sessions = event.sessions.iloc[1:6]['name'].tolist() 
        return sessions
    except Exception as e:
        st.sidebar.error(f"Error fetching sessions for {race_name}: {e}")
        return []

session_names_list = get_event_sessions(selected_year, selected_race)
if not session_names_list:
    st.sidebar.warning("このGPのセッション情報が見つかりません。")
    selected_session = None
else:
    # デフォルトで 'Race' を選択 (もし 'Race' がなければリストの最後を選択)
    default_session = 'Race' if 'Race' in session_names_list else session_names_list[-1]
    selected_session = st.sidebar.selectbox(
        "Select Session:",
        session_names_list,
        index=session_names_list.index(default_session)
    )

# --- データ取得 ---
@st.cache_data
def load_session_data(year, race_name, session_name):
    if not all([year, race_name, session_name]):
        return None
    try:
        session = ff1.get_session(year, race_name, session_name)
        # 必要なデータを全て読み込む
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        laps = session.laps
        return laps
    except Exception as e:
        st.error(f"データ取得エラー: {year} {race_name} '{session_name}' のデータにアクセスできません。")
        st.error(e)
        return None

# --- メイン処理 ---
laps = load_session_data(selected_year, selected_race, selected_session)

if laps is None or laps.empty:
    st.info("サイドバーで分析したい「年」「レース」「セッション」を選択してください。")
else:
    # 目的のセッション名を表示
    st.header(f"{selected_year} {selected_race} - {selected_session}")
    
    # タイムを秒に変換（グラフ作成の前に一度だけ実行）
    try:
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
    except Exception as e:
        st.warning(f"LapTimeSecondsへの変換中にエラー: {e}")

    # ★★★ 分析ロジックの分岐 ★★★
    
    # セッションが決勝 (Race) または スプリント (Sprint) の場合
    if selected_session in ['Race', 'Sprint']:
        laps_cleaned = laps.pick_accurate() # ピット等を除外
        if laps_cleaned.empty:
            st.warning("分析可能なクリーンラップデータがありません。")
        else:
            # タブを作成
            tab1, tab2 = st.tabs(["📊 Driver Lap Time Analysis", "📈 Tyre Degradation Comparison"])
            
            # タブ1: 個別ドライバー分析
            with tab1:
                drivers = laps_cleaned['Driver'].unique()
                drivers.sort()
                default_driver = 'TSU' if 'TSU' in drivers else drivers[0]
                selected_driver = st.sidebar.selectbox(
                    "Select Driver (for Tab 1):", drivers, index=list(drivers).index(default_driver)
                )
                st.subheader(f"{selected_driver} Lap Time Analysis")
                driver_laps_final = laps_cleaned.pick_driver(selected_driver)

                if not driver_laps_final.empty:
                    fig_driver = px.scatter(driver_laps_final, x='LapNumber', y='LapTimeSeconds', color='Compound',
                                         color_discrete_map=TYRE_COLORS, hover_data=['Stint', 'TyreLife'])
                    fig_driver.update_layout(title=f"{selected_driver} - Lap Times by Lap Number",
                                          xaxis_title="Lap Number", yaxis_title="Lap Time (Seconds)")
                    st.plotly_chart(fig_driver, use_container_width=True)
                else:
                    st.warning(f"{selected_driver}の分析可能なラップがありません。")
            
            # タブ2: タイヤ戦略比較
            with tab2:
                st.subheader("Tyre Degradation Comparison (All Drivers)")
                fig_tyre = px.scatter(laps_cleaned, x='TyreLife', y='LapTimeSeconds', color='Compound',
                                   color_discrete_map=TYRE_COLORS, hover_data=['Driver', 'LapNumber']) 
                fig_tyre.update_layout(title="Lap Time vs. Tyre Life (All Drivers)",
                                    xaxis_title="Tyre Life (Laps)", yaxis_title="Lap Time (Seconds)")
                st.plotly_chart(fig_tyre, use_container_width=True)

    # セッションが予選 (Qualifying) または 練習走行 (Practice) の場合
    else:
        st.info("予選・練習走行セッションです。全ドライバーの最速ラップを表示します。")
        
        # ★★★ 予選・練習用の新機能 ★★★
        try:
            fastest_laps = laps.pick_fastest()
            # 必要な情報だけを抽出
            fastest_laps_summary = fastest_laps[['Driver', 'LapTime', 'Compound', 'TyreLife', 'Stint']]
            
            # streamlitのデータフレーム機能で表を表示
            st.dataframe(fastest_laps_summary.set_index('Driver').sort_values('LapTime'), use_container_width=True)
            
            # 最速ラップのタイヤ分布を円グラフで表示
            st.subheader("Fastest Lap Tyre Compound Distribution")
            fig_pie = px.pie(fastest_laps_summary, names='Compound', 
                             color='Compound', color_discrete_map=TYRE_COLORS,
                             title="Tyre Compounds used for Fastest Laps")
            st.plotly_chart(fig_pie, use_container_width=True)

        except Exception as e:
            st.error(f"最速ラップの分析中にエラー: {e}")
            st.error("このセッションでは最速ラップデータを取得できない可能性があります。")
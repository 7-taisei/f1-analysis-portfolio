import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- タイヤ色の定義 ---
TYRE_COLORS = {
    'SOFT': '#dc143c', 'MEDIUM': '#ffd700', 'HARD': '#f8f8ff',
    'INTERMEDIATE': '#4CAF50', 'WET': '#0D47A1'
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
        return schedule
    except Exception as e:
        st.sidebar.error(f"Error fetching {year} schedule: {e}")
        return pd.DataFrame()

schedule_df = get_race_schedule(selected_year)

if schedule_df.empty:
    st.sidebar.error(f"{selected_year}年のレースデータが見つかりません。")
    selected_race = None
    selected_round = None
else:
    race_names_list = schedule_df['OfficialEventName'].tolist()
    default_race_name = 'Japanese Grand Prix' if 'Japanese Grand Prix' in race_names_list else race_names_list[0]
    
    selected_race = st.sidebar.selectbox(
        "Select Race:", 
        race_names_list,
        index=race_names_list.index(default_race_name)
    )
    
    selected_round = schedule_df.loc[schedule_df['OfficialEventName'] == selected_race, 'RoundNumber'].iloc[0]


# 3. ★★★ 最終修正 ★★★ セッションの動的取得
@st.cache_data
def get_event_sessions(year, round_number):
    if round_number is None:
        return []
    
    try:
        rn_int = int(round_number)
    except (ValueError, TypeError):
        st.sidebar.error(f"ラウンド番号 '{round_number}' を数値に変換できません。")
        return []
        
    try:
        event = ff1.get_event(year, rn_int) 
        
        # ★★★ ここが新しいロジック ★★★
        # 'Session1'～'Session5' のキーをループし、その「値」（セッション名）を取得する
        session_keys = ['Session1', 'Session2', 'Session3', 'Session4', 'Session5']
        sessions_from_event = []
        for key in session_keys:
            # event[key] は 'Practice 1' などのセッション名を返す
            session_name = event[key] 
            if session_name: # (セッションが存在する場合)
                sessions_from_event.append(session_name)
        
        # 取得したセッション名を定義済みの順序でソートする
        session_order = {
            'Practice 1': 1, 'Practice 2': 2, 'Practice 3': 3,
            'Sprint Shootout': 4, 'Qualifying': 5,
            'Sprint': 6, 'Race': 7,
            # (短縮名も念のため残す)
            'FP1': 1, 'FP2': 2, 'FP3': 3, 
            'SQ': 4, 'Q': 5, 'S': 6, 'R': 7 
        }
        
        sessions_sorted = sorted(
            [s for s in sessions_from_event if s in session_order],
            key=lambda s: session_order[s]
        )
        
        return sessions_sorted

    except Exception as e:
        st.sidebar.warning(f"セッション取得エラー (Year: {year}, Round: {rn_int}): {e}")
        return []

# 'selected_round' を使って関数を呼び出す
session_names_list = get_event_sessions(selected_year, selected_round)

if not session_names_list:
    st.sidebar.warning("このGPのセッション情報が見つかりません。")
    selected_session = None
else:
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
        # get_session は 'OfficialEventName' (race_name) でも 'Practice 1' (session_name) でも動作する
        session = ff1.get_session(year, race_name, session_name)
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        laps = session.laps
        return laps
    except Exception as e:
        st.error(f"データ取得エラー: {year} {race_name} '{session_name}' のデータにアクセスできません。")
        st.error(f"詳細: {e}")
        return None

# --- メイン処理 ---
laps = load_session_data(selected_year, selected_race, selected_session)

if laps is None or laps.empty:
    st.info("サイドバーで分析したい「年」「レース」「セッション」を選択してください。")
else:
    st.header(f"{selected_year} {selected_race} - {selected_session}")
    
    try:
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
    except Exception as e:
        st.warning(f"LapTimeSecondsへの変換中にエラー: {e}")

    # --- 分析ロジックの分岐 ---
    
    # セッション名が 'Race' または 'Sprint' の場合
    if selected_session in ['Race', 'Sprint', 'S', 'R']:
        laps_cleaned = laps.pick_accurate() 
        if laps_cleaned.empty:
            st.warning("分析可能なクリーンラップデータがありません。")
        else:
            tab1, tab2 = st.tabs(["📊 Driver Lap Time Analysis", "📈 Tyre Degradation Comparison"])
            
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
            
            with tab2:
                st.subheader("Tyre Degradation Comparison (All Drivers)")
                fig_tyre = px.scatter(laps_cleaned, x='TyreLife', y='LapTimeSeconds', color='Compound',
                                   color_discrete_map=TYRE_COLORS, hover_data=['Driver', 'LapNumber']) 
                fig_tyre.update_layout(title="Lap Time vs. Tyre Life (All Drivers)",
                                    xaxis_title="Tyre Life (Laps)", yaxis_title="Lap Time (Seconds)")
                st.plotly_chart(fig_tyre, use_container_width=True)

    # 予選・練習走行、またはその他のセッションの場合
    else: 
        st.info("予選・練習走行セッションです。全ドライバーの最速ラップを表示します。")
        
        try:
            fastest_laps = laps.pick_fastest()
            fastest_laps_summary = fastest_laps[['Driver', 'LapTime', 'Compound', 'TyreLife', 'Stint']]
            
            st.dataframe(fastest_laps_summary.set_index('Driver').sort_values('LapTime'), use_container_width=True)
            
            st.subheader("Fastest Lap Tyre Compound Distribution")
            
            fig_pie = px.pie(fastest_laps_summary, names='Compound', 
                             color='Compound',
                             color_discrete_map=TYRE_COLORS,
                             title="Tyre Compounds used for Fastest Laps")
            st.plotly_chart(fig_pie, use_container_width=True)

        except Exception as e:
            st.error(f"最速ラップの分析中にエラー: {e}")
            st.error("このセッションでは最速ラップデータを取得できない可能性があります。")
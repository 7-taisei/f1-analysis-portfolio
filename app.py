import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- ★★★ 新機能 ★★★ タイヤ色の定義 ---
# FastF1のデータ（'SOFT', 'MEDIUM', 'HARD'）に対応するカラーコード
TYRE_COLORS = {
    'SOFT': '#dc143c',    # (Red)
    'MEDIUM': '#ffd700',  # (Yellow)
    'HARD': '#f8f8ff'     # (White/GhostWhite)
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
        race_names = schedule['OfficialEventName'].tolist()
        return race_names
    except Exception as e:
        st.sidebar.error(f"Error fetching {year} schedule: {e}")
        return []

race_names_list = get_race_schedule(selected_year)

# 3. レースの選択
if race_names_list:
    default_race_name = 'Japanese Grand Prix' if 'Japanese Grand Prix' in race_names_list else race_names_list[0]
    selected_race = st.sidebar.selectbox(
        "Select Race:", 
        race_names_list,
        index=race_names_list.index(default_race_name)
    )
else:
    st.sidebar.error(f"{selected_year}年のレースデータが見つかりません。")
    selected_race = None

# --- データ取得 ---
@st.cache_data
def load_session_data(year, race_name, session_type):
    if not race_name:
        return None
    try:
        session = ff1.get_session(year, race_name, session_type)
        session.load(laps=True, telemetry=False, weather=False)
        laps = session.laps
        return laps
    except Exception as e:
        st.error(f"データ取得エラー: {year}年の {race_name} はデータにアクセスできません。")
        st.error(e)
        return None

# --- メイン処理 ---
laps = load_session_data(selected_year, selected_race, 'R')

if laps is not None and not laps.empty:
    
    laps_cleaned = laps.pick_accurate()
    
    if laps_cleaned.empty:
        st.warning("分析可能なクリーンラップデータがありません。")
    else:
        laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
        
        # --- タブの作成 ---
        tab1, tab2 = st.tabs(["📊 Driver Lap Time Analysis (個別分析)", "📈 Tyre Degradation Comparison (タイヤ戦略比較)"])

        # --- タブ1: 個別ドライバー分析 ---
        with tab1:
            st.header(f"{selected_year} {selected_race}")
            
            drivers = laps_cleaned['Driver'].unique()
            drivers.sort()
            
            default_driver = 'TSU' if 'TSU' in drivers else drivers[0]
            selected_driver = st.sidebar.selectbox(
                "Select Driver (for Tab 1):",
                drivers, 
                index=list(drivers).index(default_driver)
            )

            st.subheader(f"{selected_driver} Lap Time Analysis")
            
            driver_laps_final = laps_cleaned.pick_driver(selected_driver)

            if driver_laps_final.empty:
                st.warning(f"{selected_driver} は、このレースで分析可能なラップデータがありません。")
            else:
                # ★★★ 変更点1 ★★★
                fig_driver = px.scatter(driver_laps_final, 
                                     x='LapNumber',
                                     y='LapTimeSeconds',
                                     color='Compound',
                                     color_discrete_map=TYRE_COLORS, # 色の指定を追加
                                     hover_data=['Stint', 'TyreLife'])
                fig_driver.update_layout(title=f"{selected_driver} - Lap Times by Lap Number",
                                      xaxis_title="Lap Number",
                                      yaxis_title="Lap Time (Seconds)")
                st.plotly_chart(fig_driver, use_container_width=True)

        # --- タブ2: タイヤ戦略比較 ---
        with tab2:
            st.header(f"{selected_year} {selected_race} - Tyre Degradation Comparison")
            st.info("全ドライバーのクリーンラップを、タイヤの年齢（TyreLife）順にプロットしています。")

            if laps_cleaned.empty:
                st.warning("分析データがありません。")
            else:
                # ★★★ 変更点2 ★★★
                fig_tyre = px.scatter(laps_cleaned, 
                                   x='TyreLife',
                                   y='LapTimeSeconds',
                                   color='Compound',
                                   color_discrete_map=TYRE_COLORS, # 色の指定を追加
                                   hover_data=['Driver', 'LapNumber']) 
                
                fig_tyre.update_layout(title="Lap Time vs. Tyre Life (All Drivers)",
                                    xaxis_title="Tyre Life (Laps)",
                                    yaxis_title="Lap Time (Seconds)")
                
                st.plotly_chart(fig_tyre, use_container_width=True)

else:
    st.info("サイドバーで分析したい「年」と「レース」を選択してください。")
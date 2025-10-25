import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- ★★★ 修正点 ★★★ タイヤ色の定義 ---
TYRE_COLORS = {
    'SOFT': '#dc143c',    # (Red)
    'MEDIUM': '#ffd700',  # (Yellow)
    'HARD': '#66d6fb',    # (Light Blue) <- 変更
    'INTERMEDIATE': '#4CAF50', # (Green)
    'WET': '#0D47A1'          # (Blue)
}

# --- アプリのタイトル ---
st.title("F1 Data Analysis Dashboard 🏎️")

# --- サイドバー (フィルター) ---
st.sidebar.header("Filter Options ⚙️")

# (年の選択)
supported_years = [2024, 2023, 2022]
selected_year = st.sidebar.selectbox("Select Year:", supported_years)

# (レーススケジュールの動的取得)
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
    selected_race = st.sidebar.selectbox("Select Race:", race_names_list, index=race_names_list.index(default_race_name))
    selected_round = schedule_df.loc[schedule_df['OfficialEventName'] == selected_race, 'RoundNumber'].iloc[0]

# (セッションの動的取得)
@st.cache_data
def get_event_sessions(year, round_number):
    if round_number is None: return []
    try: rn_int = int(round_number)
    except (ValueError, TypeError): return []
    try:
        event = ff1.get_event(year, rn_int) 
        session_keys = ['Session1', 'Session2', 'Session3', 'Session4', 'Session5']
        sessions_from_event = [event[key] for key in session_keys if event[key]]
        session_order = {'Practice 1': 1, 'Practice 2': 2, 'Practice 3': 3, 'Sprint Shootout': 4, 'Sprint Qualifying': 4.5, 'Qualifying': 5, 'Sprint': 6, 'Race': 7, 'FP1': 1, 'FP2': 2, 'FP3': 3, 'SQ': 4, 'Q': 5, 'S': 6, 'R': 7}
        sessions_sorted = sorted([s for s in sessions_from_event if s in session_order], key=lambda s: session_order[s])
        return sessions_sorted
    except Exception as e:
        st.sidebar.warning(f"セッション取得エラー (Y: {year}, R: {rn_int}): {e}")
        return []

session_names_list = get_event_sessions(selected_year, selected_round)
if not session_names_list:
    st.sidebar.warning("このGPのセッション情報が見つかりません。")
    selected_session = None
else:
    default_session = 'Race' if 'Race' in session_names_list else session_names_list[-1]
    selected_session = st.sidebar.selectbox("Select Session:", session_names_list, index=session_names_list.index(default_session))

# (データ取得)
@st.cache_data
def load_session_data(year, race_name, session_name):
    if not all([year, race_name, session_name]): return None, None
    try:
        session = ff1.get_session(year, race_name, session_name)
        session.load()
        return session.laps, session.results
    except Exception as e:
        st.error(f"データ取得エラー: {year} {race_name} '{session_name}' - {e}")
        return None, None

# --- メイン処理 ---
laps, results = load_session_data(selected_year, selected_race, selected_session)

# --- タブの定義 ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Session Analysis (セッション分析)", 
    "📈 Tyre Degradation (タイヤ比較)", 
    "🗺️ Pit Strategy (ピット戦略)",
    "⚔️ H2H Pace Comparison (H2H)"
])


# --- タブ1 (セッション分析) ---
with tab1:
    st.header(f"{selected_year} {selected_race} - {selected_session}")
    if laps is None or laps.empty:
        st.info("サイドバーで分析したい「年」「レース」「セッション」を選択してください。")
    elif selected_session in ['Race', 'Sprint', 'S', 'R']:
        st.info("決勝/スプリントセッションです。ドライバーのラップタイムを分析します。")
        laps_cleaned = laps.pick_accurate() 
        if laps_cleaned.empty:
            st.warning("分析可能なクリーンラップデータがありません。")
        else:
            laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
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
            else: st.warning(f"{selected_driver}の分析可能なラップがありません。")
    else: 
        st.info(f"{selected_session}セッションです。全ドライバーの最速ラップを表示します。")
        try:
            fastest_laps = laps.pick_fastest()
            fastest_laps_summary = fastest_laps[['Driver', 'LapTime', 'Compound', 'TyreLife', 'Stint']]
            st.dataframe(fastest_laps_summary.set_index('Driver').sort_values('LapTime'), use_container_width=True)
            st.subheader("Fastest Lap Tyre Compound Distribution")
            fig_pie = px.pie(fastest_laps_summary, names='Compound', color='Compound',
                             color_discrete_map=TYRE_COLORS, title="Tyre Compounds used for Fastest Laps")
            st.plotly_chart(fig_pie, use_container_width=True)
        except Exception as e:
            st.error(f"最速ラップの分析中にエラー: {e}")

# --- タブ2 (タイヤ比較) ---
with tab2:
    st.header("Tyre Degradation Comparison")
    if laps is None or laps.empty or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        laps_cleaned = laps.pick_accurate()
        if laps_cleaned.empty:
            st.warning("分析可能なクリーンラップデータがありません。")
        else:
            laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
            st.subheader(f"{selected_year} {selected_race} ({selected_session}) - Tyre Degradation")
            fig_tyre = px.scatter(laps_cleaned, x='TyreLife', y='LapTimeSeconds', color='Compound',
                               color_discrete_map=TYRE_COLORS, hover_data=['Driver', 'LapNumber']) 
            fig_tyre.update_layout(title="Lap Time vs. Tyre Life (All Drivers)",
                                xaxis_title="Tyre Life (Laps)", yaxis_title="Lap Time (Seconds)")
            st.plotly_chart(fig_tyre, use_container_width=True)

# --- タブ3 (ピット戦略) ---
with tab3:
    st.header("Pit Strategy Timeline (Gantt Chart)")
    if laps is None or laps.empty or results is None or results.empty or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        try:
            stints_df = laps.groupby(['Driver', 'Stint']).agg(
                Lap_Start=('LapNumber', 'min'), Lap_End=('LapNumber', 'max'), Compound=('Compound', 'first')    
            ).reset_index()
            stints_df['Stint_Length'] = stints_df['Lap_End'] - stints_df['Lap_Start'] + 1
            drivers_list_sorted = results['Abbreviation'].tolist() 
            fig_timeline = px.bar(
                stints_df, base="Lap_Start", x="Stint_Length", y="Driver", color="Compound",       
                color_discrete_map=TYRE_COLORS, orientation='h', hover_data=['Stint', 'Lap_Start', 'Lap_End']
            )
            fig_timeline.update_yaxes(categoryorder='array', categoryarray=list(reversed(drivers_list_sorted)))
            fig_timeline.update_layout(title=f"{selected_race} - Race Pit Stop Strategy", xaxis_title="Lap Number")
            st.plotly_chart(fig_timeline, use_container_width=True)
        except Exception as e:
            st.error(f"ガントチャートの描画中にエラーが発生しました: {e}")


# --- タブ4 (H2H ペース比較) ---
with tab4:
    st.header("⚔️ Head-to-Head (H2H) Pace Comparison")
    
    if laps is None or laps.empty or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        laps_cleaned = laps.pick_accurate()
        if laps_cleaned.empty:
            st.warning("比較対象のクリーンラップデータがありません。")
        else:
            laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
            
            drivers_list = laps_cleaned['Driver'].unique()
            drivers_list.sort()
            
            st.sidebar.subheader("H2H Driver Selection (Tab 4)")
            driver1_index = 0
            # 角田選手(TSU)がいればデフォルトで選択
            if 'TSU' in drivers_list:
                driver1_index = list(drivers_list).index('TSU')
            
            driver1 = st.sidebar.selectbox(
                "Select Driver 1:", drivers_list, index=driver1_index
            )
            
            # 2人目のデフォルトを選択
            driver2_index = 1 if len(drivers_list) > 1 else 0
            if driver1 == 'TSU' and 'RIC' in drivers_list: # もし角田選手が選ばれていたらリカルドを
                driver2_index = list(drivers_list).index('RIC')
            elif driver1_index == driver2_index and len(drivers_list) > 1:
                driver2_index = (driver1_index + 1) % len(drivers_list) # 1人目と違う人を選ぶ

            driver2 = st.sidebar.selectbox(
                "Select Driver 2:", drivers_list, index=driver2_index
            )
            
            if driver1 == driver2:
                st.warning("比較のために、異なる2人のドライバーを選択してください。")
            else:
                laps_d1 = laps_cleaned.pick_driver(driver1)[['LapNumber', 'LapTimeSeconds']]
                laps_d2 = laps_cleaned.pick_driver(driver2)[['LapNumber', 'LapTimeSeconds']]
                
                h2h_data = pd.merge(laps_d1, laps_d2, on='LapNumber', suffixes=(f'_{driver1}', f'_{driver2}'))
                
                if h2h_data.empty:
                    st.warning(f"{driver1} と {driver2} の間に、比較可能なクリーンラップが1周もありませんでした。")
                else:
                    h2h_data['Delta'] = h2h_data[f'LapTimeSeconds_{driver1}'] - h2h_data[f'LapTimeSeconds_{driver2}']
                    
                    st.subheader(f"Pace Comparison: {driver1} vs {driver2}")

                    # グラフ1: ラップタイム比較
                    h2h_melted = h2h_data.melt(
                        id_vars=['LapNumber'], 
                        value_vars=[f'LapTimeSeconds_{driver1}', f'LapTimeSeconds_{driver2}'],
                        var_name='Driver', 
                        value_name='LapTime'
                    )
                    h2h_melted['Driver'] = h2h_melted['Driver'].str.replace('LapTimeSeconds_', '')
                    
                    fig_h2h_laps = px.line(
                        h2h_melted,
                        x='LapNumber',
                        y='LapTime',
                        color='Driver',
                        title=f"Lap Times: {driver1} vs {driver2}"
                    )
                    st.plotly_chart(fig_h2h_laps, use_container_width=True)

                    # グラフ2: デルタタイム
                    st.subheader(f"Time Delta per Lap ({driver1} vs {driver2})")
                    st.info(f"プラス ( > 0 ) の場合: {driver1} が {driver2} より遅い\n\nマイナス ( < 0 ) の場合: {driver1} が {driver2} より速い")
                    
                    fig_h2h_delta = px.area(
                        h2h_data,
                        x='LapNumber',
                        y='Delta',
                        title=f"Delta: {driver1} (Time) - {driver2} (Time)"
                    )
                    fig_h2h_delta.add_hline(y=0, line_dash="dash", line_color="black")
                    st.plotly_chart(fig_h2h_delta, use_container_width=True)
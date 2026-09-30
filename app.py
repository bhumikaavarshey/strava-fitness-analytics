
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Strava Fitness Analytics",
    page_icon="🏃",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "fitness.db"

st.markdown("""
<style>
    .main {background-color: #f7f8fa;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .metric-card {
        background: white; padding: 16px 18px; border-radius: 12px;
        border: 1px solid #e7e9ee; box-shadow: 0 2px 8px rgba(0,0,0,.04);
    }
    h1, h2, h3 {letter-spacing: -0.02em;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def load_data():
    conn = get_connection()
    files = {
        "daily_activity": "dailyActivity_merged.csv",
        "daily_calories": "dailyCalories_merged.csv",
        "daily_intensities": "dailyIntensities_merged.csv",
        "daily_steps": "dailySteps_merged.csv",
        "hourly_calories": "hourlyCalories_merged.csv",
        "hourly_intensities": "hourlyIntensities_merged.csv",
        "hourly_steps": "hourlySteps_merged.csv",
        "sleep_day": "sleepDay_merged.csv",
    }
    for table, filename in files.items():
        path = DATA_DIR / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        # Normalize date/time columns so SQL can group by date, weekday and hour.
        for col in ["ActivityDate", "ActivityDay", "ActivityHour", "SleepDay"]:
            if col in df.columns:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if col in ["ActivityDate", "ActivityDay"]:
                    df["date"] = parsed.dt.strftime("%Y-%m-%d")
                    df["weekday"] = parsed.dt.strftime("%A")
                elif col == "ActivityHour":
                    df["date"] = parsed.dt.strftime("%Y-%m-%d")
                    df["hour"] = parsed.dt.hour
                    df["weekday"] = parsed.dt.strftime("%A")
                elif col == "SleepDay":
                    df["date"] = parsed.dt.strftime("%Y-%m-%d")
                    df["weekday"] = parsed.dt.strftime("%A")
        df.to_sql(table, conn, if_exists="replace", index=False)
    return conn

conn = load_data()

@st.cache_data
def sql_df(query):
    return pd.read_sql_query(query, conn)

def fmt_int(x):
    return f"{x:,.0f}"

def fmt_1(x):
    return f"{x:,.1f}"

st.sidebar.title("🏃 Fitness Analytics")
page = st.sidebar.radio("Navigate", ["Dashboard", "SQL Analysis", "Data Quality"])

st.sidebar.caption("Fitbit open/public fitness dataset used for the case study.")

if page == "Dashboard":
    st.title("🏃 Fitness Data Analytics Dashboard")
    st.caption("Interactive dashboard built in Streamlit with SQLite SQL analysis.")

    min_date, max_date = sql_df(
        "SELECT MIN(date), MAX(date) FROM daily_activity"
    ).iloc[0]
    date_range = st.sidebar.date_input(
        "Activity date range",
        value=(pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()),
        min_value=pd.to_datetime(min_date).date(),
        max_value=pd.to_datetime(max_date).date(),
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        start, end = pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()

    user_options = ["All users"] + [str(x) for x in sql_df(
        "SELECT DISTINCT Id FROM daily_activity ORDER BY Id"
    )["Id"].tolist()]
    user = st.sidebar.selectbox("User", user_options)

    where = f"date BETWEEN '{start}' AND '{end}'"
    if user != "All users":
        where += f" AND Id = {int(user)}"

    kpi = sql_df(f"""
        SELECT
            AVG(TotalSteps) avg_steps,
            AVG(Calories) avg_calories,
            AVG(SedentaryMinutes) avg_sedentary,
            AVG(VeryActiveMinutes + FairlyActiveMinutes + LightlyActiveMinutes) avg_active
        FROM daily_activity
        WHERE {where}
    """).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average Daily Steps", fmt_int(kpi.avg_steps))
    c2.metric("Average Calories", fmt_int(kpi.avg_calories))
    c3.metric("Avg Active Minutes", fmt_1(kpi.avg_active))
    c4.metric("Avg Sedentary Minutes", fmt_1(kpi.avg_sedentary))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        steps = sql_df(f"""
            SELECT weekday, AVG(TotalSteps) avg_steps
            FROM daily_activity
            WHERE {where}
            GROUP BY weekday
        """)
        order = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        steps["weekday"] = pd.Categorical(steps["weekday"], categories=order, ordered=True)
        steps = steps.sort_values("weekday")
        fig = px.bar(steps, x="weekday", y="avg_steps", title="Average Steps by Weekday",
                     labels={"weekday":"Weekday","avg_steps":"Average Steps"})
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        activity = sql_df(f"""
            SELECT
                AVG(LightlyActiveMinutes) lightly_active,
                AVG(FairlyActiveMinutes) fairly_active,
                AVG(VeryActiveMinutes) very_active
            FROM daily_activity
            WHERE {where}
        """).melt(var_name="activity_type", value_name="minutes")
        activity["activity_type"] = activity["activity_type"].str.replace("_", " ").str.title()
        fig = px.bar(activity, x="activity_type", y="minutes",
                     title="Average Minutes by Activity Intensity",
                     labels={"activity_type":"Activity Type","minutes":"Minutes"})
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        trend = sql_df(f"""
            SELECT date, TotalSteps, Calories
            FROM daily_activity
            WHERE {where}
            ORDER BY date
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["date"], y=trend["TotalSteps"],
                                 mode="lines+markers", name="Steps"))
        fig.update_layout(template="plotly_white", title="Daily Step Trend",
                          yaxis_title="Steps", xaxis_title="Date")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        hourly = sql_df("""
            SELECT hour, AVG(Calories) avg_calories
            FROM hourly_calories
            GROUP BY hour
            ORDER BY hour
        """)
        fig = px.line(hourly, x="hour", y="avg_calories", markers=True,
                      title="Average Calories Burned by Hour",
                      labels={"hour":"Hour of Day","avg_calories":"Average Calories"})
        fig.update_layout(template="plotly_white", xaxis=dict(dtick=2))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Key Findings")
    findings = sql_df(f"""
        SELECT
            (SELECT weekday FROM (
                SELECT weekday, AVG(TotalSteps) v FROM daily_activity
                WHERE {where} GROUP BY weekday ORDER BY v DESC LIMIT 1
            )) top_step_day,
            (SELECT ROUND(AVG(TotalSleepMinutes),1) FROM (
                SELECT Id, date, TotalMinutesAsleep AS TotalSleepMinutes
                FROM sleep_day
            )) avg_sleep
    """).iloc[0]
    st.write(
        f"• The filtered period averages **{fmt_int(kpi.avg_steps)} steps/day** and "
        f"**{fmt_int(kpi.avg_calories)} calories/day**."
    )
    st.write(
        f"• The highest average-step weekday in the filtered data is **{findings.top_step_day}**."
    )
    st.write(
        f"• Across recorded sleep entries, average sleep is **{findings.avg_sleep:.1f} minutes** "
        f"({findings.avg_sleep/60:.1f} hours)."
    )
    st.info("The dataset has known limitations: participant demographics are unavailable, coverage is incomplete for some users/days, and the collection period is from 2016.")

elif page == "SQL Analysis":
    st.title("🧮 SQL Analysis")
    st.caption("All results below are generated directly from SQLite tables loaded from the supplied CSV files.")

    queries = {
        "1. Average steps by weekday": """
SELECT weekday, ROUND(AVG(TotalSteps), 0) AS avg_steps
FROM daily_activity
GROUP BY weekday
ORDER BY CASE weekday
    WHEN 'Sunday' THEN 1 WHEN 'Monday' THEN 2 WHEN 'Tuesday' THEN 3
    WHEN 'Wednesday' THEN 4 WHEN 'Thursday' THEN 5 WHEN 'Friday' THEN 6
    WHEN 'Saturday' THEN 7 END;
""",
        "2. Activity intensity summary": """
SELECT
    ROUND(AVG(LightlyActiveMinutes),1) AS avg_lightly_active_minutes,
    ROUND(AVG(FairlyActiveMinutes),1) AS avg_fairly_active_minutes,
    ROUND(AVG(VeryActiveMinutes),1) AS avg_very_active_minutes,
    ROUND(AVG(SedentaryMinutes),1) AS avg_sedentary_minutes
FROM daily_activity;
""",
        "3. Top 10 users by average daily steps": """
SELECT Id, ROUND(AVG(TotalSteps),0) AS avg_daily_steps
FROM daily_activity
GROUP BY Id
ORDER BY avg_daily_steps DESC
LIMIT 10;
""",
        "4. Top 10 most sedentary users": """
SELECT Id, ROUND(AVG(SedentaryMinutes),1) AS avg_sedentary_minutes
FROM daily_activity
GROUP BY Id
ORDER BY avg_sedentary_minutes DESC
LIMIT 10;
""",
        "5. Average calories by hour": """
SELECT hour, ROUND(AVG(Calories),2) AS avg_calories
FROM hourly_calories
GROUP BY hour
ORDER BY hour;
""",
        "6. Daily steps vs calories": """
SELECT date,
       ROUND(AVG(TotalSteps),0) AS steps,
       ROUND(AVG(Calories),0) AS calories
FROM daily_activity
GROUP BY date
ORDER BY date;
""",
        "7. Sleep analysis": """
SELECT
    ROUND(AVG(TotalMinutesAsleep),1) AS avg_sleep_minutes,
    ROUND(AVG(TotalTimeInBed),1) AS avg_time_in_bed,
    ROUND(AVG(TotalTimeInBed - TotalMinutesAsleep),1) AS avg_awake_in_bed_minutes
FROM sleep_day;
""",
        "8. Data quality / coverage": """
SELECT
    COUNT(*) AS daily_rows,
    COUNT(DISTINCT Id) AS users,
    MIN(date) AS start_date,
    MAX(date) AS end_date,
    SUM(CASE WHEN TotalSteps IS NULL THEN 1 ELSE 0 END) AS null_step_rows
FROM daily_activity;
"""
    }

    choice = st.selectbox("Choose an analysis", list(queries.keys()))
    query = queries[choice]
    st.code(query.strip(), language="sql")

    result = sql_df(query)
    st.dataframe(result, use_container_width=True, hide_index=True)

    insights = {
        "1. Average steps by weekday": "This identifies the weekly movement pattern and can support day-specific engagement campaigns.",
        "2. Activity intensity summary": "The dataset contains much more lightly active time than fairly or very active time, while sedentary time is also substantial.",
        "3. Top 10 users by average daily steps": "This highlights the most active tracked users and provides a basis for high-engagement user segmentation.",
        "4. Top 10 most sedentary users": "This identifies users with the highest recorded sedentary time and can support inactivity nudges.",
        "5. Average calories by hour": "Hourly calorie patterns show when users are most active across a typical day.",
        "6. Daily steps vs calories": "Comparing the two measures helps examine whether higher movement days coincide with higher recorded calorie burn.",
        "7. Sleep analysis": "Sleep duration and time-in-bed can be compared to understand rest patterns in the tracked population.",
        "8. Data quality / coverage": "This gives the core record count, user count, date range and a basic null check."
    }
    st.success(insights[choice])

    st.subheader("Run your own SELECT query")
    custom = st.text_area(
        "Custom SQL",
        value="SELECT Id, ROUND(AVG(TotalSteps),0) AS avg_steps FROM daily_activity GROUP BY Id ORDER BY avg_steps DESC LIMIT 10;",
        height=130,
    )
    if st.button("Run SQL"):
        clean = custom.strip().lower()
        if not (clean.startswith("select") or clean.startswith("with")):
            st.error("For safety, only SELECT/WITH queries are allowed.")
        else:
            try:
                out = sql_df(custom)
                st.dataframe(out, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"SQL error: {e}")

elif page == "Data Quality":
    st.title("🔎 Data Quality & Sources")
    st.write(
        "This app uses the supplied Fitbit fitness-tracking CSV files. "
        "The project deck notes that the dataset contains minute-, hour-, and day-level tracking data "
        "for activity, heart rate and sleep, with limitations around demographics, incomplete coverage and the 2016 collection period."
    )
    tables = sql_df("""
        SELECT name AS table_name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    rows = []
    for table in tables["table_name"]:
        n = sql_df(f"SELECT COUNT(*) n FROM \"{table}\"").iloc[0,0]
        rows.append({"Table": table, "Rows": n})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.warning(
        "Important: the original case-study deck states that the data is from Fitbit open/public data, "
        "covers about 30 individuals, has incomplete day coverage for some participants, and lacks age/sex/profession details."
    )
    st.subheader("Project workflow")
    st.markdown("""
    **Data → Cleaning → SQL → Insights → Dashboard**

    - CSV files are loaded into SQLite.
    - Date/time fields are normalized for SQL grouping.
    - Dashboard KPIs and charts are generated from SQL queries.
    - The SQL Analysis page exposes the exact queries used.
    - Custom SELECT/WITH queries are supported for demonstration during the presentation.
    """)

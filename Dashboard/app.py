from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# Read from parquet after running refresh script

# First we will get Calendly specific data

DATA_DIR = Path(__file__).parent / "data"

#-------------------
# Page Setup
#--------------------
st.set_page_config(
    page_title="InsightFlow-Project",
    page_icon=":calendar:",
    layout="wide"
)

#-----------------------
# Boiler Plate code first
#------------------------

@st.cache_data
def load_data():
    initial_gold = pd.read_parquet(DATA_DIR / "calendly_marketing.parquet")
    initial_gold['booking_date'] = pd.to_datetime(initial_gold['booking_date'])
    return initial_gold

try:
    df = load_data()
except FileNotFoundError as e:
    st.error(
        f"Missing local data files, Run 'refresh.py first. \n\n"
        f"Details {e}"
    )
    st.stop()

#---------------
# HEADER
#---------------

st.title("Calendly Insights")
st.caption(
    f"Caption here if needed"
)

#----------------------------------
# PANDAS Aggregations and tuning
#---------------------------------

#---------------------------------------------------------------
# 1.1 Daily Calls Booked by source
# Count of calendly bookings per source per day
# Line chart: Date vs Number of Bookings, color-coded by source
# ----------------------------------------------------------------

#-------------------------------
# Filtering and cleaning issues
#-------------------------------

now = pd.Timestamp.now()
current_year = now.year
current_month = now.month

df = df[(df['booking_date'].dt.month == current_month) & (df['booking_date'].dt.year == current_year)]
df['spend'] = df['spend'].fillna(0).astype(float)

#----------------------------------------------------


calendly_bookings = df.groupby(['booking_date','channel']).agg(
    bookings = ('invitee_id', 'count')
).reset_index()

fig1 = px.line(
    calendly_bookings, 
    x='booking_date', 
    y='bookings', color='channel',
    title='Daily Calls Booked by Source'
    )
st.plotly_chart(fig1)

#-----------------------------------------
# 1.2 Cost Per Booking
# Average cost per booking per channel
# CPB = Total Spend / Total Booked Calls
# Bar chart: Channel vs CPB
# KPI Tiles: Total Bookings, Total Spend, Average CPB
# Table with sorting: Channel, Spend, Bookings, CPB
#--------------------------------------------------------


cost_per_bookings = df.groupby('channel').agg(
    total_spend = ('spend', 'sum'),
    booked_calls = ('invitee_id', 'count')
).reset_index()

cost_per_bookings['Average_CPB'] = cost_per_bookings['total_spend'] / cost_per_bookings['booked_calls']

fig2 = px.bar(
    cost_per_bookings, 
    x='channel', 
    y='Average_CPB', 
    title="Average Cost Per Booking by Source",
)

st.plotly_chart(fig2)

#---------------------------------------------------
# KPI Tiles Section
#-------------------------------------------------

total_bookings = cost_per_bookings['booked_calls'].sum()
total_spend = cost_per_bookings['total_spend'].sum()
average_cpb = cost_per_bookings['Average_CPB'].mean()

st.subheader("KPI Metrics", divider=True)
col1, col2, col3 = st.columns(3)

col1.metric(label="Total Bookings", value=f"{total_bookings}")
col2.metric(label="Total Spend", value=f"${total_spend:,.0f}")
col3.metric(label="Average CPB", value=f"${average_cpb:,.2f}")

st.dataframe(cost_per_bookings, use_container_width=True)

st.subheader('',divider=True)

st.subheader("Bookings Trend Over Time")

#------------------
# Booking Trends over time
#---------------------------

# 1. sort dateframe created in 1.1 by date
# 2. group by source(channel) and specify column to cumsum

bookings_sorted = calendly_bookings.sort_values(by='booking_date')
bookings_sorted['cumulative_bookings'] = bookings_sorted.groupby('channel')['bookings'].transform('cumsum')

# now plot it

fig3 = px.area(
  bookings_sorted,
  x='booking_date',
  y = 'cumulative_bookings',
  color='channel'
)

st.plotly_chart(fig3)
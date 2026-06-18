import awswrangler as wr
import pandas as pd
import os

os.makedirs("data", exist_ok=True)
print("Querying Athena...")

df = wr.athena.read_sql_query(
    sql="SELECT * from marketing",
    database="insightflow-db",
    s3_output="s3://insightflow-wistia/athena_queries/"
)

# Extract date values from start_time 

df['start_time'] = pd.to_datetime(df['start_time'])
df['booking_date'] = df['start_time'].dt.date
df['hour'] = df['start_time'].dt.hour
df['day_of_week'] = df['start_time'].dt.day_name()
df['week'] = df['start_time'].dt.isocalendar().week

df.to_parquet("data/calendly_marketing.parquet", index=False)
print(f"Data refreshed successfully - {len(df)} rows saved")
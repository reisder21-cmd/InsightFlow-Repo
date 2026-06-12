import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from datetime import date
from pyspark.sql.utils import AnalysisException

from pyspark.sql.functions import to_date

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

today = date.today()

# read data from silver
df_visitors = spark.read.parquet(f"s3://insightflow-wistia/silver/visitor_{today}/")
df_metadata = spark.read.parquet(f"s3://insightflow-wistia/silver/metadata_{today}/")

try:
    df_events = spark.read.parquet(f"s3://insightflow-wistia/silver/events_{today}/")

    # convert 'received_at' to 'date' to get proper join
    df_events = df_events.withColumn("date", to_date("received_at"))
except AnalysisException:
    print("No events data today, proceeding without events join")
    df_events = None

# join data together and select columns because many columns have same name
if df_events is not None:
    gold = (df_visitors
        .join(df_events, on='visitor_key', how="left")
        .join(df_metadata, on=["media_id","date"], how="left")
        .select(
            df_visitors['visitor_key'],
            df_visitors['created_at'],
            df_visitors['load_count'],
            df_visitors['play_count'],
            df_events['event_key'],
            df_events['ip'],
            df_events['country'],
            df_events['region'],
            df_events['city'],
            df_events['percent_viewed'],
            df_events['media_id'],
            df_events['media_name'],
            df_metadata['date'],
            df_metadata['hours_watched']
    ))
    gold.write.mode("overwrite").parquet("s3://insightflow-wistia/gold/")
else:
    df_visitors.write.mode("overwrite").parquet("s3://insightflow-wistia/gold/visitors/")
    df_metadata.write.mode("overwrite").parquet("s3://insightflow-wistia/gold/media_stats/")

job.commit()

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from datetime import date
from pyspark.sql.utils import AnalysisException

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def wistia_transform(df,key_columns):
    df = df.dropDuplicates(key_columns)
    return df
    
today = date.today()
key_columns_map = {
    'visitor':['visitor_key'],
    'events': ['event_key'],
    'metadata': ['media_id', 'date']
    
}

for data_type in key_columns_map:
    try:
        df=spark.read.parquet(f"s3://insightflow-wistia/bronze/{data_type}_{today}*.parquet")
        df = wistia_transform(df, key_columns_map[data_type])
        df.write.mode("overwrite").parquet(f"s3://insightflow-wistia/silver/{data_type}_{today}/")
        print(f"{data_type} silver write complete")
    except AnalysisException as e:
        print(f"No bronze data found for {data_type} on {today}, skipping: {e}")

job.commit()
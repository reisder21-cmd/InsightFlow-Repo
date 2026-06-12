import sys
import boto3
import json
import urllib.request
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
# from pyspark.sql import SparkSession
# from pyspark.sql.functions import current_date
from datetime import date, timedelta

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

secrets_client = boto3.client('secretsmanager')
secret = secrets_client.get_secret_value(SecretId='insightflow/wistia')
api_token = json.loads(secret['SecretString'])['wistia-api-token']

headers = {
    "Authorization": f"Bearer {api_token}",
    "Accept": "application/json"
}

# get today's date, this is just for labeling the S3 filename
today = date.today()
yesterday = date.today() - timedelta(1) # This is to only get media stats and visitors from yesterday, see logic comment below
test_date = date(2026, 3, 10)


media_ids = ['gskhw4w4lm','v08dlrgr7v']
for media_id in media_ids:
  metadata_url = f"https://api.wistia.com/modern/stats/medias/{media_id}/by_date?start_date={yesterday}"
  page = 0
  while True:
      events_url = f"https://api.wistia.com/modern/stats/events?media_id={media_id}&per_page=100&{page}&start_date={yesterday}"
      
      events_req = urllib.request.Request(events_url, headers=headers)
      with urllib.request.urlopen(events_req) as response:
          events=json.loads(response.read().decode('utf-8'))
      flattened_events = [
          {
              'received_at': e['received_at'],
              'event_key': e['event_key'],
              'ip': e['ip'],
              'country': e['country'],
              'region': e['region'],
              'city': e['city'],
              'percent_viewed': e['percent_viewed'],
              'visitor_key': e['visitor_key'],
              'media_id': e['media_id'],
              'media_name': e['media_name']
          }
          for e in events
      ]
      if flattened_events:
            events_df = spark.createDataFrame(flattened_events)
            events_df.write.mode("overwrite").parquet
      page +=1
      if len(events) < 100 or not flattened_events:
            break
  
  #make api call for metadata
  metadata_req = urllib.request.Request(metadata_url, headers=headers)
  with urllib.request.urlopen(metadata_req) as response:
      metadata=json.loads(response.read().decode('utf-8'))
  flattened_metadata = [
    {
        'media_id': media_id,
        'date': s['date'],
        'load_count': s['load_count'],
        'play_count': s['play_count'],
        'hours_watched': s['hours_watched']
    }
    for s in metadata
]
  metadata_df = spark.createDataFrame(flattened_metadata)
  metadata_df.write.mode("overwrite").parquet(f"s3://insightflow-wistia/bronze/metadata_{today}_{media_id}.parquet")

page = 0

while True:
    visitor_data = f"https://api.wistia.com/modern/stats/visitors?page={page}&per_page=100"

    #api call for visitor visitor data
    visitor_req = urllib.request.Request(visitor_data, headers=headers)
    with urllib.request.urlopen(visitor_req) as response:
        visitor=json.loads(response.read().decode('utf-8'))
        #print(f" DEBUG::filtered_visitors sample: {filtered_visitors[:2]}")
        
        # extract and flatten only what is needed so spark can understand it as opposed to defining the schema explicitly
        filtered_visitors = [
            {
                'visitor_key': v['visitor_key'],
                'created_at': v['created_at'],
                'last_active_at': v['last_active_at'],
                'load_count': v['load_count'],
                'play_count': v['play_count']
            }
            for v in visitor if v['created_at'][:10] >= str(yesterday) # list comprehension to get yesterdays date to present, [:10] cuts it back to YYYY-MM-DD
        ]
        # print(f"DEBUG Total visitors fetched: {len(visitor)}")
        # print(f"DEBUG Filtered visitors count: {len(filtered_visitors)}")
        # print(f"DEBUG Sample filtered: {filtered_visitors[:1]}")
        if filtered_visitors:
            visitor_df = spark.createDataFrame(filtered_visitors)
            visitor_df.write.mode("overwrite").parquet(f"s3://insightflow-wistia/bronze/visitor_{today}_{page}.parquet")
        
        page +=1
        if len(visitor) < 100 or not filtered_visitors:
            break
    
    

# put into dataframe for pyspark then write to S3
# visitor_df = spark.createDataFrame([visitor])
# visitor_df.write.mode("overwrite").parquet(f"s3://insightflow-wistia/bronze/visitor_{today}.parquet")


job.commit()
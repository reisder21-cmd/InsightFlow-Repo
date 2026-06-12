import json
import boto3
import urllib.request

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    # Read lead_id from SQS - normally would have to loop through records but its just one so 'Records[0]'
    # With records is body which is a string so needs to convert to dictionary
    # within body is the lead_id
    record = event['Records'][0]
    message_body = json.loads(record['body'])
    lead_id = message_body['lead_id']

    # Get lead_id from S3 Bronze
    bucket_name = 'insightflow-close'
    file_key = f"bronze/crm_event_{lead_id}.json"
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    file_content = s3_response['Body'].read().decode('utf-8')

    # where lead_id and details from owner get combined
    target_key = f'silver/enriched_{lead_id}.json'

    # retrieve lead owner details from public bucket, if it fails still write to S3 silver instead of crashing the entire pipeline

    url = f"https://dea-lead-owner.s3.us-east-1.amazonaws.com/{lead_id}.json"
    try:
      with urllib.request.urlopen(url) as response:
        owner_data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError:
      owner_data = {}

    #combine file_content(dict1) from S3 and the owner_data(dict2) into one dictionary
    combined = owner_data | json.loads(file_content)

    # upload to S3 Silver
    s3_client.put_object(Bucket=bucket_name,Key=target_key,Body=json.dumps(combined))
import json
import boto3
s3_client = boto3.client('s3')

def lambda_handler(event, context):

    body = json.loads(event['body'])
    calendly_id = body['payload']['uri'].split('/')[-1]
    bucket = 'insightflow-calendly'
    target_key = f"bronze/calendly_event_{calendly_id}.json"

    s3_client.put_object(Bucket=bucket,Key=target_key,Body=json.dumps(body))

    response = {'statusCode': 200,'body': json.dumps({'message': 'JSON Data loaded successfully'}),'headers': {'Content-Type': 'application/json'}}

    return response
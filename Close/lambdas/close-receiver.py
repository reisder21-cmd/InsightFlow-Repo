import json
import boto3
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

def lambda_handler(event, context):

    body = json.loads(event['body'])
    lead_id = body['event']['lead_id']
    bucket = 'insightflow-close'
    target_key = f"bronze/crm_event_{lead_id}.json"

    s3_client.put_object(Bucket=bucket,Key=target_key,Body=json.dumps(body))
    sqs_client.send_message(QueueUrl='https://sqs.us-east-1.amazonaws.com/012178638860/close-enricher-queue', MessageBody=json.dumps({'lead_id':lead_id}))
    

    response = {'statusCode': 200,'body': json.dumps({'message': 'JSON Data loaded successfully'}),'headers': {'Content-Type': 'application/json'}}

    return response
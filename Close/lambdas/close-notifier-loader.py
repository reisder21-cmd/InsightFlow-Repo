import json
import boto3
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import os

#ses_client = boto3.client('ses', region_name='us-east-1')
s3_client = boto3.client('s3')
# redshift_client = boto3.client('redshift-data', region_name='us-east-1')

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']

    object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    file_content = response['Body'].read().decode('utf-8')

    body = json.loads(file_content)

    lead_id = body['lead_id']
    display_name= body['display_name']
    lead_email = body['lead_email']
    lead_owner = body['lead_owner']
    funnel = body['funnel']
    status_label = body['status_label']
    date_created = body['date_created']
    # TEST

    date_created = date_created.replace('+00:00', '').replace('T', ' ')
    date_created = date_created[:19] # trim to YYYY-MM-DD HH:MM:SS
    
    # Slack WebHook
    slack_url = os.environ.get('SLACK_WEBHOOK_URL')

    message = f"Incoming Lead ID: {lead_id}"
    # Testing CI/CD

    payload = {
      "text": f"New Lead: {display_name} | {lead_email} | Owner: {lead_owner} | Funnel: {funnel} | Status: {status_label}"

    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
          slack_url,
          data=data,
          headers={'Content-Type': 'application/json'},
          method='POST'
    )
    try:
      with urllib.request.urlopen(req) as response:
        response_body = response.read().decode('utf-8')
      print(f"Slack notification sent: {response_body}")
    except HTTPError as e:
      print(f"Slack HTTP Error: {e.code} {e.reason}")
    except URLError as e:
      print(f"Slack URL Error: {e.reason}")





    # Create gold dictionary
    gold_record = {
        'lead_id': lead_id,
        'display_name': display_name,
        'lead_email': lead_email,
        'lead_owner': lead_owner,
        'funnel': funnel,
        'status_label': status_label,
        'date_created': date_created
    }
    # write to gold
    target_key = f'gold/lead_final_{lead_id}.json'
    s3_client.put_object(Bucket='insightflow-close',Key=target_key,Body=json.dumps(gold_record))

    # Insert into Redshift table
    # Using select instead of INSERT to only put lead is once to avoid duplicates on primary key, makes it idempotent
    # print(f'Inserting lead {lead_id} into Redshift')
    # sql=f'''
    #   INSERT INTO leads (
    #     lead_id,
    #     display_name,
    #     lead_email,
    #     lead_owner,
    #     funnel,
    #     status_label,
    #     date_created
    #    )
    #   SELECT
    #     '{lead_id}',
    #     '{display_name}',
    #     '{lead_email}',
    #     '{lead_owner}',
    #     '{funnel}',
    #     '{status_label}',
    #     '{date_created}'::TIMESTAMP
    #   WHERE NOT EXISTS (
    #     SELECT 1 FROM leads WHERE lead_id = '{lead_id}'
    #     )
    #     '''
    # import time

    # print(f"SQL: {sql}")
    # response = redshift_client.execute_statement(
    #     WorkgroupName='insightflow-workgroup',
    #     Database='dev',
    #     Sql=sql
    #   )
    # statement_id = response['Id']
    # print(f"Statement ID: {statement_id}")
    
    # time.sleep(5)
    # status_response = redshift_client.describe_statement(Id=statement_id)
    # print(f"Status: {status_response['Status']}")
    # if status_response.get('Error'):
    #     print(f"Error: {status_response['Error']}")


    # print("Redshift insert submitted")
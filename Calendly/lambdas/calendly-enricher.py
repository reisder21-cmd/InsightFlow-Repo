import json
import boto3
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import os
from datetime import date,timedelta

s3_client = boto3.client('s3')
# redshift_client = boto3.client('redshift-data', region_name='us-east-1')

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']

    object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    file_content = response['Body'].read().decode('utf-8')

    body = json.loads(file_content)

    # Invitee info from payload
    invitee_id = body['payload']['uri'].split('/')[-1]
    email = body['payload']['email']
    name = body['payload']['name']
    status = body['payload']['status']
    booking_created_at = body['payload']['created_at']

    # meeting info from payload.scheduled_event

    booking_id = body['payload']['scheduled_event']['uri'].split('/')[-1]
    start_time = body['payload']['scheduled_event']['start_time']
    end_time = body['payload']['scheduled_event']['end_time']
    event_name = body['payload']['scheduled_event']['name']
    event_type_id = body['payload']['scheduled_event']['event_type'].split('/')[-1]
    campaign = body['payload']['tracking']['utm_campaign']
    print(f"event_type_id: '{event_type_id}'")

    # Employee from payload.scheduled_event.event_membership[0]
    employee_email = body['payload']['scheduled_event']['event_memberships'][0]['user_email']
    employee_name = body['payload']['scheduled_event']['event_memberships'][0]['user_name']

    #channel mapping dictionary (event_type UUID to which social media ad)
    channel_mapping = {
        "d639ecd3-8718-4068-955a-436b10d72c78": "facebook_paid_ads",
        "dbb4ec50-38cd-4bcd-bbff-efb7b5a6f098": "youtube_paid_ads",
        "bb339e98-7a67-4af2-b584-8dbf95564312" : "tiktok_paid_ads"
    }
    channel = channel_mapping.get(event_type_id)
    print(f"invitee_id: {invitee_id}, email: {email}, name: {name}, status: {status}, booking_created_at: {booking_created_at}, booking_id: {booking_id}, start_time: {start_time}, end_time: {end_time}, event_name: {event_name}, event_type_id: {event_type_id}, channel: {channel}, employee_email: {employee_email}, employee_name: {employee_name}")

    # Joining in the spend from public S3 using yesterday's date

    yesterday = date.today() - timedelta(1)

    s3_url = f"https://dea-data-bucket.s3.us-east-1.amazonaws.com/calendly_spend_data/spend_data_{yesterday}.json"

    try:
      with urllib.request.urlopen(s3_url) as spend_response:
        spend_data = json.loads(spend_response.read().decode('utf-8'))
    except urllib.error.HTTPError:
      spend_data = {}
    print(f"spend_data fetched: {spend_data}")
    
    spend = None
    for item in spend_data:
        if item['channel'] == channel and item['date'] == str(yesterday):
            spend = item['spend']
            break
    
    # dictionary for Silver from bronze

    silver_events_data = {
        "invitee_id": invitee_id,
        "email": email,
        "name": name,
        "status": status,
        "booking_created_at": booking_created_at,
        "booking_id": booking_id,
        "start_time": start_time,
        "end_time": end_time,
        "event_name": event_name,
        "event_type_id": event_type_id,
        "channel": channel,
        "employee_email": employee_email,
        "employee_name": employee_name,
        "campaign": campaign
    }
    # Upload dictionary to silver S3
    target_key = f"silver/calendly_event_{invitee_id}.json"
    s3_client.put_object(Bucket=bucket_name,Key=target_key,Body=json.dumps(silver_events_data))

    # Create gold dictionary and add to gold S3
    gold_events_data = {
        "invitee_id": invitee_id,
        "email": email,
        "name": name,
        "status": status,
        "booking_created_at": booking_created_at,
        "booking_id": booking_id,
        "start_time": start_time,
        "end_time": end_time,
        "event_name": event_name,
        "event_type_id": event_type_id,
        "channel": channel,
        "employee_email": employee_email,
        "employee_name": employee_name,
        "spend": spend,
        "campaign": campaign
    }

    target_key = f"gold/calendly_event_{invitee_id}.json"
    s3_client.put_object(Bucket=bucket_name,Key=target_key,Body=json.dumps(gold_events_data))
    # TEST
    # TEST

    # Insert into Redshift Table

    # print(f'Inserting event {invitee_id} into Redshift')
    # sql=f'''
    #   INSERT INTO events (
    #     invitee_id,
    #     email,
    #     name,
    #     status,
    #     booking_created_at,
    #     booking_id,
    #     start_time,
    #     end_time,
    #     event_name,
    #     event_type_id,
    #     channel,
    #     employee_email,
    #     employee_name,
    #     inserted_at
    #   ) 
    #   SELECT
    #     '{invitee_id}',
    #     '{email}',
    #     '{name}',
    #     '{status}',
    #     '{booking_created_at}',
    #     '{booking_id}',
    #     '{start_time}',
    #     '{end_time}',
    #     '{event_name}',
    #     '{event_type_id}',
    #     '{channel}',
    #     '{employee_email}',
    #     '{employee_name}',
    #      GETDATE()
    #   WHERE NOT EXISTS (
    #     SELECT 1 FROM events
    #     WHERE invitee_id = '{invitee_id}'
    #   )
    # '''
    # redshift_client.execute_statement(
    # WorkgroupName='insightflow-workgroup',
    # Database='dev',
    # Sql=sql
    # )
    # print(f"spend value: {spend}, channel: {channel}")
    # print(f'Inserting spend data into Redshift')
    # sql=f'''
    #   INSERT INTO marketing (
    #     invitee_id,
    #     email,
    #     name,
    #     status,
    #     booking_created_at,
    #     booking_id,
    #     start_time,
    #     end_time,
    #     event_name,
    #     event_type_id,
    #     channel,
    #     employee_email,
    #     employee_name,
    #     spend,
    #     inserted_at
    #   ) 
    #   SELECT
    #     '{invitee_id}',
    #     '{email}',
    #     '{name}',
    #     '{status}',
    #     '{booking_created_at}',
    #     '{booking_id}',
    #     '{start_time}',
    #     '{end_time}',
    #     '{event_name}',
    #     '{event_type_id}',
    #     '{channel}',
    #     '{employee_email}',
    #     '{employee_name}',
    #      {spend},
    #      GETDATE()
    #   WHERE NOT EXISTS (
    #     SELECT 1 FROM marketing
    #     WHERE invitee_id = '{invitee_id}'
    #   )
    # '''
    # redshift_client.execute_statement(
    # WorkgroupName='insightflow-workgroup',
    # Database='dev',
    # Sql=sql
    # )
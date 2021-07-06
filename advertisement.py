import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

import io
import base64

from PIL import Image

advertisement_table = boto3.resource('dynamodb').Table(os.environ.get('DYNAMODB_ADVERTISEMENTS_TABLE'))
messages_table = boto3.resource('dynamodb').Table(os.environ.get('DYNAMODB_MESSAGES_TABLE'))


def create(event, context):
    advertisement_id = event.get('pathParameters', {}).get('id')
    advertisement_data = json.loads(event.get('body', '{}'))

    # Resize image if present
    if 'image' in advertisement_data:
        buffer = io.BytesIO()
        imgdata = base64.b64decode(advertisement_data['image'])
        img = Image.open(io.BytesIO(imgdata))
        new_img = img.resize((512, 512))  # x, y
        new_img.save(buffer, format="PNG")
        advertisement_data['image'] = str(base64.b64encode(buffer.getvalue()))[2:-1]

    advertisement_table.put_item(
        Item={
            'id': advertisement_id,
            **advertisement_data
        }
    )

    response = {
        "statusCode": 201,
        "body": json.dumps({
            "status": 201,
            "detail": f"Advertisement {advertisement_id} created.",
        })
    }

    return response


def get(event, context):
    advertisement_id = event.get('pathParameters', {}).get('id')
    advertisement = advertisement_table.query(KeyConditionExpression=Key('id').eq(advertisement_id))

    if "Items" in advertisement:
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "status": 200,
                "advertisement": advertisement["Items"][0]
            })
        }
    else:
        response = {
            "statusCode": 404,
            "body": json.dumps({
                "status": 404,
                "title": "Advertisement not found",
                "detail": f"Advertisement {advertisement_id} not found.",
            })
        }

    return response


def get_all(event, context):
    advertisements_chunk = advertisement_table.scan()

    # Make as many queries as needed due to DynamoDB's 1MBs response limit
    advertisements = advertisements_chunk['Items']
    while 'LastEvaluatedKey' in advertisements_chunk:
        advertisements_chunk = advertisement_table.scan(ExclusiveStartKey=advertisements_chunk['LastEvaluatedKey'])
        advertisements.extend(advertisements_chunk['Items'])

    response = {
        "statusCode": 200,
        "body": json.dumps({
            "status": 200,
            'advertisements': advertisements,
        })
    }

    return response


def send_message(event, context):
    advertisement_id = event.get('pathParameters', {}).get('id')
    message = json.loads(event.get('body', '{}'))
    messages_table.put_item(
        Item={
            'advertisement_id': advertisement_id,
            'timestamp': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            **message
        }
    )

    response = {
        "statusCode": 201,
        "body": json.dumps({
            "status": 201,
            "title": "OK",
            "detail": f"Advertisement {advertisement_id} has a new message",
        })
    }

    return response


def get_message(event, context):
    advertisement_id = event.get('pathParameters', {}).get('id')
    messages = messages_table.query(KeyConditionExpression=Key('advertisement_id').eq(advertisement_id))

    if "Items" in messages:
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "status": 200,
                "messages": messages["Items"]
            })
        }
    else:
        response = {
            "statusCode": 404,
            "body": json.dumps({
                "status": 404,
                "title": "Chat not found",
                "detail": f"Chat {advertisement_id} not found in database",
            })
        }

    return response

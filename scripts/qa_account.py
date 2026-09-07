"""Ephemeral hosted browser-test account. Pipe creation output directly to the test."""
import json
import secrets
import sys
import uuid
import boto3

session = boto3.Session(profile_name='simplifynext', region_name='us-east-1')
client = session.client('cognito-idp')
pool = 'us-east-1_irxzgkJjO'
if sys.argv[1] == 'create':
    username = 'augury-qa-' + uuid.uuid4().hex + '@example.com'
    password = 'Qa!' + secrets.token_urlsafe(24) + '7z'
    client.admin_create_user(UserPoolId=pool, Username=username, MessageAction='SUPPRESS',
        UserAttributes=[{'Name':'email','Value':username},{'Name':'email_verified','Value':'true'}])
    client.admin_set_user_password(UserPoolId=pool,Username=username,Password=password,Permanent=True)
    print(json.dumps({'username':username,'password':password}))
elif sys.argv[1] == 'delete':
    username = sys.argv[2]
    if not username.startswith('augury-qa-') or not username.endswith('@example.com'):
        raise ValueError('Only disposable QA accounts may be removed')
    account = client.admin_get_user(UserPoolId=pool, Username=username)
    owner = next(a['Value'] for a in account['UserAttributes'] if a['Name'] == 'sub')
    outputs = {v['OutputKey']: v['OutputValue'] for v in session.client('cloudformation').describe_stacks(StackName='simplifynext-dev')['Stacks'][0]['Outputs']}
    table = session.resource('dynamodb').Table(outputs['RunTableName'])
    workspace = table.get_item(Key={'record_id':'workspace#' + owner}, ConsistentRead=True).get('Item', {})
    for run_id in workspace.get('run_ids', []):
        item = table.get_item(Key={'record_id':run_id}, ConsistentRead=True).get('Item', {})
        if item.get('owner') != owner:
            raise ValueError('QA ownership mismatch')
        if item.get('status') in ('QUEUED','RUNNING'):
            raise RuntimeError('QA worker is still active; retain account for cleanup after completion')
        table.delete_item(Key={'record_id':run_id})
    table.delete_item(Key={'record_id':'workspace#' + owner})
    from boto3.dynamodb.conditions import Key
    ledger = session.resource('dynamodb').Table(outputs['LedgerTableName'])
    entries = ledger.query(KeyConditionExpression=Key('startup_id').eq(owner)).get('Items', [])
    for item in entries:
        ledger.delete_item(Key={'startup_id':owner, 'entry_key':item['entry_key']})
    client.admin_delete_user(UserPoolId=pool,Username=username)

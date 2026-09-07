"""Authenticated, durable workspace and human approval API."""
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from traction.schemas.founder import FounderBrief
from traction.schemas.profile import StartupProfile

table = boto3.resource('dynamodb').Table(os.environ.get('RUN_TABLE_NAME', 'unconfigured'))
lambda_client = boto3.client('lambda')

def now():
    return datetime.now(timezone.utc).isoformat()

def json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    raise TypeError(type(value).__name__)

def dumps(value):
    return json.dumps(value, default=json_default, allow_nan=False)

def db(value):
    return json.loads(dumps(value), parse_float=Decimal)

def get(key):
    item = table.get_item(Key={'record_id': key}, ConsistentRead=True).get('Item')
    if item and item.get('status') in ('RUNNING', 'QUEUED') and item.get('updated_at'):
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(item['updated_at'])).total_seconds()
        limit = 1200 if item['status'] == 'RUNNING' else 300
        if elapsed > limit:
            try:
                table.update_item(Key={'record_id': key}, UpdateExpression='SET #s=:failed, error=:error',
                    ConditionExpression='#s=:old AND updated_at=:updated', ExpressionAttributeNames={'#s':'status'},
                    ExpressionAttributeValues={':failed':'FAILED', ':error':'Worker timed out. Start a new cycle to retry.', ':old':item['status'], ':updated':item['updated_at']})
                item.update(status='FAILED', error='Worker timed out. Start a new cycle to retry.')
            except ClientError as exc:
                if exc.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise
                return get(key)
    return item

def response(status, value):
    return {'statusCode': status, 'headers': {'content-type': 'application/json', 'cache-control': 'no-store'}, 'body': dumps(value)}

class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def owned(run_id, owner):
    item = get(run_id)
    if not item or item.get('owner') != owner:
        raise ApiError(404, 'Run not found')
    return item

def public_run(item):
    return {k: v for k, v in item.items() if k not in ('checkpoint', 'owner', 'record_id')}

def invoke(item, phase):
    try:
        lambda_client.invoke(FunctionName=os.environ['RUN_CYCLE_FUNCTION_NAME'], InvocationType='Event',
                             Payload=dumps({'run_id': item['run_id'], 'phase': phase}).encode())
    except Exception:
        table.update_item(Key={'record_id': item['run_id']}, UpdateExpression='SET #s=:s, error=:e',
                          ExpressionAttributeNames={'#s': 'status'}, ExpressionAttributeValues={':s': 'FAILED', ':e': 'Could not queue workflow. Start a new cycle to retry.'})
        raise

def start(owner, payload):
    workspace_id = 'workspace#' + owner
    workspace = get(workspace_id) or {}
    if not workspace.get('brief'):
        raise ApiError(422, 'Save a valid founder brief first')
    run_id = 'run_' + str(uuid.UUID(payload['request_id']))
    if get(run_id):
        return public_run(owned(run_id, owner))
    latest = get(workspace['latest_run_id']) if workspace.get('latest_run_id') else None
    if latest and latest['status'] not in ('COMPLETE', 'FAILED', 'REJECTED'):
        raise ApiError(409, 'Finish the current cycle before starting another')
    version = int(workspace.get('cycle_count', 0))
    item = {'record_id': run_id, 'run_id': run_id, 'owner': owner, 'startup_id': owner,
            'cycle_id': version + 1, 'status': 'QUEUED', 'phase': 'plan', 'created_at': now(), 'updated_at': now(),
            'founder_brief': workspace['brief'], 'startup_profile': workspace['profile'],
            'model_mode': 'bedrock' if os.environ.get('USE_STUB_MODELS') == 'false' else 'stub',
            'execution_mode': 'simulation', 'events': [], 'result': {}}
    table.update_item(Key={'record_id': workspace_id},
        UpdateExpression='SET cycle_count=:n, latest_run_id=:r, run_ids=list_append(if_not_exists(run_ids,:empty),:ids)',
        ConditionExpression='attribute_not_exists(cycle_count) OR cycle_count=:old',
        ExpressionAttributeValues={':n': version + 1, ':r': run_id, ':empty': [], ':ids': [run_id], ':old': version})
    table.put_item(Item=db(item), ConditionExpression='attribute_not_exists(record_id)')
    invoke(item, 'plan')
    return public_run(item)

def approve(owner, run_id):
    item = owned(run_id, owner)
    if item['status'] != 'WAITING_APPROVAL' or not item.get('checkpoint'):
        raise ApiError(409, 'This run is not waiting for approval')
    table.update_item(Key={'record_id': run_id},
        UpdateExpression='SET #s=:queued, phase=:phase, approved_at=:time, updated_at=:time',
        ConditionExpression='#s=:waiting', ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':queued': 'QUEUED', ':phase': 'execute', ':waiting': 'WAITING_APPROVAL', ':time': now()})
    invoke(item, 'execute')
    return public_run(owned(run_id, owner))

def handler(event, context=None):
    try:
        owner = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
        if not owner:
            raise ApiError(401, 'Sign in to access your workspace')
        method = event.get('requestContext', {}).get('http', {}).get('method', '')
        parts = event.get('rawPath', '').strip('/').split('/')
        payload = json.loads(event.get('body') or '{}')
        if method == 'GET' and parts == ['workspace']:
            workspace = get('workspace#' + owner) or {}
            runs = [public_run(item) for key in reversed(workspace.get('run_ids', [])[-20:]) if (item := get(key)) and item.get('owner') == owner]
            return response(200, {'brief': workspace.get('brief'), 'profile': workspace.get('profile'), 'runs': runs,
                                  'model_mode': 'bedrock' if os.environ.get('USE_STUB_MODELS') == 'false' else 'stub', 'execution_mode': 'simulation'})
        if len(parts) == 2 and parts[0] == 'briefs':
            if method == 'GET':
                workspace = get('workspace#' + owner) or {}
                return response(200, {'brief': workspace.get('brief'), 'profile': workspace.get('profile')})
            if method == 'PUT':
                brief = FounderBrief.model_validate(payload['brief'])
                if not brief.startup_name.strip() or not brief.one_line_pitch.strip():
                    raise ApiError(422, 'Startup name and pitch are required')
                profile = StartupProfile.model_validate({**payload['profile'], 'startup_id': owner, 'startup_name': brief.startup_name,
                                                         'primary_outcome_metric': brief.primary_goal.metric_name})
                table.update_item(Key={'record_id': 'workspace#' + owner}, UpdateExpression='SET brief=:b, profile=:p, updated_at=:t',
                    ExpressionAttributeValues=db({':b': brief.model_dump(mode='json'), ':p': profile.model_dump(mode='json'), ':t': now()}))
                return response(200, {'saved': True, 'brief': brief.model_dump(mode='json'), 'profile': profile.model_dump(mode='json')})
        if method == 'POST' and parts == ['runs']:
            return response(202, start(owner, payload))
        if len(parts) >= 2 and parts[0] == 'runs':
            item = owned(parts[1], owner)
            if method == 'GET' and len(parts) == 2:
                return response(200, public_run(item))
            if method == 'POST' and parts[2:] == ['approve']:
                return response(202, approve(owner, parts[1]))
            if method == 'POST' and parts[2:] == ['reject']:
                feedback = str(payload.get('feedback', '')).strip()
                if not feedback:
                    raise ApiError(422, 'Explain what the Strategist should change')
                table.update_item(Key={'record_id': parts[1]},
                    UpdateExpression='SET #s=:queued, phase=:phase, founder_feedback=:f, updated_at=:t',
                    ConditionExpression='#s=:waiting', ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':queued': 'QUEUED', ':phase': 'revise_' + uuid.uuid4().hex[:8], ':f': feedback, ':t': now(), ':waiting': 'WAITING_APPROVAL'})
                item = owned(parts[1], owner)
                invoke(item, item['phase'])
                return response(202, public_run(item))
        raise ApiError(404, 'Route not found')
    except ApiError as exc:
        return response(exc.status, {'error': exc.message})
    except (ValueError, KeyError) as exc:
        return response(422, {'error': str(exc)})
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(409, {'error': 'The workflow changed. Refresh and try again.'})
        raise

lambda_handler = handler

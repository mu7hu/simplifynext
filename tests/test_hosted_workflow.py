"""Durable approval, ownership, input precision and refresh regression tests."""
import json
import uuid
from unittest.mock import Mock
import boto3
import pytest
from moto import mock_aws

@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('RUN_TABLE_NAME', 'runs-test')
    monkeypatch.setenv('RUN_CYCLE_FUNCTION_NAME', 'worker')
    with mock_aws():
        table = boto3.resource('dynamodb', region_name='us-east-1').create_table(TableName='runs-test',
            KeySchema=[{'AttributeName':'record_id','KeyType':'HASH'}], AttributeDefinitions=[{'AttributeName':'record_id','AttributeType':'S'}], BillingMode='PAY_PER_REQUEST')
        from traction.api import run_manager_lambda as manager, run_cycle_lambda as worker
        from traction.ledger.sqlite import SQLiteExperimentLedger
        from traction.config import settings
        monkeypatch.setattr(settings, 'use_stub_models', True)
        monkeypatch.setattr(manager, 'table', table)
        monkeypatch.setattr(worker, 'table', table)
        monkeypatch.setattr(manager, 'lambda_client', Mock())
        monkeypatch.setattr(worker, 'get_runtime_ledger', lambda: SQLiteExperimentLedger(str(tmp_path/'ledger.db')))
        yield manager, worker

def call(manager, method, path, body=None, owner='founder-a'):
    event={'rawPath':path,'body':json.dumps(body or {}),'requestContext':{'http':{'method':method},'authorizer':{'jwt':{'claims':{'sub':owner}}}}}
    response=manager.handler(event)
    return response['statusCode'], json.loads(response['body'])

def save(manager):
    from traction.services.intake import _ledger_ai_brief
    brief=_ledger_ai_brief().model_dump(mode='json')
    brief['total_budget']=2000.25
    profile={'stage':'SEED','sector':'B2B_SAAS','target_acv':1234.56,'sales_cycle_days':30}
    code, _=call(manager,'PUT','/briefs/current',{'brief':brief,'profile':profile})
    assert code==200

def test_save_refresh_precision_and_isolation(hosted):
    manager,_=hosted
    save(manager)
    code,data=call(manager,'GET','/workspace')
    assert code==200 and data['brief']['total_budget']==2000.25
    assert data['profile']['target_acv']==1234.56
    assert call(manager,'GET','/workspace',owner='founder-b')[1]['brief'] is None
    assert call(manager,'GET','/workspace',owner='')[0]==401

def test_approval_resumes_identical_plan_without_replanning(hosted, monkeypatch):
    manager,worker=hosted
    save(manager)
    request={'request_id':str(uuid.uuid4())}
    code,run=call(manager,'POST','/runs',request)
    assert code==202 and run['cycle_id']==1
    run_id=run['run_id']
    assert call(manager,'POST','/runs',request)[1]['run_id']==run_id
    assert call(manager,'POST','/runs',{'request_id':str(uuid.uuid4())})[0]==409
    assert call(manager,'GET','/runs/'+run_id,owner='founder-b')[0]==404
    assert call(manager,'POST','/runs/'+run_id+'/approve')[0]==409
    assert worker.handler({'run_id':run_id,'phase':'plan'})['status']=='WAITING_APPROVAL'
    saved=call(manager,'GET','/workspace')[1]['runs'][0]
    plan=saved['result']['plan']
    assert saved['result']['content_package']['items']
    assert any(e['node']=='strategist' and e['status']=='started' for e in saved['events'])
    from traction.agents.strategist import StrategistAgent
    monkeypatch.setattr(StrategistAgent,'plan_cycle',Mock(side_effect=AssertionError('Approved plan must never be regenerated')))
    assert call(manager,'POST','/runs/'+run_id+'/approve')[0]==202
    assert call(manager,'POST','/runs/'+run_id+'/approve')[0]==409
    assert worker.handler({'run_id':run_id,'phase':'execute'})['status']=='COMPLETE'
    done=call(manager,'GET','/workspace')[1]['runs'][0]
    assert done['result']['plan']==plan
    assert done['result']['results'] and done['result']['digest_markdown']
    assert worker.handler({'run_id':run_id,'phase':'execute'})=={'duplicate':True}
    assert call(manager,'POST','/runs',{'request_id':str(uuid.uuid4())})[1]['cycle_id']==2

def test_invalid_plan_reports_failure(hosted, monkeypatch):
    manager, worker=hosted
    save(manager)
    run=call(manager,'POST','/runs',{'request_id':str(uuid.uuid4())})[1]
    from traction.agents.strategist import StrategistAgent
    monkeypatch.setattr(StrategistAgent,'plan_cycle',Mock(side_effect=RuntimeError('Bedrock unavailable')))
    assert worker.handler({'run_id':run['run_id'],'phase':'plan'})['status']=='FAILED'
    data=call(manager,'GET','/runs/'+run['run_id'])[1]
    assert 'Bedrock unavailable' in data['error']
    assert not data['result'].get('plan')

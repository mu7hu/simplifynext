"""Asynchronous supervisor with durable approval snapshots and real node telemetry."""
import json
from datetime import datetime, timezone
from pydantic import BaseModel
from botocore.exceptions import ClientError
from traction.api.run_manager_lambda import table, get, db, dumps, response
from traction.config import settings
from traction.agents.strategist import StrategistAgent
from traction.agents.analyst import get_analyst_agent
from traction.agents.content import get_content_generator_agent
from traction.graph.build import compile_traction_graph
from traction.approval.cli import AutoApprovalGate
from traction.runtime import get_runtime_ledger
from traction.services.execution import get_execution_service
from traction.services.measurement import DefaultMeasurementService
from traction.services.digest import get_digest_service
from traction.schemas.founder import FounderBrief
from traction.schemas.profile import StartupProfile
from traction.schemas.experiment import ExperimentPlan
from traction.constraints.budget import validate_plan_constraints

def serialize(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value

def update(run_id, fields, event=None):
    fields = {**fields, 'updated_at': datetime.now(timezone.utc).isoformat()}
    names = {f'#k{i}': k for i, k in enumerate(fields)}
    values = {f':v{i}': db(serialize(v)) for i, v in enumerate(fields.values())}
    expr = 'SET ' + ', '.join(f'#k{i}=:v{i}' for i in range(len(fields)))
    if event:
        names['#events'] = 'events'
        values[':events'] = db([event])
        values[':empty'] = []
        expr += ', #events=list_append(if_not_exists(#events,:empty),:events)'
    table.update_item(Key={'record_id': run_id}, UpdateExpression=expr, ExpressionAttributeNames=names, ExpressionAttributeValues=values)

def result_for(state):
    plan = state.get('approved_plan') or state.get('proposed_plan')
    report = state.get('analysis_report')
    return serialize({'plan': plan, 'content_package': state.get('content_package'),
                      'analysis_report': report, 'results': state.get('normalized_results', []),
                      'raw_results': state.get('raw_results', []), 'digest_markdown': state.get('digest_markdown'),
                      'learnings': state.get('recent_learnings', []), 'constraint_errors': state.get('constraint_errors', [])})

def handler(event, context=None):
    # All browser operations go through the authenticated manager and its state guards.
    if 'requestContext' in event or 'body' in event:
        return response(409, {'error': 'Use /runs and approve the saved plan through /runs/{id}/approve'})
    run_id, phase = event['run_id'], event['phase']
    try:
        table.update_item(Key={'record_id': run_id}, UpdateExpression='SET #s=:running',
                          ConditionExpression='#s=:queued AND phase=:phase', ExpressionAttributeNames={'#s': 'status'},
                          ExpressionAttributeValues={':running': 'RUNNING', ':queued': 'QUEUED', ':phase': phase})
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'duplicate': True}
        raise
    run = get(run_id)
    try:
        if phase == 'execute':
            state = json.loads(dumps(run['checkpoint']))
            state['founder_brief'] = FounderBrief.model_validate(state['founder_brief'])
            state['startup_profile'] = StartupProfile.model_validate(state['startup_profile'])
            state['proposed_plan'] = ExperimentPlan.model_validate(state['proposed_plan'])
            valid, errors = validate_plan_constraints(state['proposed_plan'], state['founder_brief'])
            if not valid:
                raise ValueError('Saved plan failed validation: ' + '; '.join(errors))
            state.update(approved_plan=state['proposed_plan'], approval_status='APPROVED', approval_only=False)
        else:
            state = {'startup_id': run['startup_id'], 'cycle_id': int(run['cycle_id']),
                     'founder_brief': FounderBrief.model_validate(run['founder_brief']),
                     'startup_profile': StartupProfile.model_validate(run['startup_profile']),
                     'benchmark_priors': [], 'approval_only': True, 'iteration_count': 0, 'retry_count': 0,
                     'max_iterations': settings.max_graph_iterations, 'max_retries': settings.max_agent_retries,
                     'next_cycle_requested': False, 'founder_feedback': run.get('founder_feedback'), 'events': []}
        def started(node):
            update(run_id, {'current_node': node}, {'node': node, 'status': 'started',
                   'timestamp': datetime.now(timezone.utc).isoformat(), 'message': node.replace('_', ' ') + ' started'})
        graph = compile_traction_graph(ledger=get_runtime_ledger(), profiler=None, intake=None,
            strategist_agent=StrategistAgent(), analyst_agent=get_analyst_agent(), approval_gate=AutoApprovalGate(),
            execution_service=get_execution_service(seed=int(run_id[-8:].replace('-', ''), 16)),
            measurement_service=DefaultMeasurementService(), digest_service=get_digest_service(),
            content_agent=get_content_generator_agent(), on_node_start=started)
        for chunk in graph.stream(state):
            for node, changes in chunk.items():
                state.update(changes)
                events = changes.get('events', [])
                detail = dict(events[-1]) if events else {}
                detail.update(node=node, status='completed', timestamp=datetime.now(timezone.utc).isoformat())
                detail.setdefault('message', node.replace('_', ' ') + ' completed')
                update(run_id, {'result': result_for(state)}, detail)
        if not state.get('plan_valid'):
            raise ValueError('Plan could not pass validation: ' + '; '.join(state.get('constraint_errors', [])))
        waiting = state.get('approval_status') == 'PENDING'
        if not waiting and not state.get('digest_markdown'):
            raise RuntimeError('Workflow stopped before producing its digest')
        fields = {'status': 'WAITING_APPROVAL' if waiting else 'COMPLETE', 'result': result_for(state), 'current_node': None}
        if waiting:
            fields['checkpoint'] = serialize(state)
        update(run_id, fields)
        return {'run_id': run_id, 'status': fields['status']}
    except Exception as exc:
        import logging
        logging.exception('Run %s failed', run_id)
        update(run_id, {'status': 'FAILED', 'error': str(exc), 'current_node': None},
               {'node': 'supervisor', 'status': 'failed', 'timestamp': datetime.now(timezone.utc).isoformat(), 'message': str(exc)})
        return {'run_id': run_id, 'status': 'FAILED'}

lambda_handler = handler

"""Bedrock structured responses with schema validation and bounded repair.

Nova's supported tool-schema subset does not cover all our nested Pydantic
schemas. Supplying the full schema as JSON avoids silently dropping fields.
"""
import json
import boto3
from botocore.config import Config
from pydantic import ValidationError
from traction.config import settings

class BedrockJsonModel:
    def __init__(self, model_id, schema=None):
        self.model_id, self.schema = model_id, schema

    def with_structured_output(self, schema):
        return BedrockJsonModel(self.model_id, schema)

    def parse(self, text):
        data = json.loads(text)
        if self.schema.__name__ == 'ChannelContent' and isinstance(data, dict):
            # Derived QA fields are computed from the generated text by the Content agent.
            for asset in data.get('assets', []):
                if isinstance(asset, dict):
                    asset.pop('char_counts', None)
                    asset.pop('length_warnings', None)
        return self.schema.model_validate(data)

    def invoke(self, messages, **kwargs):
        if self.schema is None:
            raise ValueError('A structured output schema is required')
        system, conversation = [], []
        for message in messages:
            role = getattr(message, 'type', None) or message.get('role', 'user')
            content = message.content if hasattr(message, 'content') else message['content']
            if role == 'system':
                system.append({'text': str(content)})
            else:
                conversation.append({'role': 'assistant' if role in ('ai', 'assistant') else 'user', 'content': [{'text': str(content)}]})
        schema = self.schema.model_json_schema()
        definitions = schema.get('$defs', {})
        def inline(value):
            if isinstance(value, dict):
                if '$ref' in value:
                    return inline({**definitions[value['$ref'].split('/')[-1]], **{k:v for k,v in value.items() if k != '$ref'}})
                return {k:inline(v) for k,v in value.items() if k not in ('$defs', 'title')}
            return [inline(v) for v in value] if isinstance(value, list) else value
        if self.schema.__name__ == 'ChannelContent':
            properties = schema.get('$defs', {}).get('ContentAsset', {}).get('properties', {})
            properties.pop('char_counts', None)
            properties.pop('length_warnings', None)
        schema = inline(schema)
        system.append({'text': 'Return only a complete JSON object conforming to this JSON Schema. Populate every required nested field. Do not return markdown or placeholders. Use only the supplied evidence; never invent historical observations.\n' + json.dumps(schema)})
        client = boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_default_region).client('bedrock-runtime', config=Config(read_timeout=180, retries={'mode':'standard','max_attempts':2}))
        for attempt in range(settings.max_agent_retries + 1):
            result = client.converse(modelId=self.model_id, system=system, messages=conversation,
                                     inferenceConfig={'maxTokens':8192,'temperature':0.0})
            text = ''.join(block.get('text', '') for block in result['output']['message']['content']).strip()
            if text.startswith('```'):
                text = text.split('\n',1)[1].rsplit('```',1)[0].strip()
            try:
                return self.parse(text)
            except (ValidationError, ValueError) as exc:
                if attempt == settings.max_agent_retries:
                    raise RuntimeError(f'{self.schema.__name__} response failed schema validation after {attempt + 1} Bedrock calls') from exc
                conversation.extend([{'role':'assistant','content':[{'text':text or 'Empty response'}]},
                                     {'role':'user','content':[{'text':'Correct the complete JSON object. Validation errors: ' + str(exc)[:4000]}]}])

import json
import pytest
from pydantic import ValidationError
from traction.bedrock_json import BedrockJsonModel
from traction.schemas.content import ChannelContent

def test_content_qa_metadata_is_recomputed_not_model_supplied():
    data={'channel':'GOOGLE_SEARCH','experiment_id':'exp-1','format':'SEARCH_AD','hypothesis':'Search converts','audience':'Founders','message_angle':'Save time',
          'assets':[{'variant_label':'A','format':'SEARCH_AD','headline':'Original generated headline','body':'Original generated text',
                     'char_counts':{'secondary_headlines':[19,24]},'length_warnings':['invented warning']}]}
    content=BedrockJsonModel('amazon.nova-lite-v1:0',ChannelContent).parse(json.dumps(data))
    assert content.assets[0].body=='Original generated text'
    assert content.assets[0].char_counts=={}
    assert content.assets[0].length_warnings==[]
    data['assets']=[]
    with pytest.raises(ValidationError):
        BedrockJsonModel('amazon.nova-lite-v1:0',ChannelContent).parse(json.dumps(data))

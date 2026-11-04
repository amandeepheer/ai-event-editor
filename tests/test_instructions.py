from copy import deepcopy
import pytest
from ai_event_editor.instructions import interpret
from ai_event_editor.workflow import Setup


def shots():
    return [dict(id=str(i),path='a.mp4',category=cat,start=i*5,end=i*5+5,
                 quality=.8,decision='keep') for i,cat in enumerate(['performance','crowd','stalls'])]


@pytest.mark.parametrize('text,seconds,pace,style',[
    ('Make a one-minute cinematic recap with energetic pacing',60,'Energetic','cinematic'),
    ('Please create a 30 second wedding highlight with calm pacing',30,'Calm','wedding'),
    ('Make a 2-minute concert recap with balanced pacing',120,'Balanced','concert'),
    ('Create a 3.5 minute social reel',210,'Balanced','social-reel'),
    ('',60,'Balanced','energetic-event'),
])
def test_supported_instructions(text,seconds,pace,style):
    data=shots();before=deepcopy(data)
    result=interpret(text,Setup(),data)
    assert not result['unsupported']
    assert result['setup']['duration']==seconds
    assert result['setup']['pacing']==pace
    assert result['setup']['style']==style
    assert data==before


def test_include_and_exclude():
    result=interpret('include crowd; exclude stalls',Setup(),shots())
    assert not result['unsupported']
    assert result['candidates'][1]['decision']=='must_include'
    assert result['candidates'][2]['decision']=='reject'


@pytest.mark.parametrize('text',[
    'Add slow motion and speed ramps','add titles','remove interview silences','add transitions',
    'make it magical','not energetic','include dancing','exclude crowd and include crowd',
    '30 seconds and 60 seconds','make a 2 second recap','make a 301 second recap',
    'make a 30.5 second recap','cinematic wedding','calm energetic','start music at 30 seconds',
    'make a '+('9'*500)+' minute recap',
])
def test_unsupported_or_ambiguous_is_disclosed(text):
    assert interpret(text,Setup(),shots())['unsupported']


def test_negated_unimplemented_effects_are_normal_speed():
    assert not interpret('60 seconds without slow motion',Setup(),shots())['unsupported']


def test_rejected_shots_are_not_automatically_restored():
    data=shots();data[1]['decision']='reject'
    assert interpret('include crowd',Setup(),data)['unsupported']


def test_text_limit():
    with pytest.raises(ValueError):interpret('x'*2001,Setup(),shots())

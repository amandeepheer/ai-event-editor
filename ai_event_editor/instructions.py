"""Offline, bounded instruction interpreter; never pretends to be a general LLM."""
from copy import deepcopy
from dataclasses import asdict
import re
from math import isfinite
from .workflow import Setup, reviewed_shots
from .planner import ORDER

WORDS = {'one':1,'two':2,'three':3,'four':4,'five':5,'thirty':30,'sixty':60,'ninety':90}


def interpret(text, setup, candidates):
    if not isinstance(text, str) or len(text) > 2000:
        raise ValueError('Instructions must be text up to 2000 characters')
    settings, shots = asdict(setup), deepcopy(candidates)
    reviewed_shots(shots)
    remaining = text.lower().replace('—',' ').replace('–',' ')
    applied, unsupported = [], []
    # References to the already chosen media pool are not new editing actions.
    # Do not discard "all": using every source clip is not guaranteed by planning.
    remaining = re.sub(r'\b(?:use|using)\s+(?:these|selected|the selected)\s+(?:project\s+)?(?:clips|videos|footage)\b', ' ', remaining)
    if re.search(r'\b(?:this|selected|the selected)\s+music\b', remaining):
        if not setup.music: unsupported.append('Choose a music file before requesting this music')
        remaining = re.sub(r'\b(?:this|selected|the selected)\s+music\b', ' ', remaining)
    # Explicitly requested unsupported features block creation instead of disappearing.
    remaining = re.sub(r'\b(?:no|without|avoid)\s+(?:slow[ -]?motion|speed ramps?|effects?|transitions?)\b', ' ', remaining)
    for expression, label in [
        (r'\bslow[ -]?motion\b|\bslowmo\b|\bspeed[ -]?ramps?\b|\bretim\w*\b','Slow motion / speed ramps'),
        (r'\b(?:titles?|captions?|subtitles?|lower thirds?)\b','Native titles / captions'),
        (r'\b(?:transitions?|dissolves?|zooms?|shakes?|effects?|vfx|colour|color|grading)\b','Native visual effects / grading'),
        (r'\b(?:interviews?|speeches|speech|ducking|voiceover|dialogue)\b','Speech / interview editing'),
    ]:
        if re.search(expression, remaining):
            unsupported.append(label+' is not implemented in the plugin yet')
            remaining = re.sub(expression, ' ', remaining)
    durations = []
    def duration(match):
        number = WORDS.get(match[1], None)
        number = float(match[1]) if number is None else number
        durations.append(number*(60 if match[2].startswith('m') else 1))
        return ' '
    remaining = re.sub(r'\b(\d+(?:\.\d+)?|one|two|three|four|five|thirty|sixty|ninety)[ -]*(seconds?|secs?|s|minutes?|mins?|m)\b', duration, remaining)
    if durations:
        if len(set(durations)) != 1 or not isfinite(durations[0]) or int(durations[0]) != durations[0]:
            unsupported.append('Specify one whole-number edit duration')
        elif not 30 <= durations[0] <= 300:
            unsupported.append('Edit duration must be between 30 and 300 seconds')
        else:
            settings['duration'] = int(durations[0]); applied.append(f"Length: {settings['duration']} seconds")
    paces = []
    for expression, label in [(r'\b(?:energetic|fast[ -]?cuts?|fast[ -]?paced)\b','Energetic'),
                               (r'\b(?:calm|gentle|slow[ -]?cuts?)\b','Calm'),(r'\bbalanced\b','Balanced')]:
        if re.search(expression,remaining):
            paces.append(label); remaining=re.sub(expression,' ',remaining)
    if len(paces)>1: unsupported.append('Choose one pacing: Calm, Balanced or Energetic')
    elif paces:
        settings['pacing']=paces[0]; applied.append('Pacing: '+paces[0])
    styles=[]
    for expression, slug in [(r'\bcinematic\b','cinematic'),(r'\bwedding\b','wedding'),
                              (r'\bconcert\b','concert'),(r'\bdocumentary\b','documentary'),
                              (r'\bsocial[ -]?reel\b','social-reel')]:
        if re.search(expression,remaining): styles.append(slug); remaining=re.sub(expression,' ',remaining)
    if len(styles)>1: unsupported.append('Choose one editing style')
    elif styles: settings['style']=styles[0]; applied.append('Style: '+styles[0])
    aliases={'drone':'drone','stalls':'stalls','performance':'performance','performances':'performance',
             'dancing':'dancing','crowd':'crowd','finale':'finale'}
    actions=[]
    def category(match):
        actions.append((match[1], aliases[match[2]])); return ' '
    remaining=re.sub(r'\b(must include|exclude|reject|include)\s+(drone|stalls|performances?|dancing|crowd|finale)\b',category,remaining)
    for cat in ORDER:
        commands={a for a,c in actions if c==cat}
        if commands & {'exclude','reject'} and commands & {'include','must include'}:
            unsupported.append('Conflicting include/exclude instructions for '+cat)
            continue
        if commands & {'exclude','reject'}:
            for shot in shots:
                if shot['category']==cat: shot['decision']='reject'
            applied.append('Exclude: '+cat)
        elif commands:
            eligible=[s for s in shots if s['category']==cat and s['decision']!='reject']
            if not eligible: unsupported.append('No kept '+cat+' moment available; keep or relabel one in review')
            else:
                best=max(eligible,key=lambda s:s.get('quality',.5))
                best['decision']='must_include'
                applied.append('Must include one reviewed '+cat+' moment')
    # Unrecognized instructions are disclosed and block automatic creation.
    remaining=re.sub(r'\b(?:please|make|create|build|give|me|a|an|the|my|this|video|edit|highlight|highlights|recap|event|of|with|and|for|style|pacing|pace|cuts|cut|it|to|use)\b',' ',remaining)
    remaining=re.sub(r'[\s.,!;:\-]+',' ',remaining).strip()
    if remaining: unsupported.append('Not understood: '+remaining)
    return {'setup':settings,'candidates':shots,'applied':applied,'unsupported':unsupported,
            'interpreter':'Local rules for duration, pacing, style and category selection; not a general language model'}

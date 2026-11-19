"""Private, design-scoped native Harness checkpoints (never display evidence)."""
from contextvars import ContextVar
from hashlib import sha256
import json
import sys

CURRENT = ContextVar('native_harness_context', default=None)
KEY = 'native_harness_dialogue'


def conversation(session):
    # Feed every delivered turn, including host fallback replies and UI actions.
    # The SDK, not a host last-N heuristic, owns history retention/compaction.
    return [{'revision': turn.get('revision'), 'stage': turn.get('handled_stage'),
             'mode': turn.get('interaction_state'), 'selected_option_id': turn.get('selected_option_id'),
             'user_message': turn.get('user_message'),
             'output': {key: turn.get('output', {}).get(key) for key in
                        ('assistant_message', 'student_task', 'warnings', 'assumptions')}
             if isinstance(turn.get('output'), dict) else {}}
            for turn in session.history]


def digest(turns):
    return sha256(json.dumps(turns, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def prepare(session, model):
    from .harness_runtime import SDK_VERSION
    turns = conversation(session)
    saved = session.model_context.get(KEY, {})
    if not isinstance(saved, dict): saved = {}
    count = saved.get('history_count', 0)
    guidance_digest = digest(session.model_context.get('experience_signature'))
    valid = (saved.get('version') == 2
             and saved.get('guidance_digest') == guidance_digest and saved.get('sdk_version') == SDK_VERSION
             and saved.get('platform') == sys.platform and saved.get('mode') == session.interaction_state.value
             and saved.get('model') == model and type(count) is int and 0 <= count <= len(turns)
             and saved.get('history_digest') == digest(turns[:count]) and isinstance(saved.get('log'), str))
    return {'log': saved['log'] if valid else None, 'turns': turns[count:] if valid else turns,
            'history_count': len(turns), 'history_digest': digest(turns),
            'mode': session.interaction_state.value, 'model': model, 'version': 2,
            'guidance_digest': guidance_digest,
            'sdk_version': SDK_VERSION, 'platform': sys.platform}


def commit(session, context, log):
    if isinstance(log, str) and log:
        session.model_context[KEY] = {key: context[key] for key in
            ('version', 'sdk_version', 'platform', 'history_count', 'history_digest', 'mode', 'model', 'guidance_digest')}
        session.model_context[KEY]['log'] = log

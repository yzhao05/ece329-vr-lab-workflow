"""Native context uses isolated checkpoints, not a host last-N message window."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace

import pytest

from ece329_workflow.harness_context import CURRENT, KEY, prepare, commit
from ece329_workflow.harness_runtime import Runtime
from ece329_workflow.models import InteractionState
from ece329_workflow.workflow_harness import WorkflowHarnessTransport
from ece329_workflow.telemetry import ObservedTransport, CURRENT_TRACE
from ece329_workflow.generation_policy import TurnBudget
from tests.test_workflow_harness import Provider, LocalRuntime, payload


def session(mode):
    return SimpleNamespace(interaction_state=mode, history=[], model_context={})


@pytest.mark.parametrize('mode', list(InteractionState))
def test_full_bootstrap_incremental_delivery_and_branch_reset(mode):
    s = session(mode)
    s.history = [{'revision': i, 'user_message': str(i), 'output': {
        'assistant_message': 'A: center / B: surroundings', 'student_task': {'title': 'Choose'}}} for i in range(20)]
    c = prepare(s, 'deepseek-flash')
    assert len(c['turns']) == 20 and c['log'] is None
    commit(s, c, 'native-log')
    s.history.append({'revision': 21, 'user_message': 'The former', 'output': {'assistant_message': 'kept'}})
    c = prepare(s, 'deepseek-flash')
    assert len(c['turns']) == 1 and c['log'] == 'native-log'
    assert prepare(s, 'gpt-5.4-mini')['log'] is None
    other = session(mode)
    assert prepare(other, 'deepseek-flash')['log'] is None
    s.history[0]['output']['assistant_message'] = 'changed branch'
    assert prepare(s, 'deepseek-flash')['log'] is None


def test_long_context_does_not_bypass_native_runtime():
    provider = Provider()
    request = payload('ece329_harness_understanding')
    request['input'][0]['content'] = 'previous turn ' * 30000
    token = CURRENT.set({'log': None, 'turns': []})
    try:
        result = WorkflowHarnessTransport(provider, runtime_factory=LocalRuntime).create(request)
    finally:
        CURRENT.reset(token)
    assert result['_workflow_harness']['status'] == 'completed'
    assert len(provider.payloads[0]['input'][0]['content']) > 240000


def test_workflow_runtime_has_no_response_deadline():
    runtime = Runtime(Provider(), 'deepseek-flash', {}, None)
    assert not hasattr(runtime, 'deadline')


@pytest.mark.parametrize('mode', list(InteractionState))
def test_reply_generation_shares_native_context_with_interpretation(mode):
    from ece329_workflow.models import DesignSession
    s = DesignSession('shared-context', mode)
    s.history = [{'user_message': 'choices?', 'output': {'assistant_message': 'former or latter'}}]
    commit(s, prepare(s, 'deepseek-flash'), 'interpretation-checkpoint')
    class CheckpointRuntime(LocalRuntime):
        def run(self, prompt):
            assert self.managed_context and self.session_log == 'interpretation-checkpoint'
            assert json.loads(prompt)['delivered_turns_since_checkpoint'] == []
            value = super().run(prompt)
            self.session_log = 'reply-checkpoint'
            return value
    p = Provider()
    route = {'profile': 'test', 'max_output_tokens': 700}
    response = ObservedTransport(WorkflowHarnessTransport(p, runtime_factory=CheckpointRuntime), s, route).create(payload('ece329_stage_output'))
    assert prepare(s, 'deepseek-flash')['log'] == 'reply-checkpoint'
    assert '_harness_session_log' not in response
    assert response['_workflow_harness']['context'] == 'resumed'


@pytest.mark.parametrize('mode', list(InteractionState))
def test_checkpoint_is_durable_private_and_deleted_with_design(tmp_path, mode):
    from ece329_workflow.store import SQLiteSessionStore
    from ece329_workflow.models import DesignSession, SessionNotFound
    path = tmp_path / 'context.sqlite3'
    store = SQLiteSessionStore(path)
    s = DesignSession('private-context', mode)
    commit(s, prepare(s, 'deepseek-flash'), 'private native log')
    store.save(s)
    restarted = SQLiteSessionStore(path)
    restored = restarted.get(s.design_id)
    assert prepare(restored, 'deepseek-flash')['log'] == 'private native log'
    assert 'private native log' not in json.dumps(restored.to_dict(include_history=True))
    restarted.delete(s.design_id)
    with pytest.raises(SessionNotFound): store.get(s.design_id)


@pytest.mark.parametrize('mode', list(InteractionState))
@pytest.mark.parametrize('language', ['zh', 'en'])
def test_service_failure_is_not_presented_as_unclear_user_intent(mode, language):
    from ece329_workflow.engine import WorkflowEngine
    from ece329_workflow.generator import RuleBasedStageGenerator
    from ece329_workflow.openai_generator import FallbackStageGenerator, OpenAIStageGenerator, ModelServiceError
    from ece329_workflow.models import DesignSession
    from tests.test_experience_continue import pending
    class Offline(Provider):
        def create(self, payload): raise ModelServiceError('simulated service failure')
    generator = FallbackStageGenerator(OpenAIStageGenerator(
        WorkflowHarnessTransport(Offline(), runtime_factory=LocalRuntime)), RuleBasedStageGenerator())
    engine = WorkflowEngine(generator=generator)
    s = DesignSession('offline-context', mode)
    s.model_context['response_language'] = language
    s.model_context['dialogue_state'] = {'pending_action': pending(mode)}
    engine.store.save(s)
    result = engine.process_turn(s.design_id, {'message': '我想选前面那种', 'turn_id': 'context-failure-0001', 'language': language})
    assert ('interpretation service' if language == 'en' else '语义分析服务') in result['assistant_message']
    assert '我还没完全明白' not in result['assistant_message']
    saved = engine.store.get(s.design_id)
    assert saved.model_context['dialogue_state']['pending_action']['candidate_answer'] == pending(mode)['candidate_answer']


@pytest.mark.skipif(os.getenv('ECE329_TEST_HARNESS_RUNTIME') != '1', reason='Native SDK with local fake provider')
@pytest.mark.parametrize('mode', list(InteractionState))
@pytest.mark.parametrize("wrapped", [False, True])
def test_native_resume_includes_actual_delivered_turns_and_compacts(mode, wrapped):
    class Upstream(Provider):
        def create(self, request):
            self.payloads.append(deepcopy(request))
            compact = request['text']['format']['name'] == 'ece329_harness_context_summary'
            return {'output_text': json.dumps({'summary': 'User chose the former: center of the ring.'} if compact else {'ok': True}),
                    # Synthetic token pressure triggers the real SDK's policy.
                    'usage': {'input_tokens': 900000 if len(self.payloads) == 1 else 100, 'output_tokens': 10}}
    p = Upstream()
    class SmallWindowRuntime(Runtime):
        def __init__(self, *args, **kwargs):
            # Same native policy and bridge; force pressure using a small test
            # threshold rather than building a million-token fixture.
            super().__init__(*args, **kwargs, compaction_policy={'thresholdRatio': 0.002, 'retainTokens': 1})
    from ece329_workflow.model_limits import UnrestrictedTransport
    transport = WorkflowHarnessTransport(UnrestrictedTransport(p) if wrapped else p, runtime_factory=SmallWindowRuntime)
    s = session(mode)
    c = prepare(s, 'deepseek-flash')
    first = payload('ece329_harness_understanding')
    first['input'][0]['content'] = 'Previous alternatives: PROBE_CENTER versus PROBE_SURROUNDINGS. ' * 500
    token = CURRENT.set(c)
    try:
        result = transport.create(first)
    finally:
        CURRENT.reset(token)
    assert result['_workflow_harness']['status'] == 'completed'
    commit(s, c, result.pop('_harness_session_log'))
    assert s.model_context[KEY]['log']
    s.history.append({'revision': 1, 'user_message': 'options please',
                      'output': {'assistant_message': 'A: center. B: surroundings.'}})
    second = payload('ece329_harness_understanding')
    c = prepare(s, 'deepseek-flash')
    second['input'][0]['content'] = json.dumps({'delivered_turns_since_checkpoint': c['turns'], 'message': 'The former'})
    token = CURRENT.set(c)
    try:
        result = transport.create(second)
    finally:
        CURRENT.reset(token)
    assert result['_workflow_harness']['context'] == 'resumed'
    assert 'A: center. B: surroundings.' in str(p.payloads[-1]['input'])
    assert 'PROBE_CENTER' in str(p.payloads[1]['input'])
    assert len(p.payloads) == 3, result['_workflow_harness']
    assert p.payloads[1]['text']['format']['name'] == 'ece329_harness_context_summary'
    assert result['_workflow_harness']['summary_calls'] == 1
    assert 'compaction/end' in result['_harness_session_log']
    assert all('max_output_tokens' not in request for request in p.payloads)


def test_summary_has_separate_schema_usage_budget_and_no_second_summary():
    provider = Provider({'summary': 'checkpoint'})
    route = {'profile': 'test', 'max_output_tokens': 8192, 'max_model_calls': 4, 'turn_output_tokens': 20000}
    budget = TurnBudget(route)
    trace = SimpleNamespace(data={'calls': []})
    class CompactRuntime(LocalRuntime):
        def run(self, prompt):
            self.complete({'model': 'deepseek-v4-pro', 'messages': [{'role': 'user', 'content': 'summarize'}]})
            with pytest.raises(ValueError, match='harness_repeated_request'):
                self.complete({'model': 'deepseek-v4-pro', 'messages': [{'role': 'user', 'content': 'summarize'}]})
            return super().run(prompt)
    s = session(InteractionState.EMVR_DIRECT)
    from ece329_workflow.models import Stage
    s.current_stage = Stage.IDEA_BRAINSTORMING
    s.turn_context = {}
    token = CURRENT.set({'log': None, 'turns': []})
    trace_token = CURRENT_TRACE.set(trace)
    try:
        ObservedTransport(WorkflowHarnessTransport(provider, runtime_factory=CompactRuntime), s, route, budget).create(payload('ece329_harness_understanding'))
    finally:
        CURRENT_TRACE.reset(trace_token)
        CURRENT.reset(token)
    assert budget.calls == 2 and budget.charged == 26
    assert len(trace.data['calls']) == 2
    assert trace.data['calls'][0]['agent'] == 'context_compactor'
    assert trace.data['calls'][0]['output_tokens'] == 13


@pytest.mark.skipif(os.getenv('ECE329_TEST_HARNESS_RUNTIME') != '1', reason='Opt-in local loopback bridge')
def test_native_failed_summary_blocks_followup_and_preserves_first_error():
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from ece329_workflow.openai_generator import ModelServiceError
    error = ModelServiceError('simulated first provider error')
    class Failing(Provider):
        def create(self, request):
            self.payloads.append(request)
            raise error
    p = Failing()
    runtime = Runtime(p, 'deepseek-flash', {}, None,
                      request_template=payload('ece329_harness_understanding'))
    runtime.managed_context = True
    with runtime.bridge() as endpoint:
        for model in ('deepseek-v4-pro', 'deepseek-flash'):
            request = Request(endpoint + '/v1/chat/completions',
                data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'test'}]}).encode(),
                headers={'Authorization': 'Bearer ' + runtime.token, 'Content-Type': 'application/json'})
            with pytest.raises(HTTPError): urlopen(request, timeout=5)
    assert len(p.payloads) == 1 and runtime.failure_exception is error


@pytest.mark.parametrize('mode', list(InteractionState))
@pytest.mark.parametrize('change', ['stopped', 'new_version', 'disabled'])
def test_native_checkpoint_revokes_superseded_experience_instructions(mode, change):
    from ece329_workflow.engine import WorkflowEngine
    s = session(mode)
    s.history = [{'revision': 1, 'user_message': 'continue', 'output': {'assistant_message': 'question'}}]
    s.turn_context = {'experience_rules': [{'id': 'rule-1', 'version': 1}]}
    WorkflowEngine._refresh_experience_chain(s, enabled=True)
    commit(s, prepare(s, 'deepseek-flash'), 'private log containing old rule instructions')
    assert prepare(s, 'deepseek-flash')['log'] is not None
    if change == 'new_version':
        s.turn_context['experience_rules'][0]['version'] = 2
    else:
        s.turn_context['experience_rules'] = []
    WorkflowEngine._refresh_experience_chain(s, enabled=change != 'disabled')
    fresh = prepare(s, 'deepseek-flash')
    assert fresh['log'] is None
    assert len(fresh['turns']) == 1  # Preserve delivered conversation, discard old instructions.
    assert s.history[0]['user_message'] == 'continue'

"""No production output/deadline cap; finite call counts and job ownership."""
from copy import deepcopy
import json
import os
from threading import Event
from types import SimpleNamespace

import pytest

from ece329_workflow.generation_policy import GenerationPolicy, TurnBudget, TurnBudgetExceeded
from ece329_workflow.model_limits import UnrestrictedTransport
from ece329_workflow.models import DesignSession, InteractionState
from ece329_workflow.openai_generator import generator_from_environment
from ece329_workflow.provider_transport import provider_transport
from ece329_workflow.telemetry import CURRENT_TRACE, ObservedTransport
from ece329_workflow.usage import UsageTransport
from ece329_workflow.workflow_harness import WorkflowHarnessTransport
from tests.test_workflow_harness import Provider, LocalRuntime, payload
from tests.test_feedback_pipeline import pipeline, submit, extraction_draft, extraction_check


@pytest.mark.parametrize('provider', ['openai', 'deepseek'])
def test_factory_ignores_retired_env_and_omits_caps_at_http_boundary(monkeypatch, provider):
    from ece329_workflow import openai_generator
    env = {'ECE329_GENERATOR': provider, f'{provider.upper()}_API_KEY': 'fixture',
           'ECE329_OPENAI_FALLBACK': 'false', 'ECE329_HARNESS_ENABLED': 'false'}
    retired = ['OPENAI_TIMEOUT_SECONDS', 'DEEPSEEK_TIMEOUT_SECONDS',
        'OPENAI_INTENT_MAX_OUTPUT_TOKENS', 'OPENAI_MAX_OUTPUT_TOKENS',
        'OPENAI_STAGE_ONE_MAX_OUTPUT_TOKENS', 'OPENAI_FINAL_MAX_OUTPUT_TOKENS',
        'DEEPSEEK_MAX_OUTPUT_TOKENS', 'ECE329_MAX_OUTPUT_TOKENS_PER_CALL',
        'ECE329_MAX_OUTPUT_TOKENS_PER_TURN', 'ECE329_FEEDBACK_MAX_OUTPUT_TOKENS',
        'ECE329_FEEDBACK_CHECK_MAX_OUTPUT_TOKENS']
    env.update(dict.fromkeys(retired, 'obsolete-not-a-number'))
    generator = generator_from_environment(environ=env)
    assert generator.runtime_info()['intent_max_output_tokens'] is None
    fallback = generator_from_environment(environ={**env, 'ECE329_OPENAI_FALLBACK': 'true'})
    assert fallback.runtime_info()['intent_max_output_tokens'] is None
    adapters = provider_transport(generator.transport)
    adapter = adapters.providers[provider]
    assert not hasattr(getattr(adapter, 'http', adapter), '_timeout_seconds')
    requests = []
    class Response:
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({'output_text': '{}', 'choices': [
                {'message': {'content': '{}'}, 'finish_reason': 'stop'}]}).encode()
    def urlopen(request, timeout):
        assert timeout is None
        requests.append(json.loads(request.data))
        return Response()
    monkeypatch.setattr(openai_generator, 'urlopen', urlopen)
    request = payload('ece329_stage_output', generator.model)
    request['_workflow_output_cap'] = 1
    generator.transport.create(request)
    assert len(requests) == 1
    assert not {'max_tokens', 'max_output_tokens', '_workflow_output_cap'} & requests[0].keys()
    route = GenerationPolicy(generator, env).budget(generator.model, 'none')
    assert route == {'max_output_tokens': None, 'turn_output_tokens': None, 'max_model_calls': 12}
    from ece329_workflow.experience import ModelExperienceExtractor
    extractor = ModelExperienceExtractor(generator, env)
    assert not hasattr(extractor, 'draft_tokens') and not hasattr(extractor, 'check_tokens')
    assert extractor.lease_seconds() == 300


@pytest.mark.parametrize('mode', list(InteractionState))
def test_harness_unlimited_output_still_counts_calls_and_actual_usage(mode):
    class NoDeadline(LocalRuntime):
        def run(self, prompt):
            assert not hasattr(self, 'deadline')
            assert 'max_output_tokens' not in self.template
            return super().run(prompt)
    upstream = Provider()
    transport = WorkflowHarnessTransport(UnrestrictedTransport(upstream), runtime_factory=NoDeadline)
    route = {'profile': 'test', 'max_output_tokens': None, 'turn_output_tokens': None, 'max_model_calls': 1}
    budget = TurnBudget(route)
    trace = SimpleNamespace(data={'calls': []})
    token = CURRENT_TRACE.set(trace)
    try:
        observed = ObservedTransport(transport, DesignSession('test', mode), route, budget)
        observed.create(payload('ece329_stage_output'))
        with pytest.raises(TurnBudgetExceeded): observed.create(payload('ece329_stage_output'))
    finally:
        CURRENT_TRACE.reset(token)
    assert len(upstream.payloads) == 1
    assert 'max_output_tokens' not in upstream.payloads[0]
    assert trace.data['calls'][0]['max_output_tokens'] is None
    assert budget.charged == 13


def test_unlimited_compaction_does_not_add_sdk_summary_cap():
    from ece329_workflow.harness_runtime import Runtime
    upstream = Provider({'summary': 'Saved design and pending question.'})
    runtime = Runtime(UnrestrictedTransport(upstream), 'deepseek-flash', {}, [],
                      request_template=payload('ece329_stage_output'))
    runtime.managed_context = True
    runtime.complete({'model': 'deepseek-v4-pro', 'max_tokens': 123,
                      'messages': [{'role': 'user', 'content': 'summarize'}]})
    assert 'max_output_tokens' not in upstream.payloads[0]
    assert runtime.auxiliary_calls[0]['max_output_tokens'] is None
    with pytest.raises(ValueError, match='repeated_request'):
        runtime.complete({'model': 'deepseek-v4-pro', 'messages': [{'role': 'user', 'content': 'again'}]})


def test_lease_heartbeat_stops_on_exit():
    from ece329_workflow.lease_heartbeat import LeaseHeartbeat
    called = Event()
    with LeaseHeartbeat(lambda: called.set() or True, interval=0.01) as heartbeat:
        assert called.wait(2)
    assert not heartbeat.thread.is_alive()


def test_feedback_lease_renewal_is_token_bound_and_prevents_reclaim(pipeline):
    p = pipeline
    submit(p)
    job = p.repo.claim(lease_seconds=-1)
    assert not p.repo.renew_lease({**job, 'token': 'wrong'})
    assert p.repo.renew_lease(job, 300)
    assert p.repo.claim() is None
    p.repo.finish(job, error='fixture finished')
    assert not p.repo.renew_lease(job)


def test_feedback_analysis_omits_both_caps_and_preserves_measured_usage(pipeline):
    from ece329_workflow.experience import ModelExperienceExtractor
    requests = []
    def create(request):
        requests.append(deepcopy(request))
        value = extraction_draft() if len(requests) == 1 else extraction_check()
        return {'output_text': json.dumps(value), 'usage': {'input_tokens': 10, 'output_tokens': 5}}
    primary = SimpleNamespace(model='test', transport=UnrestrictedTransport(SimpleNamespace(create=create)))
    pipeline.service.extractor = ModelExperienceExtractor(primary, {})
    submit(pipeline)
    assert pipeline.service.run_once()
    assert len(requests) == 2
    assert all(not {'max_output_tokens', '_workflow_output_cap'} & row.keys() for row in requests)


@pytest.mark.parametrize('mode', list(InteractionState))
def test_maintainer_harness_report_and_request_have_no_response_limits(pipeline, mode):
    from ece329_workflow.experience_harness import generate
    from tests.test_experience_harness import setup, response
    pipeline.session.interaction_state = mode
    pipeline.engine.store.save(pipeline.session)
    item, body = setup(pipeline)
    upstream = Provider(json.loads(response()))
    pipeline.service.extractor.generator.transport = UnrestrictedTransport(upstream)
    result = generate(pipeline.service, item['id'], body, LocalRuntime)
    assert result['status'] == 'completed'
    assert result['draft']['status'] == 'draft_not_approved'
    assert result['limits']['timeout_seconds'] is None
    assert result['limits']['output_tokens_per_call'] is None
    assert len(upstream.payloads) == 1
    assert not {'max_output_tokens', '_workflow_output_cap'} & upstream.payloads[0].keys()
    assert generate(pipeline.service, item['id'], body, LocalRuntime) == result
    assert len(upstream.payloads) == 1  # Idempotency is independent of response time.


@pytest.mark.skipif(os.getenv('ECE329_TEST_HARNESS_RUNTIME') != '1', reason='Real SDK, local fake provider')
def test_native_sdk_accepts_no_output_limit_and_no_deadline():
    upstream = Provider({'ok': True})
    response = WorkflowHarnessTransport(UnrestrictedTransport(upstream)).create(payload('ece329_stage_output'))
    assert response['_workflow_harness']['status'] == 'completed'
    assert len(upstream.payloads) == 1
    assert 'max_output_tokens' not in upstream.payloads[0]


@pytest.mark.parametrize('mode', list(InteractionState))
def test_harness_capabilities_survive_wrappers_and_do_not_bypass_them(mode):
    from ece329_workflow.openai_generator import OpenAIStageGenerator
    from ece329_workflow.workflow_harness import enabled_for
    from ece329_workflow.harness_semantics import enabled
    upstream = Provider()
    harness = WorkflowHarnessTransport(upstream, tasks={'dialogue', 'artifact'}, runtime_factory=LocalRuntime)
    session = DesignSession('wrapped', mode)
    route = {'profile': 'test', 'max_model_calls': 1}
    budget = TurnBudget(route)
    observed = ObservedTransport(harness, session, route, budget)
    wrapped = UnrestrictedTransport(UsageTransport(observed, []))
    generator = OpenAIStageGenerator(wrapped, model='deepseek-flash')
    assert enabled(generator) and enabled_for(generator, 'artifact')
    assert not enabled_for(generator, 'stage')
    assert generator.transport is wrapped
    wrapped.create(payload('ece329_report_review'))
    assert budget.calls == 1 and len(upstream.payloads) == 1
    with pytest.raises(TurnBudgetExceeded):
        wrapped.create(payload('ece329_report_review'))
    wrapped.transport = wrapped  # Bad wrapper cycles must terminate discovery.
    assert not enabled(generator) and not enabled_for(generator, 'artifact')


def test_harness_preserves_terminal_call_limit_instead_of_retryable_service_error():
    class Exhausted(LocalRuntime):
        def run(self, prompt):
            raise TurnBudgetExceeded('call limit')
    upstream = Provider()
    transport = WorkflowHarnessTransport(upstream, runtime_factory=Exhausted)
    with pytest.raises(TurnBudgetExceeded):
        transport.create(payload('ece329_stage_output'))
    assert upstream.payloads == []

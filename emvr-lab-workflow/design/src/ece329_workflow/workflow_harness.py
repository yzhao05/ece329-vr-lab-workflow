"""Bounded Harness execution for existing workflow model contracts.

The host owns field authorization, completeness and confirmation. Native dialogue
sessions own history and compaction, with separately measured summary calls.
"""
from copy import deepcopy
import json
from threading import BoundedSemaphore
from time import monotonic

from .harness_runtime import Runtime, available
from .openai_generator import ModelServiceError, ModelOutputError, _extract_output_text

TASKS = frozenset({'dialogue', 'stage', 'translation', 'artifact'})
DIALOGUE_SCHEMAS = frozenset({
    'ece329_harness_understanding',
    'ece329_context_intent', 'ece329_compact_dialogue_acts',
    'ece329_emvr_open_answer_recovery', 'ece329_emvr_formula_phase_recovery',
    'ece329_guided_design_turn_recovery', 'ece329_pending_reference_decision',
    'ece329_pending_comparison_decisions', 'ece329_scene_batch_verification'})


def task_for(payload):
    name = payload.get('text', {}).get('format', {}).get('name')
    if name in DIALOGUE_SCHEMAS: return 'dialogue'
    if name == 'ece329_stage_output': return 'stage'
    if name == 'ece329_display_translation': return 'translation'
    if name in ('ece329_report_review', 'ece329_builder_review'): return 'artifact'
    return None


class WorkflowHarnessTransport:
    def __init__(self, transport, tasks=TASKS, *, runtime_factory=Runtime):
        self.transport, self.tasks, self.runtime_factory = transport, frozenset(tasks), runtime_factory
        self.slots = BoundedSemaphore(2)

    def create(self, payload):
        from .model_limits import without_output_cap
        payload = without_output_cap(payload)
        task = task_for(payload)
        if task not in self.tasks: return self.transport.create(payload)
        from .execution_diagnostics import record
        from .telemetry import CURRENT_TRACE, HARNESS_AUXILIARY_CALL, CURRENT_SESSION
        from .harness_context import CURRENT, prepare, commit
        context = CURRENT.get() if task == 'dialogue' else None
        stage_session = CURRENT_SESSION.get() if task == 'stage' else None
        if stage_session is not None:
            # Reply generation shares the native conversation with semantic
            # interpretation. Translation/artifact reviews remain separate tasks.
            context = prepare(stage_session, payload['model'])
        trace = CURRENT_TRACE.get()
        started = monotonic()
        event = {'task': task, 'schema': payload['text']['format']['name'], 'status': 'running',
                 'model_calls_limit': 2 if context is not None else 1, 'validation': 'host_validation_required'}
        if trace is not None:
            trace.data.setdefault('harness', []).append(event)
        record('harness', 'started', task=task, schema=event['schema'])
        runtime = None
        acquired = False
        try:
            prompt = json.dumps({'instructions': payload.get('instructions', ''),
                                 'input': payload.get('input', []),
                                 **({'delivered_turns_since_checkpoint': context['turns']}
                                    if stage_session is not None else {})}, ensure_ascii=False)
            # A known local limitation must not erase context or add another API
            # request. Execute the original bounded path once and record the bypass.
            reason = ('sdk_unavailable' if self.runtime_factory is Runtime and not available() else
                      'input_budget' if context is None and len(prompt.encode('utf-8')) > 240000 else None)
            if reason is None:
                acquired = self.slots.acquire(blocking=False)
                if not acquired: reason = 'runtime_busy'
            if reason:
                if context is not None:
                    # Do not silently send an incremental prompt without the
                    # native history it refers to. Keep the checkpoint for retry.
                    event.update(reason=reason, context='unavailable')
                    raise ModelServiceError('Harness context unavailable: ' + reason)
                event.update(status='bypassed', reason=reason)
                record('harness', 'blocked', task=task, reason=reason, fallback='existing_model_contract')
                response = self.transport.create(payload)
                response['_workflow_harness'] = {'task': task, 'status': 'bypassed', 'reason': reason}
                return response
            template = deepcopy(payload)
            calls_limit = 2 if context is not None else 1
            runtime = self.runtime_factory(self.transport, template['model'],
                template['text']['format']['schema'], None, request_template=template,
                max_calls=calls_limit)
            if context is not None:
                runtime.managed_context = True
                runtime.session_log = context['log']
                runtime.auxiliary_call = HARNESS_AUXILIARY_CALL.get()
                event.update(context='resumed' if context['log'] else 'initialized',
                             appended_turns=len(context['turns']))
            result = runtime.run(prompt)
            response = runtime.response
            # Never replace measured provider envelopes with a fabricated SDK
            # envelope; preserve actual tokens, IDs and incomplete-output details.
            if response is None or result != _extract_output_text(response):
                raise ModelOutputError('Harness response did not match the provider output')
            event.update(status='completed', model_calls=runtime.requests)
            response['_workflow_harness'] = {'task': task, 'status': 'completed', 'model_calls': runtime.requests}
            if context is not None:
                event.update(summary_calls=runtime.summary_requests)
                if stage_session is not None:
                    commit(stage_session, context, runtime.session_log)
                else:
                    response['_harness_session_log'] = runtime.session_log
                response['_workflow_harness'].update(context=event['context'],
                    appended_turns=event['appended_turns'], summary_calls=runtime.summary_requests)
            if runtime.auxiliary_calls:
                response['_harness_auxiliary_calls'] = runtime.auxiliary_calls
            record('harness', 'success', task=task, model_calls=runtime.requests,
                   validation='host_validation_required')
            return response
        except Exception as exc:
            event.update(status='failed', error_type=type(exc).__name__)
            if isinstance(exc, ValueError) and str(exc).startswith('harness_'):
                event['reason'] = str(exc)
            record('harness', 'failed', task=task, error_type=type(exc).__name__)
            from .generation_policy import TurnBudgetExceeded
            error = exc if isinstance(exc, (ModelServiceError, TurnBudgetExceeded)) else ModelServiceError('Workflow Harness failed; no automatic Harness retry')
            if runtime is not None and runtime.response is not None:
                error._workflow_usage_response = runtime.response
            if runtime is not None and runtime.auxiliary_calls:
                usage_response = getattr(error, '_workflow_usage_response', {})
                usage_response['_harness_auxiliary_calls'] = runtime.auxiliary_calls
                error._workflow_usage_response = usage_response
            if error is exc: raise
            raise error from exc
        finally:
            event['latency_ms'] = round((monotonic() - started) * 1000, 2)
            if acquired: self.slots.release()


def configure(transport, environ, *, production=False):
    enabled = environ.get('ECE329_HARNESS_ENABLED', 'true' if production else 'false').strip().lower()
    if enabled not in ('true', 'false', '1', '0'):
        from .openai_generator import ModelConfigurationError
        raise ModelConfigurationError('ECE329_HARNESS_ENABLED must be true or false')
    if enabled in ('false', '0'): return transport
    tasks = {x.strip() for x in environ.get('ECE329_HARNESS_TASKS', ','.join(sorted(TASKS))).split(',') if x.strip()}
    if not tasks or tasks - TASKS:
        from .openai_generator import ModelConfigurationError
        raise ModelConfigurationError('ECE329_HARNESS_TASKS must select dialogue,stage,translation,artifact')
    return WorkflowHarnessTransport(transport, tasks)


def enabled_for(generator, task):
    from .model_selection import primary_generator
    primary = primary_generator(generator)
    transport = getattr(primary, 'transport', None)
    seen = set()
    while transport is not None and id(transport) not in seen:
        seen.add(id(transport))
        if isinstance(transport, WorkflowHarnessTransport):
            return task in transport.tasks
        transport = getattr(transport, 'transport', None)
    return False

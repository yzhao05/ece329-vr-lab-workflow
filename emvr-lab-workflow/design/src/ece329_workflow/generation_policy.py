"""Call-count accounting and reasoning capabilities; outputs are uncapped."""

from .model_selection import model_provider, primary_generator

EFFORTS = ('none', 'low', 'medium', 'high', 'xhigh', 'max')


def supported_efforts(model):
    if model_provider(model) == 'deepseek':
        return ('none', 'low', 'high', 'max')
    return EFFORTS if model.startswith('gpt-5.6-') else EFFORTS[:-1]


class GenerationPolicy:
    def __init__(self, generator, env):
        raw = env.get('ECE329_MAX_MODEL_CALLS_PER_TURN', '12')
        try:
            self.max_calls = int(raw)
        except (TypeError, ValueError):
            raise ValueError('ECE329_MAX_MODEL_CALLS_PER_TURN must be an integer') from None
        if isinstance(raw, bool) or not 1 <= self.max_calls <= 64:
            raise ValueError('ECE329_MAX_MODEL_CALLS_PER_TURN must be between 1 and 64')
        primary = primary_generator(generator)
        self.models = {}
        for model in primary.allowed_models if primary is not None else ():
            budgets = {effort: {'max_output_tokens': None, 'turn_output_tokens': None,
                               'max_model_calls': self.max_calls} for effort in supported_efforts(model)}
            self.models[model] = {'reasoning_efforts': list(budgets), 'budgets': budgets}

    def budget(self, model, effort):
        if model is None:
            return {}
        return dict(self.models[model]['budgets'][effort])


class TurnBudgetExceeded(Exception):
    """Terminal for this turn; must not enter model repair or fallback loops."""


class TurnBudget:
    """Finite call count with measured usage; no output-token reservation."""
    def __init__(self, route):
        self.limit = None
        self.max_calls = route.get('max_model_calls', 0)
        self.charged = 0
        self.calls = 0

    def reserve(self):
        if self.calls >= self.max_calls:
            raise TurnBudgetExceeded('This turn reached its model call limit')
        self.calls += 1

    def settle(self, actual):
        # Only known usage is added here; the usage record preserves unknowns.
        if type(actual) is int and actual >= 0:
            self.charged += actual

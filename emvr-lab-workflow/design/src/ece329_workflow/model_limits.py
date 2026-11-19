"""Production requests omit application output caps and response deadlines.

Provider context/output limits still apply. Call-count and validation guards are
independent of this policy and remain enabled.
"""


def without_output_cap(payload):
    return {key: value for key, value in payload.items()
            if key not in ('max_output_tokens', 'max_tokens', '_workflow_output_cap')}


class UnrestrictedTransport:
    def __init__(self, transport):
        self.transport = transport

    def create(self, payload):
        return self.transport.create(without_output_cap(payload))

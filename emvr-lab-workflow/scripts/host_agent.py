"""Interpret the host agent's structured turn using the existing Design engine."""
from ece329_workflow.dialogue_state import ALL_INTENTS, UserIntent, fallback_intent, resolved_intent
from ece329_workflow.emvr_formula_flow import recover_topic_analysis_from_knowledge
from ece329_workflow.generator import RuleBasedStageGenerator


class HostAgentGenerator(RuleBasedStageGenerator):
    supports_emvr_formula_flow = True

    def __init__(self):
        self.interpretation = None

    def set_interpretation(self, raw):
        if not isinstance(raw, dict) or raw.get("intent") not in ALL_INTENTS:
            raise ValueError("interpretation.intent must be an existing Design intent")
        self.interpretation = {**raw, "source": "HOST_AGENT"}

    def resolve_intent(self, session, user_message, pending_action, carried_context):
        if self.interpretation is not None:
            return self.interpretation
        phase = carried_context.get("emvr_formula_flow", {}).get("phase")
        if not session.history or phase == "TOPIC_RECEIVED":
            topic = recover_topic_analysis_from_knowledge(user_message)
            if topic:
                return resolved_intent(UserIntent.ANSWER_CURRENT_QUESTION, source="HOST_COURSE_CATALOG",
                    semantic_updates={"emvr_formula_actions": [{"type": "SET_EMVR_TOPIC", "content": topic}]})
        return fallback_intent(user_message, pending_action, interaction_state=session.interaction_state)


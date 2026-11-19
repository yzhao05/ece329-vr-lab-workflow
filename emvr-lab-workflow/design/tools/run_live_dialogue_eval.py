from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ece329_workflow.engine import WorkflowEngine  # noqa: E402
from ece329_workflow.models import InteractionState, Stage  # noqa: E402


EMVR_STAGE_ANSWERS = {
    Stage.IDEA_BRAINSTORMING.value: "设计一个Unity VR实验：学生移动两个点电荷，让距离从远到近变化，比较同种和异种电荷时中间区域电场线的重排。",
    Stage.LEARNING_OBJECTIVES.value: "学生应能解释电荷极性和距离对合电场的影响，比较两种配置并把VR操作对应到物理变量。",
    Stage.RESEARCH_QUESTION.value: "在电荷量和观察方式固定时，两个点电荷从远到近移动会怎样改变中间区域的电场线；同种和异种电荷有何差异？",
    Stage.HYPOTHESIS.value: "距离减小时两源叠加更明显；同种电荷的中间场线向外分开，异种电荷的场线更集中地连接。",
    Stage.CONCEPTUAL_OR_VR_SETUP.value: "需要两个可抓取电荷、统一观察平面、场线与场强可视化、距离尺、参数面板、重置按钮和数据记录面板。",
    Stage.VARIABLES_AND_CONDITIONS.value: "自变量是电荷间距；观察场线弯曲、疏密和中间平面场强；固定电荷量、观察平面、空间边界和显示尺度。",
    Stage.CONCEPTUAL_PROCEDURE.value: "建立远距离基准，逐步减小距离并记录；分别运行同种和异种电荷，最后并排比较并解释。",
    Stage.EXPECTED_DATA_VISUALIZATION.value: "同步显示三维场线、中间平面场强热图、距离数值和两种配置的对照截图，并标注为理论计算。",
    Stage.RESULT_INTERPRETATION.value: "符合预期时用叠加解释；趋势相反或不明显时检查控制条件、采样尺度和边界假设。",
    Stage.DESIGN_VALUE_AND_LIMITATIONS.value: "VR便于观察空间场线并交互比较，但点电荷近似、有限边界和可视化抽样限制结论。",
    Stage.STUDENT_SYNTHESIS_OR_EMVR_OUTPUT.value: "请汇总完整EMVR设计并生成PDF。",
}


def _turn_id() -> str:
    return f"live-eval-{uuid.uuid4().hex}"


def _run(max_turns: int) -> dict[str, Any]:
    engine = WorkflowEngine()
    generator_info = engine.generator_info()
    if generator_info.get("provider") != "openai":
        raise RuntimeError(
            "Live evaluation requires the OpenAI generator; check ECE329_GENERATOR and OPENAI_API_KEY."
        )
    result = engine.create_design("我想研究两个点电荷靠近时电场线怎样变化")
    transcript = [{"role": "assistant", "stage": result["current_stage"], "text": result["assistant_message"]}]
    answered_stage: str | None = None
    for _ in range(max_turns):
        if result.get("workflow_status") == "complete":
            break
        stage = str(result["current_stage"])
        if answered_stage != stage or result.get("stage_payload", {}).get("awaiting_user_design_input") is True:
            message = EMVR_STAGE_ANSWERS.get(stage, "请基于前面已确认的信息给出一份可修改的课程内参考。")
            complete = False
            answered_stage = stage
        else:
            message = "这部分保留，继续完善下一部分。"
            complete = True
        transcript.append({"role": "user", "stage": stage, "text": message})
        result = engine.process_turn(
            result["design_id"],
            {"message": message, "complete_stage": complete, "turn_id": _turn_id()},
        )
        transcript.append({"role": "assistant", "stage": result["current_stage"], "text": result["assistant_message"]})
    design = engine.get_design(result["design_id"])
    return {
        "mode": InteractionState.EMVR_DIRECT.value,
        "design_id": result["design_id"],
        "status": design["status"],
        "turn_count": len([item for item in transcript if item["role"] == "user"]),
        "quality_status": design["quality_review"].get("status"),
        "report_ready": design.get("report_ready", False),
        "builder_input_ready": design.get("builder_input_ready", False),
        "transcript": transcript,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an opt-in, real-model VR design dialogue regression."
    )
    parser.add_argument("--mode", choices=("guided", "emvr", "both"), default="emvr", help="Legacy names select the same unified workflow.")
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / ".test-tmp" / "live-dialogue-eval.json")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required; this script makes paid live-model calls")
    os.environ["ECE329_GENERATOR"] = "openai"
    results = [_run(args.max_turns)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps([{key: value for key, value in result.items() if key != "transcript"} for result in results], ensure_ascii=False, indent=2))
    return 0 if all(result["status"] == "complete" and result["report_ready"] and result["builder_input_ready"]
                    for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

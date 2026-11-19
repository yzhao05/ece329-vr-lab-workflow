# 宿主 Agent 输入协议

在包根运行 `python emvr-lab-workflow/scripts/workflow.py turn DESIGN_ID --stdin-json`，通过标准输入发送一个 UTF-8 JSON 对象。将当前用户的原话放入 `message`。普通回复只需要原话；使用可见选项时可设置 `selected_option_id`。重新发送同一个操作时沿用同一 `turn_id`。引擎返回实际接受的修改、草稿和待回答项。

当用户以自然语言指代已显示的公式或修订多个细节时，宿主可随附 `interpretation`。仅描述原话所授权的动作。例如，**仅当本次用户已明确选定长螺线管公式**时：

```json
{
  "message": "选择长螺线管内部磁场公式",
  "turn_id": "design-turn-002",
  "interpretation": {
    "intent": "ANSWER_CURRENT_QUESTION",
    "confidence": 1.0,
    "semantic_updates": {
      "emvr_formula_actions": [{
        "type": "SELECT_EMVR_FORMULAS",
        "content": {
          "primary_profile_ids": ["FD13_CURRENT_SHEET_SOLENOID"],
          "primary_formula_ids": ["long_solenoid_field"]
        }
      }]
    }
  }
}
```

对于“给我参考”，可使用 `intent: REQUEST_MORE_EXAMPLES`。对于“解释一下这个关系”，可使用 `ASK_COURSE_QUESTION`。对待核对的草稿提出修改，将意图及修改目标绑定到当前阶段的可见字段。含义不明确时先追问。执行确认使用用户原话及 `"complete_stage": true`。从最新的 `stage_payload` 和课程索引取得候选 ID。引擎负责约束合法 ID、验证输入和决定状态转换。

动作词汇与字段定义以 `emvr-lab-workflow/design/src/ece329_workflow/dialogue_state.py` 中的 `UserIntent`、`dialogue_acts.py` 及 `emvr_formula_flow.py` 的公式动作校验为准。详细输入可以使用 JSON 管道或宿主的子进程接口传入，无需开启 HTTP 服务。


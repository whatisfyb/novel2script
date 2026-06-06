"""
ReAct agent runner — the core loop shared by extractor / critic / refiner.

The loop:
  1. Send prompt + accumulated observations to LLM
  2. LLM returns {thought, action, action_input} OR {is_final, final_answer}
  3. If tool call: execute tool, append observation, repeat
  4. If final: validate final_answer against the agent's specific schema, return

The Pydantic `ReActStep` schema is enforced as LLM's response_format,
so the LLM cannot return unstructured text.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from llm.client import llm_complete, LLMError
from llm.react_schema import ReActStep
from pydantic import BaseModel

logger = logging.getLogger(__name__)


async def run_react_agent(
    system_prompt: str,
    user_context: str,
    tools: dict[str, Any],
    final_schema: type[BaseModel],
    max_iterations: int = 5,
) -> dict[str, Any]:
    """
    Run a ReAct agent loop.

    Args:
        system_prompt: the system instructions for this agent
        user_context: the user input (scene text + characters etc.)
        tools: dict of tool name -> async function
        final_schema: Pydantic model class to validate the final answer
        max_iterations: safety cap on loop iterations

    Returns:
        Parsed final answer as a dict (validated against final_schema)

    Raises:
        LLMError: if all retries fail
        ValueError: if loop exits without a final answer
    """
    # Build initial prompt
    full_prompt = f"""{system_prompt}

{user_context}

请按 ReAct 范式工作:
1. 先用工具分析场景/角色/对话
2. 观察工具返回结果
3. 继续推理或输出最终答案

每一步返回:
- 工具调用: {{"thought": "...", "action": "tool_name", "action_input": {{...}}}}
- 最终答案: {{"thought": "...", "is_final": true, "final_answer": {{...}}}}

最终答案必须严格符合:
{json.dumps(final_schema.model_json_schema(), ensure_ascii=False, indent=2)[:2000]}
"""

    history: list[str] = []  # accumulated observations
    last_data: dict | None = None

    for iteration in range(max_iterations):
        logger.info("ReAct iteration %d", iteration + 1)

        # Build prompt with accumulated history
        if history:
            history_text = "\n\n".join(history)
            current_prompt = f"{full_prompt}\n\n【之前的观察】\n{history_text}"
        else:
            current_prompt = full_prompt

        # Call LLM with ReActStep schema
        try:
            data = await llm_complete(
                current_prompt,
                pydantic_model=ReActStep,
            )
        except LLMError as e:
            logger.error("LLM call failed in ReAct: %s", e)
            break

        if not isinstance(data, dict):
            logger.warning("LLM returned non-dict: %s", type(data))
            break

        last_data = data
        thought = data.get("thought", "")
        is_final = data.get("is_final", False)
        action = data.get("action")
        action_input = data.get("action_input") or {}

        # Case 1: Final answer
        if is_final:
            final_answer = data.get("final_answer")
            if final_answer is None:
                logger.warning("is_final=True but final_answer is None")
                break
            # Validate against agent's specific schema
            try:
                validated = final_schema.model_validate(final_answer)
                logger.info("Final answer validated: %d fields", len(validated.model_dump()))
                return validated.model_dump()
            except Exception as e:
                logger.warning("Final answer validation failed: %s. Retrying...", e)
                history.append(
                    f"迭代 {iteration + 1}: 你的最终答案不符合 schema: {e}\n"
                    f"请严格按 schema 重新输出 final_answer。"
                )
                continue

        # Case 2: Tool call
        if action:
            if action not in tools:
                history.append(
                    f"迭代 {iteration + 1}: 思考={thought}\n"
                    f"错误: 未知工具 '{action}'\n"
                    f"可用工具: {list(tools.keys())}\n"
                    f"请使用已知工具或输出最终答案。"
                )
                continue

            # Execute tool
            try:
                logger.info("Calling tool: %s with %s", action, action_input)
                result = await tools[action](**action_input)
                history.append(
                    f"迭代 {iteration + 1}: 思考={thought}\n"
                    f"工具调用: {action}({json.dumps(action_input, ensure_ascii=False)})\n"
                    f"观察: {json.dumps(result, ensure_ascii=False, default=str)[:1500]}"
                )
            except Exception as e:
                logger.error("Tool %s failed: %s", action, e)
                history.append(
                    f"迭代 {iteration + 1}: 思考={thought}\n"
                    f"工具 {action} 调用失败: {e}\n"
                    f"请重试或换其他工具,或直接输出最终答案。"
                )
            continue

        # Case 3: Neither tool call nor final answer
        logger.warning("LLM returned neither action nor is_final: %s", data)
        history.append(
            f"迭代 {iteration + 1}: 你的输出既没有 action 也没有 is_final。\n"
            f"请明确调用工具或输出最终答案。"
        )

    # Loop exhausted without final answer
    logger.warning("ReAct loop exhausted after %d iterations", max_iterations)
    if last_data and last_data.get("final_answer"):
        # Try to validate the last attempt
        try:
            return final_schema.model_validate(last_data["final_answer"]).model_dump()
        except Exception:
            pass
    raise ValueError(
        f"ReAct agent did not produce a valid final answer in {max_iterations} iterations"
    )

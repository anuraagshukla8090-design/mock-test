"""Quick smoke test: verify qwen2.5:7b via Ollama returns valid JSON metadata."""
import asyncio
import json
import sys

from app.services.llm import get_llm_client

PROMPT = """You are a metadata tagger for JEE exam questions.

Given this question:
A ball is thrown vertically upward with velocity 20 m/s. Find the maximum height.

Return ONLY this JSON object:
{
  "chapter": "Kinematics",
  "topic": "Equations of Motion",
  "subtopic": null,
  "difficulty": "easy",
  "question_type": "numerical",
  "concepts": ["kinematics", "equations of motion"],
  "has_formula": true,
  "has_diagram": false
}"""


async def main():
    llm = get_llm_client()
    print(f"Provider : {type(llm).__name__}")
    print(f"Model    : {llm._model}")
    print("Calling LLM...")
    result = await llm.generate_json(PROMPT)
    print("\nResponse:")
    print(json.dumps(result, indent=2))
    print()
    required = {"chapter", "difficulty", "question_type", "concepts"}
    missing = required - set(result.keys())
    if missing:
        print(f"FAILED — missing keys: {missing}")
        sys.exit(1)
    else:
        print("✓ SUCCESS — all required fields present")


asyncio.run(main())

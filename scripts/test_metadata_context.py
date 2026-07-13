"""
Smoke test: verify qwen2.5:7b now returns chapter and topic.
Tests a physics question with subject context in the prompt.
"""
import asyncio, json, sys, os
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("LLM_MODEL", "qwen2.5:7b")

from app.services.metadata_generator import generate_metadata
from app.services.llm import get_llm_client
from app.services.question_builder.base import Question

async def main():
    llm = get_llm_client()
    print(f"Provider : {type(llm).__name__}")

    q = Question(
        question_number=1,
        stem_md=r"A body of mass 2 kg is moving with velocity $10\ m/s$. A force of 5 N acts on it for 4 s. Find the final kinetic energy of the body.",
        options={"A": "200 J", "B": "400 J", "C": "450 J", "D": "500 J"},
        answer="C",
        section_type="mcq",
    )

    print("Calling LLM with subject context...")
    meta = await generate_metadata(q, llm, exam_name="JEE Main", subject="physics")

    print(f"\nchapter     : {meta.chapter}")
    print(f"topic       : {meta.topic}")
    print(f"subtopic    : {meta.subtopic}")
    print(f"difficulty  : {meta.difficulty}")
    print(f"concepts    : {meta.concepts}")
    print(f"raw         : {json.dumps(meta.raw_response, indent=2)}")

    ok = meta.chapter and meta.topic and meta.difficulty
    print("\nSUCCESS - chapter and topic are populated" if ok else "\nFAILED - chapter or topic still null")
    sys.exit(0 if ok else 1)

asyncio.run(main())

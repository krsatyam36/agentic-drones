from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from src.llm.llm_node import LLMNode
from src.validator.validator import validate_mission

logger = logging.getLogger("cli")


def run_pipeline(prompt: str, backend: str = "ollama",
                 model: str = None, save_path: str = None) -> bool:
    node = LLMNode(backend=backend, model=model)

    logger.info(f"Prompt: '{prompt}'")
    print(f"\n{'=' * 60}")
    print(f"PROMPT: {prompt}")
    print(f"{'=' * 60}\n")

    raw_json = node.generate(prompt)
    print(f"[LLM RAW OUTPUT]\n{raw_json}\n")

    def llm_callback(p, raw, errors):
        print(f"[RE-PROMPT] Fixing errors: {errors}")
        return node.generate(p, errors)

    result = validate_mission(raw_json, prompt, llm_callback=llm_callback)

    if result.valid:
        print(f"[VALIDATOR] PASS (layer {result.layer})")
        mission = result.mission.model_dump()
        print(json.dumps(mission, indent=2))

        if save_path:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w") as f:
                json.dump(mission, f, indent=2)
            print(f"\n[SAVED] Mission written to {save_path}")

        return True
    else:
        print(f"[VALIDATOR] FAIL (layer {result.layer})")
        for err in result.errors:
            print(f"  - {err}")
        return False


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger.setLevel(logging.WARNING)

    backend = "ollama"
    model = None

    print("Agentic Drones — Agentic Drone Pipeline")
    print("Type 'exit' to quit\n")

    while True:
        try:
            prompt = input(">>> Enter command: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            break

        save_path = "output/mission.json"
        run_pipeline(prompt, backend=backend, model=model, save_path=save_path)

        print(f"\nTo fly this mission: python -m src.executor.executor --mission {save_path}\n")


if __name__ == "__main__":
    main()

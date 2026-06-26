from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("llm_node")

SYSTEM_PROMPT = """You are a drone mission planner. Your ONLY job is to output valid mission JSON.
The JSON must match this schema exactly — no markdown, no explanations, only JSON.

ACTION VOCABULARY (whitelist):
- TAKEOFF: requires "altitude" (1-50m)
- GOTO: requires "waypoint" with x,y,z coordinates (in meters, local NED frame)
- LOITER: requires "loiter_seconds" (0-300s)
- RETURN_TO_LAUNCH: no extra fields
- LAND: no extra fields

RULES (you MUST follow):
1. Mission MUST start with TAKEOFF
2. Mission MUST end with LAND or RETURN_TO_LAUNCH
3. Altitude must be between 1 and 50 meters
4. Speed must be between 0.5 and 15 m/s
5. Waypoints must be within reasonable distance of each other
6. Maximum 50 actions per mission

EXAMPLE:
Input: "Patrol the perimeter loop twice at 15 metres"
Output:
{
  "mission_id": "patrol_001",
  "target": "drone1",
  "actions": [
    {"type": "TAKEOFF", "altitude": 15, "speed": 5},
    {"type": "GOTO", "waypoint": {"x": 50, "y": 0, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 50, "y": 50, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 0, "y": 50, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 0, "y": 0, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 50, "y": 0, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 50, "y": 50, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 0, "y": 50, "z": -15}, "speed": 10},
    {"type": "GOTO", "waypoint": {"x": 0, "y": 0, "z": -15}, "speed": 10},
    {"type": "LAND"}
  ]
}"""


class LLMNode:
    def __init__(self, backend: str = "ollama", model: str = None,
                 api_key: Optional[str] = None):
        self.backend = backend
        self.model = model or self._default_model()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def _default_model(self) -> str:
        if self.backend == "ollama":
            return "llama3.2"
        return "gpt-4o-mini"

    def generate(self, prompt: str, previous_errors: Optional[list[str]] = None) -> str:
        if self.backend == "ollama":
            return self._generate_ollama(prompt, previous_errors)
        elif self.backend == "openai":
            return self._generate_openai(prompt, previous_errors)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _generate_ollama(self, prompt: str, previous_errors: Optional[list[str]] = None) -> str:
        try:
            import requests
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            if previous_errors:
                messages.append({
                    "role": "user",
                    "content": f"Your previous output had errors: {previous_errors}. Fix the JSON."
                })

            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            return self._extract_json(content)
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return "{}"

    def _generate_openai(self, prompt: str, previous_errors: Optional[list[str]] = None) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            if previous_errors:
                messages.append({
                    "role": "user",
                    "content": f"Fix these errors: {previous_errors}"
                })

            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = resp.choices[0].message.content
            return self._extract_json(content)
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return "{}"

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = next(i for i, l in enumerate(lines) if "```" in l) + 1
            end = next(i for i in range(start, len(lines)) if "```" in lines[i])
            text = "\n".join(lines[start:end])
        return text.strip()


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    backend = os.environ.get("LLM_BACKEND", "ollama")
    model = os.environ.get("LLM_MODEL", None)

    node = LLMNode(backend=backend, model=model)

    import sys
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter command: ")

    logger.info(f"Generating mission for: '{prompt}'")
    raw = node.generate(prompt)
    print(raw)


if __name__ == "__main__":
    main()

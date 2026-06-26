from __future__ import annotations

import json
import logging
import sys
from typing import Optional

from pydantic import ValidationError

from src.schema.mission import MissionPlan

logger = logging.getLogger("validator")

MAX_RETRIES = 3


class ValidationResult:
    def __init__(self, valid: bool, mission: Optional[MissionPlan] = None,
                 errors: Optional[list[str]] = None, layer: int = 0):
        self.valid = valid
        self.mission = mission
        self.errors = errors or []
        self.layer = layer

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "layer": self.layer,
        }


def validate_layer1_structure(raw_json: str) -> ValidationResult:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return ValidationResult(valid=False, errors=[f"Layer 1: Invalid JSON — {e}"], layer=1)

    if not isinstance(data, dict):
        return ValidationResult(valid=False, errors=["Layer 1: JSON root must be an object"], layer=1)

    if "actions" not in data:
        return ValidationResult(valid=False, errors=["Layer 1: Missing required field 'actions'"], layer=1)

    if not isinstance(data["actions"], list) or len(data["actions"]) == 0:
        return ValidationResult(valid=False, errors=["Layer 1: 'actions' must be a non-empty list"], layer=1)

    return ValidationResult(valid=True, layer=1)


def validate_layer2_semantic(data: dict) -> ValidationResult:
    try:
        mission = MissionPlan(**data)
        return ValidationResult(valid=True, mission=mission, layer=2)
    except ValidationError as e:
        errors = [f"Layer 2: {err['msg']} (field: {'.'.join(str(p) for p in err['loc'])})"
                  for err in e.errors()]
        return ValidationResult(valid=False, errors=errors, layer=2)


def validate_layer3_reprompt(raw_json: str, prompt: str,
                              llm_callback=None) -> ValidationResult:
    result1 = validate_layer1_structure(raw_json)
    if not result1.valid:
        logger.warning(f"Layer 1 failed: {result1.errors}")

    if result1.valid:
        data = json.loads(raw_json)
        result2 = validate_layer2_semantic(data)
        if result2.valid:
            return result2
        logger.warning(f"Layer 2 failed: {result2.errors}")
    else:
        data = None
        result2 = ValidationResult(valid=False, errors=result1.errors, layer=1)

    if llm_callback is None or result1.valid:
        return result2

    retries = 0
    current_raw = raw_json
    while retries < MAX_RETRIES:
        logger.info(f"Re-prompting LLM for correction (attempt {retries + 1}/{MAX_RETRIES})...")
        try:
            current_raw = llm_callback(prompt, current_raw, result2.errors)
        except Exception as e:
            logger.error(f"Re-prompt failed: {e}")
            break

        result1 = validate_layer1_structure(current_raw)
        if not result1.valid:
            retries += 1
            continue

        data = json.loads(current_raw)
        result2 = validate_layer2_semantic(data)
        if result2.valid:
            logger.info("Re-prompt succeeded")
            return result2
        retries += 1

    return ValidationResult(
        valid=False,
        errors=[f"Layer 3: Failed after {MAX_RETRIES} re-prompt attempts. Last errors: {result2.errors}"],
        layer=3,
    )


def validate_mission(raw_json: str, prompt: str = "",
                     llm_callback=None) -> ValidationResult:
    return validate_layer3_reprompt(raw_json, prompt, llm_callback)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m src.validator.validator <mission.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r") as f:
        raw = f.read()

    result = validate_mission(raw)
    if result.valid:
        print(json.dumps(result.mission.model_dump(), indent=2))
        logger.info("VALID: Mission passed all validation layers")
    else:
        for err in result.errors:
            logger.error(err)
        sys.exit(1)


if __name__ == "__main__":
    main()

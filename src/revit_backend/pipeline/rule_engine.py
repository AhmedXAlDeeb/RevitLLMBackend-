from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


VALID_OPERATORS = {">", ">=", "<", "<=", "==", "!="}


@dataclass
class RuleEvaluation:
    element_id: str
    element_name: str
    property_name: str
    operator: str
    expected_value: float
    actual_value: float | None
    status: str
    message: str
    rule: Dict[str, Any]


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _compare(actual: float, operator: str, expected: float) -> bool:
    if operator == ">":
        return actual > expected
    if operator == ">=":
        return actual >= expected
    if operator == "<":
        return actual < expected
    if operator == "<=":
        return actual <= expected
    if operator == "==":
        return actual == expected
    if operator == "!=":
        return actual != expected
    raise ValueError(f"Unsupported operator: {operator}")


def _normalize_property_name(property_name: str) -> str:
    normalized = property_name.strip().lower().replace(" ", "_")
    aliases = {
        "room_area": "area",
        "min_area": "area",
        "ceiling_height": "height",
    }
    return aliases.get(normalized, normalized)


def evaluate_rules_for_elements(elements: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    manual_count = 0

    for element in elements:
        element_id = str(element.get("id", "unknown"))
        element_name = str(element.get("name") or element_id)

        for rule in rules:
            element_type = str(rule.get("element", "room")).strip().lower()
            if element_type not in {"room", "space", "element", "any"}:
                continue

            property_name = _normalize_property_name(str(rule.get("property", "")))
            operator = str(rule.get("operator", "")).strip()
            expected_value = _to_float(rule.get("value"))

            if not property_name or operator not in VALID_OPERATORS or expected_value is None:
                findings.append(
                    {
                        "element_id": element_id,
                        "element_name": element_name,
                        "status": "needs-manual-review",
                        "reason": "Invalid or incomplete rule payload.",
                        "rule": rule,
                    }
                )
                manual_count += 1
                continue

            actual_value = _to_float(element.get(property_name))
            if actual_value is None:
                findings.append(
                    {
                        "element_id": element_id,
                        "element_name": element_name,
                        "status": "needs-manual-review",
                        "reason": f"Property '{property_name}' is missing on BIM element.",
                        "rule": rule,
                    }
                )
                manual_count += 1
                continue

            is_pass = _compare(actual_value, operator, expected_value)
            status = "pass" if is_pass else "fail"
            if is_pass:
                pass_count += 1
            else:
                fail_count += 1

            findings.append(
                {
                    "element_id": element_id,
                    "element_name": element_name,
                    "status": status,
                    "reason": f"Checked {property_name} {operator} {expected_value} ({actual_value}).",
                    "actual_value": actual_value,
                    "rule": rule,
                }
            )

    failed_ids = [f["element_id"] for f in findings if f.get("status") == "fail"]
    passed_ids = [f["element_id"] for f in findings if f.get("status") == "pass"]

    return {
        "summary": {
            "total_elements": len(elements),
            "total_rules": len(rules),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "manual_review_count": manual_count,
        },
        "findings": findings,
        "visualization": {
            "failed_ids": failed_ids,
            "passed_ids": passed_ids,
            "palette": {
                "fail": "#D32F2F",
                "pass": "#2E7D32",
                "manual": "#F9A825",
            },
        },
    }

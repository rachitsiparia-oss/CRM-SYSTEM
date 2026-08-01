"""Small, structural safety checks — GROWTH_AND_INTELLIGENCE.md section
14.8: "output must be schema-validated," "validation failure must not
mutate records." No `jsonschema` dependency is added for this lightweight,
required-field-only check — the output schemas here are simple enough
(flat objects, no nested arrays of objects) that a hand-rolled check is
both sufficient and easier to audit than pulling in a validation library
for five small schemas.
"""

# GROWTH_AND_INTELLIGENCE.md section 14.10: "restrict HR-related AI
# features." None of the five capabilities this phase wires touch staff
# HR data, so this set is empty today — it exists as the enforcement point
# a future HR-facing capability (e.g. a staff-performance summary) must
# register itself in, gated by `ai.analytics.hr_sensitive`.
HR_SENSITIVE_FEATURE_CODES: frozenset[str] = frozenset()


def requires_hr_sensitive_permission(feature_code: str) -> bool:
    return feature_code in HR_SENSITIVE_FEATURE_CODES


def validate_structured_output(
    schema: dict[str, object] | None, data: dict[str, object] | None
) -> bool:
    if schema is None:
        return True
    if data is None:
        return False
    required = schema.get("required", [])
    if not isinstance(required, list):
        return True
    return all(key in data for key in required)

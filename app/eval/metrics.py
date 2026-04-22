"""Metric helpers for the offline CoursePilot evaluation runner."""

from __future__ import annotations

from typing import Any


def summarize_eval_results(case_results: list[dict[str, Any]]) -> dict[str, float]:
    """Summarize machine-readable metrics from case execution results."""
    total_cases = len(case_results)
    successful_cases = sum(1 for result in case_results if result["status"] == "passed")
    total_plans = sum(len(result.get("plans", [])) for result in case_results)
    prerequisite_valid_plans = sum(result.get("prerequisite_valid_plans", 0) for result in case_results)
    conflict_free_plans = sum(result.get("conflict_free_plans", 0) for result in case_results)
    graduation_checked_plans = sum(result.get("graduation_checked_plans", 0) for result in case_results)
    output_schema_successes = sum(1 for result in case_results if result.get("schema_valid", False))
    tool_failures = sum(1 for result in case_results if result["status"] == "failed")
    refine_case_results = [result for result in case_results if result.get("mode") == "refine"]
    graceful_failures = sum(1 for result in refine_case_results if result.get("graceful_failure"))
    refinement_applied = sum(1 for result in refine_case_results if result.get("refinement_applied"))
    memory_writes = sum(1 for result in refine_case_results if result.get("memory_written"))

    if total_cases == 0:
        return {
            "case_count": 0.0,
            "schema_success_rate": 0.0,
            "prerequisite_correctness_rate": 0.0,
            "schedule_conflict_correctness_rate": 0.0,
            "graduation_requirement_check_rate": 0.0,
            "tool_failure_rate": 0.0,
            "refine_case_count": 0.0,
            "graceful_failure_rate": 0.0,
            "refinement_applied_rate": 0.0,
            "memory_written_rate": 0.0,
            "case_pass_rate": 0.0,
        }

    plan_denominator = float(total_plans) if total_plans else 1.0
    refine_denominator = float(len(refine_case_results)) if refine_case_results else 1.0
    return {
        "case_count": float(total_cases),
        "schema_success_rate": round(output_schema_successes / total_cases, 4),
        "prerequisite_correctness_rate": round(prerequisite_valid_plans / plan_denominator, 4),
        "schedule_conflict_correctness_rate": round(conflict_free_plans / plan_denominator, 4),
        "graduation_requirement_check_rate": round(graduation_checked_plans / plan_denominator, 4),
        "tool_failure_rate": round(tool_failures / total_cases, 4),
        "refine_case_count": float(len(refine_case_results)),
        "graceful_failure_rate": round(graceful_failures / refine_denominator, 4),
        "refinement_applied_rate": round(refinement_applied / refine_denominator, 4),
        "memory_written_rate": round(memory_writes / refine_denominator, 4),
        "case_pass_rate": round(successful_cases / total_cases, 4),
    }

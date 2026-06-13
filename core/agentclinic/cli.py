"""CLI entry points.

  analyze <trace.json>   run the full pipeline, emit report (md + json)
  budget  <input.json>   run budget guardian on one input, emit assessment
  golden  <dir>          regression-run all *.golden.json (the CI gate);
                         dispatches per file: "kind":"budget" -> budget pipeline,
                         otherwise -> trace pipeline (the default, back-compat)

Exit codes: 0 ok / 1 failures or internal error / 2 input schema error."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .budget import assess as budget_assess
from .budget import to_markdown as budget_to_markdown
from .detect import load_rules, run_detectors
from .normalize import load_trace_file, normalize
from .report import build_report, to_markdown
from .score import load_scorecard, score
from .validate import TraceSchemaError


def analyze_pipeline(trace: dict, rules_path=None, scorecard_path=None) -> dict:
    trace, gaps = normalize(trace)
    rules = load_rules(rules_path)
    findings = run_detectors(trace, gaps, rules)
    result = score(findings, load_scorecard(scorecard_path))
    return build_report(trace, gaps, findings, result)


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        trace = load_trace_file(args.trace)
        report = analyze_pipeline(trace, args.rules, args.scorecard)
    except TraceSchemaError as e:
        print(f"SCHEMA ERROR (input rejected, nothing analyzed):\n{e}",
              file=sys.stderr)
        return 2
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        print(f"INPUT ERROR (could not load input or config, nothing "
              f"analyzed): {e}", file=sys.stderr)
        return 2

    md = to_markdown(report)
    if args.report:
        Path(args.report).write_text(md, encoding="utf-8")
        print(f"report written: {args.report}")
    if args.findings:
        Path(args.findings).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"findings JSON written: {args.findings}")
    if not args.report and not args.findings:
        print(md)
    sc = report["score"]
    print(f"== score {sc['value']} / level {sc['level']} / "
          f"{len(report['sections']['2']['findings'])} finding(s) ==")
    return 0


def _approx(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def _compare_golden(golden: dict, report: dict) -> list[str]:
    """Compare actual output against a golden file. finding_id values are
    metadata and not compared; patterns, severities, confidences, evidence
    event ids, waste tokens, and the score are.

    The pipeline is deterministic, so comparison is exact by default; a
    golden file may declare {"tolerances": {"confidence": x, "score": y}}
    to loosen it deliberately — slack is opt-in config, never hardcoded."""
    problems: list[str] = []
    tolerances = golden.get("tolerances", {})
    conf_tol = tolerances.get("confidence", 0.0)
    score_tol = tolerances.get("score", 0.0)
    actual = report["sections"]["2"]["findings"]
    expected = golden.get("expected_findings", [])

    exp_patterns = sorted(f["pattern"] for f in expected)
    act_patterns = sorted(f["pattern"] for f in actual)
    if exp_patterns != act_patterns:
        problems.append(f"patterns: expected {exp_patterns}, got {act_patterns}")
        return problems  # pattern mismatch makes per-finding checks meaningless

    by_pattern: dict[str, list[dict]] = {}
    for f in actual:
        by_pattern.setdefault(f["pattern"], []).append(f)
    for exp in expected:
        candidates = by_pattern.get(exp["pattern"], [])
        exp_ids = {s["trace_event_id"] for s in exp["evidence_spans"]}
        match = next(
            (c for c in candidates
             if {s["trace_event_id"] for s in c["evidence_spans"]} == exp_ids),
            None,
        )
        if match is None:
            problems.append(
                f"{exp['pattern']}: no finding with evidence {sorted(exp_ids)}")
            continue
        candidates.remove(match)  # consume: one actual finding satisfies one expectation
        if match["severity"] != exp["severity"]:
            problems.append(f"{exp['pattern']}: severity {match['severity']} "
                            f"!= expected {exp['severity']}")
        if not _approx(match["confidence"], exp["confidence"], conf_tol):
            problems.append(f"{exp['pattern']}: confidence {match['confidence']} "
                            f"!= expected {exp['confidence']}")
        exp_waste = exp.get("estimated_waste", {}).get("tokens", "skip")
        if exp_waste != "skip" and match["estimated_waste"]["tokens"] != exp_waste:
            problems.append(f"{exp['pattern']}: waste "
                            f"{match['estimated_waste']['tokens']} "
                            f"!= expected {exp_waste}")

    exp_score = golden.get("expected_score")
    if exp_score:
        sc = report["score"]
        if sc["level"] != exp_score["level"]:
            problems.append(f"level {sc['level']} != expected {exp_score['level']}")
        if not _approx(sc["value"], exp_score["value"], score_tol):
            problems.append(f"score {sc['value']} != expected {exp_score['value']}")
    return problems


def cmd_budget(args: argparse.Namespace) -> int:
    try:
        with open(args.input, encoding="utf-8") as f:
            inp = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        print(f"INPUT ERROR: {e}", file=sys.stderr)
        return 2
    assessment = budget_assess(inp, _load_budget_rules(args.budget_rules))
    md = budget_to_markdown(assessment)
    if args.out:
        Path(args.out).write_text(
            json.dumps(assessment, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"assessment JSON written: {args.out}")
    else:
        print(md)
    print(f"== level {assessment['warning_level']} / "
          f"action {assessment['recommended_action']} ==")
    return 0


def _load_budget_rules(path: str | None) -> dict | None:
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _compare_budget_golden(golden: dict, assessment: dict) -> list[str]:
    """Compare budget assessment against expected fields. Numeric fields use
    per-golden tolerance (default 0); level + action are exact match."""
    problems: list[str] = []
    expected = golden.get("expected", {})
    tolerances = golden.get("tolerances", {})
    for key, exp in expected.items():
        actual = assessment.get(key)
        if isinstance(exp, (int, float)) and exp is not None and actual is not None:
            tol = tolerances.get(key, 0.0)
            if abs(actual - exp) > tol:
                problems.append(f"{key}: got {actual}, expected {exp} "
                                f"(tol {tol})")
        else:
            if actual != exp:
                problems.append(f"{key}: got {actual!r}, expected {exp!r}")
    return problems


def cmd_golden(args: argparse.Namespace) -> int:
    golden_dir = Path(args.dir)
    files = sorted(golden_dir.glob("*.golden.json"))
    if not files:
        print(f"no *.golden.json found in {golden_dir}", file=sys.stderr)
        return 1
    budget_rules = _load_budget_rules(args.budget_rules)
    failures = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                golden = json.load(f)
            if golden.get("kind") == "budget":
                assessment = budget_assess(golden["input"], budget_rules)
                problems = _compare_budget_golden(golden, assessment)
                summary = (f"level {assessment['warning_level']}, "
                           f"action {assessment['recommended_action']}")
            else:
                report = analyze_pipeline(golden["input_trace"],
                                          args.rules, args.scorecard)
                problems = _compare_golden(golden, report)
                sc = report["score"]
                n = len(report["sections"]["2"]["findings"])
                summary = (f"score {sc['value']}, {sc['level']}, "
                           f"{n} finding(s)")
        except Exception as e:  # noqa: BLE001 — a crash on a golden is a failure,
            # recorded as FAIL; the rest of the suite must still run
            problems = [f"pipeline crashed: {type(e).__name__}: {e}"]
            summary = ""
        if problems:
            failures += 1
            print(f"FAIL  {path.name}")
            for p in problems:
                print(f"      - {p}")
        else:
            print(f"PASS  {path.name}  ({summary})")
    print(f"== {len(files) - failures}/{len(files)} golden green ==")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentclinic",
        description="Evidence-bound forensic analysis of AI agent traces.")
    parser.add_argument("--rules", help="override detect-rules.json path")
    parser.add_argument("--scorecard", help="override scorecard.json path")
    parser.add_argument("--budget-rules", help="override budget_rules.json path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_an = sub.add_parser("analyze", help="analyze one trace file")
    p_an.add_argument("trace", help="trace JSON (golden files auto-unwrap)")
    p_an.add_argument("--report", help="write markdown report to this path")
    p_an.add_argument("--findings", help="write full report JSON to this path")
    p_an.set_defaults(func=cmd_analyze)

    p_bg = sub.add_parser("budget", help="run budget guardian on one input")
    p_bg.add_argument("input", help="budget input JSON")
    p_bg.add_argument("--out", help="write assessment JSON to this path")
    p_bg.set_defaults(func=cmd_budget)

    p_go = sub.add_parser("golden", help="run golden regression suite "
                          "(trace + budget auto-dispatch by 'kind' field)")
    p_go.add_argument("dir", help="directory containing *.golden.json")
    p_go.set_defaults(func=cmd_golden)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

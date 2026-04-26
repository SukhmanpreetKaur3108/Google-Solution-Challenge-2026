#!/usr/bin/env python3
"""
run_demo.py — End-to-end PoF-AI demo orchestrator.

Simulates a recruiter using PoF-AI live:
  1. Loads three pre-baked applicant profiles
  2. POSTs each to /score
  3. Fetches resulting certificates
  4. Prints a side-by-side comparison table
  5. Opens dashboard URLs in the browser

Run:
    python demo/run_demo.py [--api-url http://localhost:8080] [--open-browser]
"""

from __future__ import annotations

import argparse
import json
import os
import time
import webbrowser
from typing import Any

import requests

BASE_URL = os.environ.get("POF_AI_API_URL", "http://localhost:8080")
DASHBOARD_URL = os.environ.get("POF_AI_DASHBOARD_URL", "http://localhost:5173")
API_KEY = os.environ.get("API_KEY", "demo")

# ── Pre-baked applicant profiles ─────────────────────────────────────────────

APPLICANTS = [
    {
        "_label": "Majority Group",
        "applicant": {
            "name": "James Smith",
            "age": 32,
            "gender": "male",
            "ethnicity": "white",
            "education": "master",
            "years_experience": 7,
            "skills": ["python", "sql", "machine_learning", "leadership", "data_analysis"],
            "current_employer": "Google",
        },
        "job_description": "Senior Data Scientist — 5+ yrs exp, Python, ML required",
        "model_id": "default",
    },
    {
        "_label": "Minority Group (Same Quals)",
        "applicant": {
            "name": "Lakisha Jones",
            "age": 32,
            "gender": "female",
            "ethnicity": "black",
            "education": "master",
            "years_experience": 7,
            "skills": ["python", "sql", "machine_learning", "leadership", "data_analysis"],
            "current_employer": "Google",
        },
        "job_description": "Senior Data Scientist — 5+ yrs exp, Python, ML required",
        "model_id": "default",
    },
    {
        "_label": "Adversarial Near-Twin",
        "applicant": {
            "name": "Maria Rodriguez",
            "age": 33,
            "gender": "female",
            "ethnicity": "hispanic",
            "education": "master",
            "years_experience": 7,
            "skills": ["python", "sql", "machine_learning", "leadership", "data_analysis"],
            "current_employer": "Microsoft",
        },
        "job_description": "Senior Data Scientist — 5+ yrs exp, Python, ML required",
        "model_id": "default",
    },
]

# ── ANSI colours ──────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{RESET}"


def score_color(val: float, good_high: bool = True) -> str:
    if good_high:
        return GREEN if val >= 0.8 else YELLOW if val >= 0.6 else RED
    else:
        return GREEN if val <= 0.2 else YELLOW if val <= 0.35 else RED


# ── API calls ─────────────────────────────────────────────────────────────────

def score_applicant(payload: dict[str, Any]) -> dict[str, Any]:
    label = payload.pop("_label")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{BASE_URL}/score", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        result["_label"] = label
        return result
    except requests.RequestException as e:
        print(color(f"  ⚠️  API call failed for {label}: {e}", YELLOW))
        return {
            "_label": label,
            "should_hire": None,
            "candidate_score": None,
            "certificate_status": "ERROR",
            "certificate_id": "N/A",
            "verification_url": "#",
            "fairness": {
                "statistical_score": 0,
                "causal_counterfactual_score": 0,
                "adversarial_flip_rate": 1,
                "regulatory_compliance_percent": 0,
                "intersectional_worst_subgroup": "N/A",
                "regulatory_failures": [],
            },
        }


# ── Display ───────────────────────────────────────────────────────────────────

def print_banner():
    print()
    print(color("╔══════════════════════════════════════════════════════════╗", CYAN))
    print(color("║          PoF-AI — Proof-of-Fairness AI  Demo            ║", CYAN))
    print(color("║       Google Solution Challenge 2026                    ║", CYAN))
    print(color("╚══════════════════════════════════════════════════════════╝", CYAN))
    print()


def print_table(results: list[dict[str, Any]]):
    col_w = 28
    headers = ["Metric"] + [r["_label"] for r in results]
    sep = "─" * (10 + col_w * len(results))

    def row(label: str, *values: str) -> str:
        return f"  {label:<24}" + "".join(f"{v:^{col_w}}" for v in values)

    print(color(sep, GRAY))
    print(color(row(*headers), BOLD))
    print(color(sep, GRAY))

    for r in results:
        f = r.get("fairness", {})

        decision = ("✅ HIRE" if r.get("should_hire") else "❌ REJECT") if r.get("should_hire") is not None else "⚠️  ERROR"
        score_pct = f"{r['candidate_score']*100:.1f}%" if r.get("candidate_score") is not None else "N/A"
        status = r.get("certificate_status", "?")

        stat  = f.get("statistical_score", 0)
        causal = f.get("causal_counterfactual_score", 0)
        flip  = f.get("adversarial_flip_rate", 0)
        reg   = f.get("regulatory_compliance_percent", 0)

        stat_s  = color(f"{stat*100:.1f}%", score_color(stat))
        causal_s = color(f"{causal*100:.1f}%", score_color(causal))
        flip_s  = color(f"{flip*100:.1f}%", score_color(flip, good_high=False))
        reg_s   = color(f"{reg:.1f}%", score_color(reg / 100))
        status_c = color(status, GREEN if status == "FAIR" else RED if status == "BIASED" else YELLOW)

    # Print each metric as a row
    def vals(metric_fn):
        return [metric_fn(r) for r in results]

    print(row("Decision",          *[("✅ HIRE" if r.get("should_hire") else "❌ REJECT") if r.get("should_hire") is not None else "⚠️  ERROR" for r in results]))
    print(row("Candidate Score",   *[f"{r['candidate_score']*100:.1f}%" if r.get("candidate_score") is not None else "N/A" for r in results]))
    print(row("Cert Status",       *[r.get("certificate_status","?") for r in results]))
    print(color(sep, GRAY))
    print(row("Statistical Score", *[f"{r.get('fairness',{}).get('statistical_score',0)*100:.1f}%" for r in results]))
    print(row("Causal CF Score",   *[f"{r.get('fairness',{}).get('causal_counterfactual_score',0)*100:.1f}%" for r in results]))
    print(row("Adversarial Flip%", *[f"{r.get('fairness',{}).get('adversarial_flip_rate',0)*100:.1f}%" for r in results]))
    print(row("Regulatory %",      *[f"{r.get('fairness',{}).get('regulatory_compliance_percent',0):.1f}%" for r in results]))
    print(row("Worst Subgroup",    *[r.get('fairness',{}).get('intersectional_worst_subgroup','N/A') for r in results]))
    print(color(sep, GRAY))
    print(row("Certificate ID",    *[r.get("certificate_id","N/A")[:16]+"…" for r in results]))
    print()


def print_insights(results: list[dict[str, Any]]):
    print(color("  🔍 Key Findings:", BOLD))
    scores = [r.get("candidate_score") for r in results if r.get("candidate_score") is not None]
    if len(scores) >= 2:
        delta = abs(scores[0] - scores[1]) * 100
        if delta > 5:
            print(color(f"  ⚠️  Score gap between Majority and Minority group: {delta:.1f}pp on IDENTICAL qualifications", RED))
        else:
            print(color(f"  ✅ Score gap: {delta:.1f}pp — within acceptable range", GREEN))

    for r in results:
        failures = r.get("fairness", {}).get("regulatory_failures", [])
        if failures:
            print(color(f"  ❌ [{r['_label']}] Regulatory failures: {', '.join(failures)}", RED))
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PoF-AI end-to-end demo")
    parser.add_argument("--api-url",      default=BASE_URL,      help="Backend API URL")
    parser.add_argument("--dashboard-url",default=DASHBOARD_URL, help="Dashboard URL")
    parser.add_argument("--open-browser", action="store_true",    help="Open dashboard in browser")
    args = parser.parse_args()

    global BASE_URL, DASHBOARD_URL
    BASE_URL      = args.api_url
    DASHBOARD_URL = args.dashboard_url

    print_banner()

    print(color("  Submitting 3 applicant profiles to PoF-AI…", CYAN))
    print()

    results = []
    for applicant_data in APPLICANTS:
        label = applicant_data["_label"]
        print(f"  → Scoring: {color(label, BOLD)}")
        t0 = time.time()
        result = score_applicant(dict(applicant_data))  # copy to avoid mutation
        elapsed = time.time() - t0
        status = result.get("certificate_status", "?")
        print(f"    Certificate: {result.get('certificate_id','N/A')[:24]}…  [{elapsed:.2f}s]  {status}")
        results.append(result)

    print()
    print(color("  Side-by-Side Comparison", BOLD))
    print()
    print_table(results)
    print_insights(results)

    # Print verification URLs
    print(color("  Certificate Verification URLs:", BOLD))
    for r in results:
        url = r.get("verification_url", "#")
        print(f"  {r['_label']:<32} {color(url, CYAN)}")
    print()

    # Open browser
    if args.open_browser:
        print(color("  Opening dashboard in browser…", GRAY))
        for r in results:
            cert_id = r.get("certificate_id", "")
            if cert_id and cert_id != "N/A":
                webbrowser.open(f"{DASHBOARD_URL}/cert/{cert_id}")
                time.sleep(0.5)
        webbrowser.open(f"{DASHBOARD_URL}/dashboard")

    print(color("  Demo complete! 🎉", GREEN))
    print()


if __name__ == "__main__":
    main()

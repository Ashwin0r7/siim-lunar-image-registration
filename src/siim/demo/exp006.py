"""Component-ablation evidence for the demo (EXP-006).

The question every judge asks of an architecture is *why this one?* — and the
honest answer for most registration systems is "we picked a good matcher".
This project's answer is different: the matcher is a swappable engine and the
protocol around it is the contribution (ADR-0001). Until 2026-09-21 that answer
rested on a **33× protocol effect measured on SAR-optical imagery in a single
preprint**, which is a citation, not a result.

EXP-006 replaced it with a measurement on 42 real lunar pairs, and this panel
carries it — including the part that keeps it honest: the claim is bounded to
*at least one protocol step outweighs a matcher replacement*, because the step
used is the one whose both levels happened to be recorded.

A separate module for the same reason as :mod:`siim.demo.exp013` and
:mod:`siim.demo.chandrayaan2`: recorded demo paths import
:mod:`siim.demo.evidence`, and the project's rule is to add a module rather
than edit one those artefacts depend on.
"""

from __future__ import annotations

from typing import Any

from .evidence import EXPERIMENTS, ROOT, DemoDataMissing, _read

__all__ = ["exp006_evidence", "exp006_status", "EXP006_SOURCES"]

EXP006_ARTEFACT = EXPERIMENTS / "EXP-006" / "exp006_results.json"

EXP006_SOURCES = [
    "experiments/EXP-006/exp006_results.json",
    "experiments/REAL-DATA-07/real_data_07_results_nue.json",
]

EXP006_SUMMARY = (
    "On the same 42 real lunar pairs, correcting one step of the protocol "
    "changes 2.2x as many outcomes as replacing the entire feature matcher -- "
    "and it changes every one of them for the better, where swapping matchers "
    "trades six gains against five losses. A protocol fix is monotone; a "
    "matcher swap is a trade."
)

EXP006_SCOPE = (
    "42 geometry-confirmed pairs, LRO NAC, Mare Serenitatis, two ground "
    "windows. One protocol step (orientation) against three matchers. Paired "
    "throughout; exact McNemar, because the discordant counts are single "
    "digits."
)

EXP006_NOT_CLAIMED = [
    "NOT the general thesis that the protocol matters more than the matcher. "
    "The step measured here is the ONE protocol component whose both levels "
    "happen to have been recorded, and they were recorded because a defect was "
    "found (E-037), not because an ablation was designed. The master plan "
    "rules the general claim unfalsifiable as phrased, and that still stands.",
    "NOT a claim about protocol components never ablated here: scale "
    "normalisation, tiling and the photometric arm are not in this design.",
    "NOT an accuracy claim. The outcome is a binary success under a frozen "
    "rule, corroborated against archive corner geometry at its own ~100 px "
    "floor, never verified -- no ground truth exists for these pairs.",
    "NOT significant on every matcher: the RootSIFT arm gives p = 0.0625, "
    "which does not clear 0.05 and arithmetically cannot with five "
    "one-directional discordant pairs. A limit of the sample, stated rather "
    "than rounded down.",
    "NO Chandrayaan-2 evidence in this panel, and nothing about non-mare "
    "terrain. The Chandrayaan-2 result is measured separately in the "
    "REAL-DATA-09 panel.",
]


def exp006_status() -> dict[str, Any]:
    missing = [str(p.relative_to(ROOT)).replace("\\", "/")
               for p in (EXP006_ARTEFACT,) if not p.exists()]
    return {"available": not missing, "missing": missing}


def exp006_evidence() -> dict[str, Any]:
    """EXP-006, assembled for the page. Raises if the artefact is absent."""
    status = exp006_status()
    if not status["available"]:
        raise DemoDataMissing(
            "component-ablation panel: missing " + ", ".join(status["missing"]))

    doc = _read(EXP006_ARTEFACT, "EXP-006 results",
                require=("criteria", "protocol_contrast", "matcher_contrast",
                         "success_rates"))
    crit = doc["criteria"]

    # the 2 x 3 factorial, as a table the page can render directly
    rates = []
    for key, v in doc["success_rates"].items():
        arm, eng = key.split(":", 1)
        rates.append({
            "arm": "quarter-turn" if arm == "original" else "north-up-east-right",
            "arm_key": arm, "engine": v["engine"], "engine_key": eng,
            "n_success": v["n_success"], "n": v["n"], "rate": v["rate"]})
    rates.sort(key=lambda r: (r["arm_key"] != "original", r["engine_key"]))

    protocol = [
        {"engine": e, "changed": c["n_changed"],
         "gained": c["fail_to_success"], "lost": c["success_to_fail"],
         "p_exact": c["p_exact_mcnemar"]}
        for e, c in doc["protocol_contrast"].items()
    ]
    matcher = [
        {"arm": "quarter-turn" if arm == "original" else "north-up-east-right",
         "swap": k.replace("_vs_", " ↔ "), "changed": c["n_changed"],
         "gained": c["fail_to_success"], "lost": c["success_to_fail"],
         "p_exact": c["p_exact_mcnemar"]}
        for arm, d in doc["matcher_contrast"].items() for k, c in d.items()
    ]

    total_protocol = sum(p["changed"] for p in protocol)
    gained_protocol = sum(p["gained"] for p in protocol)
    total_matcher = sum(m["changed"] for m in matcher)
    gained_matcher = sum(m["gained"] for m in matcher)

    s1 = crit["S1"]
    return {
        "n_pairs": doc["n_paired_pairs"],
        "protocol_step": doc["protocol_step"],
        "factorial": rates,
        "protocol_contrast": protocol,
        "matcher_contrast": matcher,
        "headline": {
            "mean_changed_protocol": s1["mean_changed_protocol"],
            "mean_changed_matcher": s1["mean_changed_matcher"],
            "ratio": (s1["mean_changed_protocol"] / s1["mean_changed_matcher"]
                      if s1["mean_changed_matcher"] else None),
            "protocol_flips": total_protocol,
            "protocol_improvements": gained_protocol,
            "protocol_regressions": total_protocol - gained_protocol,
            "matcher_flips": total_matcher,
            "matcher_improvements": gained_matcher,
            "matcher_regressions": total_matcher - gained_matcher,
            "best_protocol_p": crit["S2"]["best_protocol_p"],
            "best_matcher_p": crit["S2"]["best_matcher_p"],
        },
        "s5": {
            "met": bool(crit["S5"]["met"]),
            "papered_over_by_matcher": crit["S5"]["n_papered_over_by_matcher"],
            "rescued_by_protocol": crit["S5"]["n_rescued_by_protocol"],
        },
        "criteria": {k: {"met": bool(v["met"]), "statement": v["statement"]}
                     for k, v in crit.items()},
        "summary": EXP006_SUMMARY,
        "scope": EXP006_SCOPE,
        "not_claimed": list(EXP006_NOT_CLAIMED),
        "sources": list(EXP006_SOURCES),
    }

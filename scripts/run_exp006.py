"""EXP-006 — protocol vs matcher, as a component ablation, run as Part 1 froze it.

Does changing ONE step of the protocol move more pair outcomes than replacing
the entire feature matcher? Answerable with no re-run, because REAL-DATA-07 was
executed twice over the identical 42 pairs -- once with the Part 1 quarter-turn
orientation, once after E-037 found five census frames are mirror images --
giving a complete 2 x 2 paired factorial, with a third matcher on the amended
arm.

Every contrast is PAIRED on (window, frozenset(pair)) and tested with an exact
McNemar, because the arms share their pairs and an unpaired test would
overstate its own confidence.

    python scripts/run_exp006.py
"""

from __future__ import annotations

import json
import math
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RD07 = ROOT / "experiments" / "REAL-DATA-07"
OUT = ROOT / "experiments" / "EXP-006"

#: Part 1 section 2, fixed. "original" = quarter-turn; "amended" = north-up-east-right.
ARMS = {
    "original": {"RD03": "rows_rd03.json", "RD04": "rows_rd04.json"},
    "amended": {"RD03": "rows_rd03_nue.json", "RD04": "rows_rd04_nue.json"},
}
ENGINES = ("b1", "lg", "xf")
ENGINE_LABEL = {"b1": "B1 RootSIFT", "lg": "B4L DISK+LightGlue", "xf": "B4X XFeat"}
#: Both arms record these two; B4X exists only on the amended arm.
BOTH_ARM_ENGINES = ("b1", "lg")
S0_MIN_PAIRED = 40


def load(arm: str) -> dict[tuple[str, frozenset], dict[str, dict]]:
    """{(window, pair) -> {engine -> row}}, under run_exp012's exact filter."""
    out: dict[tuple[str, frozenset], dict[str, dict]] = {}
    for window, name in ARMS[arm].items():
        path = RD07 / name
        if not path.exists():
            raise SystemExit(f"missing recorded artefact: {path.relative_to(ROOT)}")
        for r in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            if r.get("excluded") or "reproduces_recorded" in r:
                continue
            eng = r.get("engine")
            if eng not in ENGINES:
                continue
            out.setdefault((window, unordered_pair(r)), {})[eng] = r
    return out


def unordered_pair(row: dict) -> frozenset:
    """The two frames of a row, as an unordered pair.

    The ORIGINAL arm's rows carry only ``edge``; the amended arm carries both
    ``edge`` and a sorted ``pair``. Pairing the arms needs the unordered set,
    so it is derived from ``edge`` on both and cross-checked against ``pair``
    wherever that exists -- deriving it from ``pair`` on one arm and ``edge``
    on the other is how E-036 turns into a silent mis-pairing.
    """
    ends = frozenset(row["edge"].split(" -> "))
    if len(ends) != 2:
        raise SystemExit(f"malformed edge: {row['edge']!r}")
    if "pair" in row and frozenset(row["pair"]) != ends:
        raise SystemExit(
            f"row disagrees with itself: pair={sorted(row['pair'])} but "
            f"edge={row['edge']!r}. Refusing to pair the arms on either.")
    return ends


def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact McNemar on the discordant counts b and c.

    The binomial test on b successes in b+c trials at p = 0.5. Exact rather
    than chi-square because the discordant counts here are single digits.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def contrast(a_rows, b_rows, keys, eng_a, eng_b):
    """Paired outcome contrast: how many pairs change, in which direction."""
    both = fail_to_succ = succ_to_fail = agree = 0
    flips = []
    for k in keys:
        ra = a_rows.get(k, {}).get(eng_a)
        rb = b_rows.get(k, {}).get(eng_b)
        if ra is None or rb is None:
            continue
        both += 1
        sa, sb = bool(ra.get("success")), bool(rb.get("success"))
        if sa == sb:
            agree += 1
        elif not sa and sb:
            fail_to_succ += 1
            flips.append({"pair": sorted(k[1]), "window": k[0], "direction": "fail->success"})
        else:
            succ_to_fail += 1
            flips.append({"pair": sorted(k[1]), "window": k[0], "direction": "success->fail"})
    changed = fail_to_succ + succ_to_fail
    return {
        "n_paired": both, "n_changed": changed, "n_agree": agree,
        "fail_to_success": fail_to_succ, "success_to_fail": succ_to_fail,
        "net": fail_to_succ - succ_to_fail,
        "p_exact_mcnemar": exact_mcnemar(fail_to_succ, succ_to_fail),
        "flips": flips,
    }


def successes(rows, keys, eng):
    return {k for k in keys if bool(rows.get(k, {}).get(eng, {}).get("success"))}


def main() -> None:
    out_path = OUT / "exp006_results.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.relative_to(ROOT)} exists (integrity rule 4)")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    orig, amend = load("original"), load("amended")
    keys = sorted(set(orig) & set(amend), key=lambda k: (k[0], sorted(k[1])))
    rd03 = [k for k in keys if k[0] == "RD03"]
    rd04 = [k for k in keys if k[0] == "RD04"]

    s0 = {"criterion": "S0",
          "statement": f">= {S0_MIN_PAIRED} pairs present in both arms, identical pair sets",
          "met": len(keys) >= S0_MIN_PAIRED,
          "n_paired": len(keys), "n_original_only": len(set(orig) - set(amend)),
          "n_amended_only": len(set(amend) - set(orig)),
          "n_rd03": len(rd03), "n_rd04": len(rd04)}
    if not s0["met"]:
        raise SystemExit(f"S0 FAILED: only {len(keys)} paired pairs; nothing is reported")

    # -- the two contrasts, on the identical pair set ----------------------
    protocol = {e: contrast(orig, amend, keys, e, e) for e in BOTH_ARM_ENGINES}
    matcher = {
        "original": {f"{a}_vs_{b}": contrast(orig, orig, keys, a, b)
                     for a, b in combinations(BOTH_ARM_ENGINES, 2)},
        "amended": {f"{a}_vs_{b}": contrast(amend, amend, keys, a, b)
                    for a, b in combinations(ENGINES, 2)},
    }

    mean_protocol = float(np.mean([protocol[e]["n_changed"] for e in BOTH_ARM_ENGINES]))
    matcher_changes = ([v["n_changed"] for v in matcher["original"].values()]
                       + [v["n_changed"] for v in matcher["amended"].values()])
    mean_matcher = float(np.mean(matcher_changes))
    s1 = {"criterion": "S1",
          "statement": "the orientation step flips more outcomes than the matcher swap",
          "met": mean_protocol > mean_matcher,
          "mean_changed_protocol": mean_protocol,
          "mean_changed_matcher": mean_matcher,
          "max_changed_matcher": float(max(matcher_changes)),
          "protocol_per_engine": {e: protocol[e]["n_changed"] for e in BOTH_ARM_ENGINES},
          "matcher_per_contrast": {**{f"original:{k}": v["n_changed"] for k, v in matcher["original"].items()},
                                   **{f"amended:{k}": v["n_changed"] for k, v in matcher["amended"].items()}}}

    p_prot = {e: protocol[e]["p_exact_mcnemar"] for e in BOTH_ARM_ENGINES}
    p_match_amended = {k: v["p_exact_mcnemar"] for k, v in matcher["amended"].items()}
    best_prot = min(p_prot.values())
    s2 = {"criterion": "S2",
          "statement": "exact McNemar p <= 0.05 on the orientation contrast for at least one "
                       "matcher, and the matcher contrast's p is larger on the same arm",
          "met": bool(best_prot <= 0.05 and min(p_match_amended.values()) > best_prot),
          "p_protocol": p_prot, "p_matcher_amended": p_match_amended,
          "best_protocol_p": best_prot,
          "best_matcher_p": float(min(p_match_amended.values()))}

    def per_window(ks):
        mp = float(np.mean([contrast(orig, amend, ks, e, e)["n_changed"] for e in BOTH_ARM_ENGINES]))
        mm = float(np.mean([contrast(amend, amend, ks, a, b)["n_changed"]
                            for a, b in combinations(ENGINES, 2)]))
        return {"protocol_mean_changed": mp, "matcher_mean_changed": mm,
                "protocol_exceeds_matcher": mp > mm, "n_pairs": len(ks)}

    w3, w4 = per_window(rd03), per_window(rd04)
    s3 = {"criterion": "S3", "statement": "the sign of S1's comparison holds in RD-03 and RD-04 separately",
          "met": bool(w3["protocol_exceeds_matcher"] and w4["protocol_exceeds_matcher"]),
          "RD03": w3, "RD04": w4}

    regress = {e: protocol[e]["success_to_fail"] for e in BOTH_ARM_ENGINES}
    s4 = {"criterion": "S4",
          "statement": "every outcome the orientation step flips goes fail -> success, "
                       "or the exceptions are enumerated",
          "met": all(v == 0 for v in regress.values()),
          "success_to_fail_per_engine": regress,
          "fail_to_success_per_engine": {e: protocol[e]["fail_to_success"] for e in BOTH_ARM_ENGINES},
          "exceptions": [f for e in BOTH_ARM_ENGINES for f in protocol[e]["flips"]
                         if f["direction"] == "success->fail"]}

    # -- S5: can a better matcher paper over the protocol defect? ----------
    best_wrong = set()
    for e in BOTH_ARM_ENGINES:
        best_wrong |= successes(orig, keys, e)
    right_by_engine = {e: successes(amend, keys, e) for e in ENGINES}
    worst_right = set(keys)
    for e in ENGINES:
        worst_right &= right_by_engine[e]
    rescued = set()
    for e in BOTH_ARM_ENGINES:
        rescued |= (successes(amend, keys, e) - successes(orig, keys, e))
    papered = best_wrong - worst_right
    s5 = {"criterion": "S5",
          "statement": "pairs the BEST matcher rescues under the WRONG orientation are fewer than "
                       "pairs the orientation step rescues outright",
          "met": len(papered) < len(rescued),
          "n_papered_over_by_matcher": len(papered),
          "n_rescued_by_protocol": len(rescued),
          "note": "'papered over' = succeeded under some matcher on the WRONG orientation but is not "
                  "a unanimous success on the RIGHT one; 'rescued' = failed under an engine on the "
                  "wrong orientation and succeeds under the same engine on the right one"}

    per_engine_rates = {}
    for arm_name, rows in (("original", orig), ("amended", amend)):
        for e in ENGINES:
            n = sum(1 for k in keys if e in rows.get(k, {}))
            if n:
                per_engine_rates[f"{arm_name}:{e}"] = {
                    "engine": ENGINE_LABEL[e], "n": n,
                    "n_success": len(successes(rows, keys, e)),
                    "rate": len(successes(rows, keys, e)) / n}

    doc = {
        "stage": "EXP-006", "part": 2,
        "preregistration": "docs/stages/EXP-006_protocol_vs_matcher.md",
        "what": "component ablation: does one protocol step move more real pair outcomes "
                "than replacing the entire matcher?",
        "reframed_by": "MASTER_RESEARCH_AND_ARCHITECTURE_PLAN.md §553 — the stand-alone "
                       "protocol-vs-matcher thesis is unfalsifiable as phrased",
        "sources": [f"experiments/REAL-DATA-07/{n}" for a in ARMS.values() for n in a.values()],
        "protocol_step": "orientation: quarter-turn (Part 1 method) vs north-up-east-right (E-037)",
        "n_paired_pairs": len(keys),
        "criteria": {c["criterion"]: c for c in (s0, s1, s2, s3, s4, s5)},
        "success_rates": per_engine_rates,
        "protocol_contrast": protocol,
        "matcher_contrast": matcher,
        "claims_not_supported": [
            "NOT the universal thesis. The orientation step is the one protocol component "
            "whose both levels happen to have been recorded, and they were recorded because a "
            "defect was found, not because an ablation was designed. This supports at most "
            "'one protocol step outweighs a matcher replacement on 42 mare pairs'.",
            "NOT a claim about protocol components never ablated here (scale normalisation, "
            "tiling, photometric).",
            "NOT an accuracy claim: the outcome is a binary success under a frozen rule, "
            "corroborated against archive geometry at its own ~100 px floor.",
            "NOT a Chandrayaan-2 result, and not evidence about non-mare terrain.",
        ],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
        "total_runtime_s": round(time.time() - t0, 2),
    }
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"paired pairs: {len(keys)}  (RD03 {len(rd03)}, RD04 {len(rd04)})\n")
    print("success rate by arm x engine:")
    for k, v in per_engine_rates.items():
        print(f"  {k:16s} {v['n_success']:3d}/{v['n']:3d}  {v['rate']:.3f}  {v['engine']}")
    print("\nPROTOCOL contrast (orientation, same engine):")
    for e in BOTH_ARM_ENGINES:
        c = protocol[e]
        print(f"  {ENGINE_LABEL[e]:22s} changed {c['n_changed']:3d}  "
              f"(+{c['fail_to_success']} / -{c['success_to_fail']})  p={c['p_exact_mcnemar']:.4f}")
    print("\nMATCHER contrast (engine swap, same orientation):")
    for arm_name, d in matcher.items():
        for k, c in d.items():
            print(f"  {arm_name:9s} {k:10s} changed {c['n_changed']:3d}  "
                  f"(+{c['fail_to_success']} / -{c['success_to_fail']})  p={c['p_exact_mcnemar']:.4f}")
    print()
    for c in (s0, s1, s2, s3, s4, s5):
        print(f"  {c['criterion']}: {'MET' if c['met'] else 'NOT MET'} -- {c['statement']}")
    print(f"\nwrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""
CLI to run Phase A static graph construction (Section 4) for one or all
jurisdictions. Deliberately kept out of the API/live pipeline — this is
an offline, occasionally-run curation step, not something a request
handler should ever trigger.

Usage:
    python -m scripts.build_static_graphs --jurisdiction india
    python -m scripts.build_static_graphs --all
"""
import argparse
import sys

from app.config import JURISDICTIONS, STATUTES_DIR
from app.graph.build_static_graph import (
    build_static_subgraph, load_statute_text, propose_requires_edges, save_jurisdiction_graph,
)

HUMAN_SIGNOFF_ENV_VAR = "STATUTE_MAPPINGS_HUMAN_REVIEWED"


def build_one(jurisdiction: str, skip_signoff_check: bool = False) -> None:
    import os

    jurisdiction_dir = STATUTES_DIR / jurisdiction
    if not jurisdiction_dir.exists() or not any(jurisdiction_dir.glob("*.json")):
        print(
            f"Skipping {jurisdiction}: no statute JSON files are present yet. "
            "Add extracted statute data before building that jurisdiction.",
            file=sys.stderr,
        )
        return

    signoff_ok = skip_signoff_check or os.environ.get(HUMAN_SIGNOFF_ENV_VAR) == "yes"
    if not signoff_ok:
        print(
            f"Refusing to build the {jurisdiction} graph: pass "
            "--skip-signoff-check only after a person with legal training "
            "has reviewed and approved every proposed REQUIRES/INVOKES edge "
            "(Section 7, item 1), or set "
            f"{HUMAN_SIGNOFF_ENV_VAR}=yes in the environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    sections = load_statute_text(jurisdiction)
    proposed_edges = propose_requires_edges(jurisdiction, sections)
    # NOTE: proposed_edges here should already be the human-approved
    # subset by the time this script is actually run for real. The signoff
    # check is a guardrail and the code-level bypass must only be used after
    # a real legal review has happened.
    graph = build_static_subgraph(jurisdiction)
    out_path = save_jurisdiction_graph(jurisdiction, graph)
    print(f"Saved {jurisdiction} graph -> {out_path}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--jurisdiction", choices=JURISDICTIONS)
    group.add_argument("--all", action="store_true")
    parser.add_argument(
        "--skip-signoff-check",
        action="store_true",
        help="Explicitly confirm the human legal review is completed in code before building.",
    )
    args = parser.parse_args()

    targets = JURISDICTIONS if args.all else [args.jurisdiction]
    for j in targets:
        build_one(j, skip_signoff_check=args.skip_signoff_check)


if __name__ == "__main__":
    main()

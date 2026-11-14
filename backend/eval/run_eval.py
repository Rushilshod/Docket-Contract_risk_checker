"""
Evaluation harness (Section 6/9): precision/recall against a held-out
labeled test set, PLUS an explicit test for the "laziness" failure mode —
a model that just says "no risk found" on everything can look deceptively
good on precision/recall alone if the test set is unbalanced.
"""
from dataclasses import dataclass


@dataclass
class EvalResult:
    precision: float
    recall: float
    f1: float
    laziness_score: float  # fraction of KNOWN-risky test contracts the
    # pipeline flagged as clean. Lower is better; this number should be
    # reported alongside precision/recall, never in place of it.


def load_test_set(path: str) -> list[dict]:
    """
    TODO(human/engineer): build this held-out set yourself — it needs
    real or realistic contracts per jurisdiction x domain with known
    ground-truth flags. This is closely related to the manual testing in
    Section 7, item 3, and should probably reuse some of those documents.
    """
    raise NotImplementedError


def run_evaluation(test_set: list[dict]) -> EvalResult:
    """
    TODO(engineer): run the full pipeline (app.pipeline.run_pipeline) on
    each test contract, compare flags against ground truth, and compute:
      - precision/recall/f1 on flag detection
      - laziness_score specifically on the subset of test contracts that
        DO contain a known risk (Section 6)
    Log results to MLflow or the spreadsheet named in Section 5.
    """
    raise NotImplementedError


if __name__ == "__main__":
    # TODO(engineer): argparse for --test-set-path, then print/log results.
    raise NotImplementedError

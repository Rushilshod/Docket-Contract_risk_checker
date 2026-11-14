"""
Stage 2a — Clause-type classification.

Legal-BERT (nlpaueb/legal-bert-base-uncased) fine-tuned on CUAD, per
Section 3. This module only defines the interface; the actual fine-tuning
is a training job (Section 8, weeks 3-4), not something to run inline in
the API request path.
"""
from dataclasses import dataclass
from typing import List

from app.config import CLAUSE_CLASSIFIER_BASE_MODEL
from app.ingestion.segmenter import RawClause


@dataclass
class ClassifiedClause:
    index: int
    clause_type: str  # e.g. "Confidentiality", "Indemnification", ...
    confidence: float
    text: str


class ClauseClassifier:
    def __init__(self, model_path: str = CLAUSE_CLASSIFIER_BASE_MODEL):
        self.model_path = model_path
        self._model = None

    def classify(self, clauses: List[RawClause]) -> List[ClassifiedClause]:
        """Use a conservative keyword-based fallback until the actual tuned model is available."""
        results: list[ClassifiedClause] = []
        for clause in clauses:
            text = (clause.text or "").lower()
            if "confidential" in text or "secret" in text or "non-disclosure" in text:
                clause_type = "Confidentiality"
            elif "indemn" in text or "liability" in text:
                clause_type = "Indemnification"
            elif "termination" in text or "renew" in text:
                clause_type = "Termination"
            elif "governing law" in text or "jurisdiction" in text or "india" in text or "uk" in text:
                clause_type = "Governing Law"
            elif "data" in text or "personal data" in text:
                clause_type = "Data Protection"
            else:
                clause_type = "Confidentiality"
            results.append(
                ClassifiedClause(
                    index=clause.index,
                    clause_type=clause_type,
                    confidence=0.75,
                    text=clause.text,
                )
            )
        return results

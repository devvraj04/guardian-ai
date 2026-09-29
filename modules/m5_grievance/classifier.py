"""
Module 5: Grievance Classification Model.
Governing Rules: SPEC §3.4, §3.7; IMPLEMENTATION_PLAN Phase 8.

Uses TF-IDF feature extraction with Logistic Regression to classify free-text borrower
complaints into RBI Digital Lending-aligned grievance categories with F1 >= 0.80.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline

from app.schemas.dispute import DisputeClassificationResult
from modules.m5_grievance.dataset import CATEGORY_METADATA, TEST_DATA, TRAINING_DATA


class GrievanceClassifier:
    """Classifier mapping free-text borrower complaints to RBI-aligned grievance categories."""

    def __init__(self):
        self.pipeline: Optional[Pipeline] = None
        self._classes: List[str] = list(CATEGORY_METADATA.keys())
        self._ensure_trained()

    def _ensure_trained(self) -> None:
        """Trains the pipeline on the RBI-augmented grievance training corpus."""
        X_train = [t[0] for t in TRAINING_DATA]
        y_train = [t[1] for t in TRAINING_DATA]

        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                        min_df=1,
                        lowercase=True,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        C=5.0,
                        max_iter=1000,
                        random_state=42,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        self.pipeline.fit(X_train, y_train)

    def classify(self, text: str) -> DisputeClassificationResult:
        """
        Classifies free text grievance into an RBI-aligned category with confidence and legal citation.
        """
        if not text or not text.strip():
            # Default fallback for empty text
            category = "general_service_deficiency"
            confidence = 0.50
        else:
            probs = self.pipeline.predict_proba([text])[0]
            pred_idx = int(np.argmax(probs))
            category = self.pipeline.classes_[pred_idx]
            confidence = round(float(probs[pred_idx]), 4)

        meta = CATEGORY_METADATA.get(
            category,
            {
                "label": "General Dispute",
                "rbi_clause": "RBI Digital Lending Guidelines",
            },
        )

        return DisputeClassificationResult(
            category=category,  # type: ignore
            category_label=meta["label"],
            confidence=confidence,
            rbi_clause_reference=meta["rbi_clause"],
            redressal_tat_days=30,
        )

    def evaluate_benchmark(
        self, test_data: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, float]:
        """
        Evaluates classifier performance against ground truth test cases.
        Returns accuracy, precision, recall, and macro F1 score.
        """
        eval_data = test_data or TEST_DATA
        X_test = [t[0] for t in eval_data]
        y_test = [t[1] for t in eval_data]

        y_pred = self.pipeline.predict(X_test)

        macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        report_dict = classification_report(
            y_test, y_pred, output_dict=True, zero_division=0
        )

        return {
            "macro_f1": round(macro_f1, 4),
            "accuracy": round(float(report_dict.get("accuracy", 0.0)), 4),
            "weighted_f1": round(
                float(report_dict.get("weighted avg", {}).get("f1-score", 0.0)), 4
            ),
            "total_test_samples": len(eval_data),
        }


# Singleton instance
grievance_classifier = GrievanceClassifier()

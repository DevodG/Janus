"""
Domain Classifier Trainer for Janus self-improvement system.

Trains a domain classifier using curated examples from the observation layer.
The classifier predicts which domain a query belongs to (finance, technology, etc.)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

# Domain list from query_classifier.py
DOMAINS = [
    "finance",
    "technology",
    "healthcare",
    "policy",
    "science",
    "geopolitics",
    "energy",
    "critical_thinking",
    "emotional_intelligence",
    "philosophy",
    "business",
    "education",
    "general",
]


class DomainClassifierTrainer:
    """
    Trains a domain classifier using curated examples.
    Uses Naive Bayes approach for simplicity and interpretability.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Default to backend/data/curation
            self.data_dir = (
                Path(__file__).parent.parent.parent.parent / "data" / "curation"
            )
        else:
            self.data_dir = data_dir

        self.curated_file = self.data_dir / "curated_examples.jsonl"

        # Model parameters
        self.domain_word_counts = defaultdict(lambda: defaultdict(int))
        self.domain_total_words = defaultdict(int)
        self.domain_doc_counts = defaultdict(int)
        self.vocab = set()
        self.total_docs = 0

        # Load existing model if available
        self._load_model()

    def _load_model(self):
        """Load pre-trained model parameters if they exist."""
        model_file = self.data_dir / "domain_classifier_model.json"
        if model_file.exists():
            try:
                with open(model_file) as f:
                    model_data = json.load(f)
                    self.domain_word_counts = defaultdict(
                        lambda: defaultdict(int),
                        model_data.get("domain_word_counts", {}),
                    )
                    self.domain_total_words = defaultdict(
                        int, model_data.get("domain_total_words", {})
                    )
                    self.domain_doc_counts = defaultdict(
                        int, model_data.get("domain_doc_counts", {})
                    )
                    self.vocab = set(model_data.get("vocab", []))
                    self.total_docs = model_data.get("total_docs", 0)
                logger.info(f"Loaded domain classifier model from {model_file}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

    def _save_model(self):
        """Save model parameters to disk."""
        model_file = self.data_dir / "domain_classifier_model.json"
        try:
            model_data = {
                "domain_word_counts": dict(self.domain_word_counts),
                "domain_total_words": dict(self.domain_total_words),
                "domain_doc_counts": dict(self.domain_doc_counts),
                "vocab": list(self.vocab),
                "total_docs": self.total_docs,
            }
            with open(model_file, "w") as f:
                json.dump(model_data, f, indent=2)
            logger.info(f"Saved domain classifier model to {model_file}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - lowercase and split on non-alphanumeric."""
        import re

        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def train_from_curated_examples(self) -> Dict[str, any]:
        """
        Train the domain classifier using curated examples.
        Returns training statistics.
        """
        if not self.curated_file.exists():
            logger.warning(f"No curated examples found at {self.curated_file}")
            return {"error": "No training data available"}

        # Reset counters
        self.domain_word_counts = defaultdict(lambda: defaultdict(int))
        self.domain_total_words = defaultdict(int)
        self.domain_doc_counts = defaultdict(int)
        self.vocab = set()
        self.total_docs = 0

        # Process each curated example
        try:
            with open(self.curated_file) as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            example = json.loads(line)
                            query = example.get("query", "")
                            domain = example.get("domain", "general")

                            # Skip if domain not in our list
                            if domain not in DOMAINS:
                                domain = "general"

                            # Tokenize the query
                            tokens = self._tokenize(query)

                            # Update counts
                            self.domain_doc_counts[domain] += 1
                            self.total_docs += 1

                            for token in tokens:
                                self.domain_word_counts[domain][token] += 1
                                self.domain_total_words[domain] += 1
                                self.vocab.add(token)

                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON on line {line_num}: {e}")
                            continue

            # Calculate and save model
            self._save_model()

            stats = {
                "total_documents": self.total_docs,
                "vocabulary_size": len(self.vocab),
                "domain_distribution": dict(self.domain_doc_counts),
                "training_complete": True,
            }

            logger.info(f"Domain classifier training complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"error": str(e)}

    def predict_domain(self, query: str) -> Tuple[str, float]:
        """
        Predict the domain for a given query.
        Returns (domain, confidence) tuple.
        """
        if self.total_docs == 0:
            return "general", 0.0

        tokens = self._tokenize(query)
        if not tokens:
            return "general", 0.0

            # Calculate log probabilities for each domain
        log_probs = {}
        vocab_size = len(self.vocab)

        for domain in DOMAINS:
            # Prior probability P(domain) - handle unseen domains
            if self.domain_doc_counts[domain] == 0:
                # If domain not seen in training, use a small probability
                prior = math.log(1e-10)
            else:
                prior = math.log(self.domain_doc_counts[domain] / self.total_docs)

            # Likelihood P(query|domain) = product of P(word|domain) for each word
            likelihood = 0.0
            for token in tokens:
                # Laplace smoothing: P(word|domain) = (count(word in domain) + 1) / (total_words_in_domain + vocab_size)
                word_count = self.domain_word_counts[domain].get(token, 0)
                total_words_in_domain = self.domain_total_words[domain]
                prob = (word_count + 1) / (total_words_in_domain + vocab_size)
                likelihood += math.log(prob)

            log_probs[domain] = prior + likelihood

        # Convert log probabilities to probabilities
        max_log_prob = max(log_probs.values())
        probs = {
            domain: math.exp(log_prob - max_log_prob)
            for domain, log_prob in log_probs.items()
        }

        # Normalize to get probabilities
        prob_sum = sum(probs.values())
        if prob_sum > 0:
            probs = {domain: prob / prob_sum for domain, prob in probs.items()}
        else:
            # Uniform distribution if something went wrong
            probs = {domain: 1.0 / len(DOMAINS) for domain in DOMAINS}

        # Get the domain with highest probability
        predicted_domain = max(probs, key=probs.get)
        confidence = probs[predicted_domain]

        return predicted_domain, confidence

    def evaluate(self) -> Dict[str, any]:
        """
        Evaluate the classifier on the curated examples.
        Returns accuracy and other metrics.
        """
        if not self.curated_file.exists() or self.total_docs == 0:
            return {"error": "No training data or model not trained"}

        correct = 0
        total = 0
        domain_stats = defaultdict(lambda: {"correct": 0, "total": 0})

        try:
            with open(self.curated_file) as f:
                for line in f:
                    if line.strip():
                        example = json.loads(line)
                        query = example.get("query", "")
                        actual_domain = example.get("domain", "general")

                        if actual_domain not in DOMAINS:
                            actual_domain = "general"

                        predicted_domain, confidence = self.predict_domain(query)

                        if predicted_domain == actual_domain:
                            correct += 1
                            domain_stats[actual_domain]["correct"] += 1

                        domain_stats[actual_domain]["total"] += 1
                        total += 1

            accuracy = correct / total if total > 0 else 0.0

            # Calculate per-domain accuracy
            domain_accuracies = {}
            for domain, stats in domain_stats.items():
                if stats["total"] > 0:
                    domain_accuracies[domain] = stats["correct"] / stats["total"]
                else:
                    domain_accuracies[domain] = 0.0

            return {
                "accuracy": accuracy,
                "correct_predictions": correct,
                "total_predictions": total,
                "domain_accuracies": domain_accuracies,
                "domain_distribution": dict(self.domain_doc_counts),
            }

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}


# Global instance
domain_classifier_trainer = DomainClassifierTrainer()


def train_domain_classifier() -> Dict[str, any]:
    """Convenience function to train the domain classifier."""
    return domain_classifier_trainer.train_from_curated_examples()


def predict_domain(query: str) -> Tuple[str, float]:
    """Convenience function to predict domain for a query."""
    return domain_classifier_trainer.predict_domain(query)


def evaluate_domain_classifier() -> Dict[str, any]:
    """Convenience function to evaluate the domain classifier."""
    return domain_classifier_trainer.evaluate()

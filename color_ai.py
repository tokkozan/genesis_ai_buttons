"""Tiny supervised RGB classifier. No cloud API and no downloaded weights."""
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix

LABELS = ["blue", "green", "red"]
BASE_RGB = np.array([[0.08, 0.22, 0.95], [0.08, 0.70, 0.20], [0.90, 0.10, 0.08]])


def features(rgb):
    """Normalize brightness; same feature extraction during training/inference."""
    rgb = np.asarray(rgb, dtype=float)
    return rgb / np.maximum(rgb.sum(axis=-1, keepdims=True), 1e-6)


def samples(seed, per_class):
    rng = np.random.default_rng(seed)
    x, y = [], []
    for name, base in zip(LABELS, BASE_RGB):
        rgb = base * rng.uniform(0.35, 1.0, (per_class, 1))
        rgb += rng.normal(0, 0.025, (per_class, 3))
        x.extend(features(np.clip(rgb, 0.005, 1)))
        y.extend([name] * per_class)
    return np.array(x), np.array(y)


def train(model_path, metrics_path):
    x, y = samples(41, 1200)
    test_x, test_y = samples(103, 300)
    model = LogisticRegression(C=12, max_iter=500, random_state=41).fit(x, y)
    pred = model.predict(test_x)
    result = {
        "algorithm": "multiclass logistic regression",
        "training_samples": len(y), "heldout_samples": len(test_y),
        "synthetic_heldout_accuracy": float(np.mean(pred == test_y)),
        "classes": model.classes_.tolist(),
        "confusion_matrix": confusion_matrix(test_y, pred, labels=model.classes_).tolist(),
        "scope": "Synthetic RGB samples only; not real-world camera accuracy.",
    }
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps({"classes": model.classes_.tolist(),
                                    "coef": model.coef_.tolist(),
                                    "intercept": model.intercept_.tolist()}, indent=2), encoding="utf-8")
    Path(metrics_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


class ColorAI:
    def __init__(self, path):
        model = json.loads(Path(path).read_text(encoding="utf-8"))
        self.classes = model["classes"]
        self.coef = np.array(model["coef"])
        self.intercept = np.array(model["intercept"])

    def predict(self, patch):
        # The patch is actual rendered camera pixels, not a simulator color label.
        rgb = np.asarray(patch)[..., :3].mean(axis=(0, 1)) / 255.0
        scores = self.coef @ features(rgb) + self.intercept
        prob = np.exp(scores - scores.max())
        prob /= prob.sum()
        index = int(np.argmax(prob))
        return self.classes[index], float(prob[index]), rgb.tolist()

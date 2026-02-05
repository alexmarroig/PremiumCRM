from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Dict, Iterable, List, Sequence


@dataclass
class LogInsight:
    """Structured finding created from error logs."""

    signature: str
    count: int
    probable_cause: str
    recommended_fix: str


class FailurePredictor:
    """Simple predictor that estimates incident risk from recent metric history.

    The model intentionally uses a lightweight EWMA-based approach so it can run
    in CI/CD pipelines without external ML dependencies.
    """

    def __init__(self, latency_threshold_ms: float = 500.0, error_rate_threshold: float = 0.05):
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold

    def predict_risk(self, latency_series: Sequence[float], error_rate_series: Sequence[float]) -> float:
        if not latency_series or not error_rate_series:
            return 0.0

        latency_signal = self._ewma(latency_series)
        error_signal = self._ewma(error_rate_series)

        latency_risk = min(1.0, latency_signal / self.latency_threshold_ms)
        error_risk = min(1.0, error_signal / self.error_rate_threshold)

        # Weighted blend keeps the score interpretable while emphasizing errors.
        return round((latency_risk * 0.4) + (error_risk * 0.6), 4)

    @staticmethod
    def _ewma(values: Sequence[float], alpha: float = 0.35) -> float:
        score = values[0]
        for value in values[1:]:
            score = (alpha * value) + ((1 - alpha) * score)
        return score


class RealtimePerformanceMonitor:
    """Monitors service snapshots and emits alerts for bottlenecks."""

    def __init__(self, latency_threshold_ms: float = 500.0, cpu_threshold: float = 0.9):
        self.latency_threshold_ms = latency_threshold_ms
        self.cpu_threshold = cpu_threshold

    def evaluate_snapshot(self, snapshot: Dict[str, float]) -> List[str]:
        alerts: List[str] = []
        latency = snapshot.get("latency_ms", 0.0)
        cpu = snapshot.get("cpu_usage", 0.0)
        memory = snapshot.get("memory_usage", 0.0)

        if latency >= self.latency_threshold_ms:
            alerts.append("High latency detected: verify database indexes and queue backlog")
        if cpu >= self.cpu_threshold:
            alerts.append("CPU saturation risk: review hot paths and autoscaling policy")
        if memory >= 0.9:
            alerts.append("Memory pressure risk: inspect object retention and cache limits")

        return alerts


class AnomalyDetector:
    """Detects anomalies using z-score to keep inference deterministic and fast."""

    def detect(self, values: Sequence[float], z_threshold: float = 2.5) -> List[int]:
        if len(values) < 3:
            return []

        avg = mean(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        std_dev = sqrt(variance)
        if std_dev == 0:
            return []

        outliers = []
        for idx, value in enumerate(values):
            z_score = abs((value - avg) / std_dev)
            if z_score >= z_threshold:
                outliers.append(idx)
        return outliers


class RegressionPlanner:
    """Prioritizes regression suites based on changed modules and risk weights."""

    DEFAULT_MAP: Dict[str, List[str]] = {
        "api": ["tests/test_auth.py", "tests/test_webhook_normalizers.py"],
        "automation": ["tests/test_automation_callbacks.py", "tests/test_automation_delivery.py"],
        "rules": ["tests/test_rules_engine.py"],
        "ai": ["tests/test_ai_provider.py"],
    }

    def plan(self, changed_paths: Iterable[str], custom_map: Dict[str, List[str]] | None = None) -> List[str]:
        mapping = custom_map or self.DEFAULT_MAP
        selected: List[str] = []

        for path in changed_paths:
            for key, tests in mapping.items():
                if key in path:
                    selected.extend(tests)

        # Stable and unique ordering for deterministic CI runs.
        return sorted(set(selected))


class UserBehaviorSimulator:
    """Builds synthetic user journeys to validate UX and interface test flows."""

    def simulate(self, transitions: Dict[str, Dict[str, float]], start: str, steps: int = 5) -> List[str]:
        journey = [start]
        current = start

        for _ in range(steps):
            options = transitions.get(current, {})
            if not options:
                break
            current = self._pick_most_likely(options)
            journey.append(current)

        return journey

    @staticmethod
    def _pick_most_likely(options: Dict[str, float]) -> str:
        # Deterministic pick avoids flaky unit tests.
        return max(options.items(), key=lambda item: item[1])[0]


def analyze_error_logs(log_lines: Sequence[str]) -> List[LogInsight]:
    """Extracts recurring signatures and attaches likely causes/fixes."""

    signature_count: Dict[str, int] = {}
    for line in log_lines:
        signature = _extract_signature(line)
        signature_count[signature] = signature_count.get(signature, 0) + 1

    insights: List[LogInsight] = []
    for signature, count in sorted(signature_count.items(), key=lambda item: item[1], reverse=True):
        cause, fix = _suggest_fix(signature)
        insights.append(LogInsight(signature=signature, count=count, probable_cause=cause, recommended_fix=fix))

    return insights


def _extract_signature(line: str) -> str:
    lowered = line.lower()
    if "timeout" in lowered:
        return "timeout"
    if "connection refused" in lowered:
        return "connection_refused"
    if "keyerror" in lowered:
        return "key_error"
    return "generic_error"


def _suggest_fix(signature: str) -> tuple[str, str]:
    if signature == "timeout":
        return "Service dependency is responding too slowly", "Tune timeout/retry policy and optimize slow query paths"
    if signature == "connection_refused":
        return "Downstream service unavailable", "Add health checks and validate deployment/network policies"
    if signature == "key_error":
        return "Unexpected payload shape", "Add schema validation and default guards before dictionary access"
    return "Unknown exception pattern", "Capture stack traces with richer context and correlate by request id"

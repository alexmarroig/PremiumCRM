from services.quality.intelligence import (
    AnomalyDetector,
    FailurePredictor,
    RegressionPlanner,
    RealtimePerformanceMonitor,
    UserBehaviorSimulator,
    analyze_error_logs,
)


def test_failure_predictor_risk_increases_with_errors():
    predictor = FailurePredictor(latency_threshold_ms=400, error_rate_threshold=0.05)

    low_risk = predictor.predict_risk([200, 210, 220], [0.01, 0.01, 0.02])
    high_risk = predictor.predict_risk([350, 390, 420], [0.03, 0.05, 0.08])

    assert high_risk > low_risk
    assert 0 <= high_risk <= 1


def test_realtime_monitor_emits_expected_alerts():
    monitor = RealtimePerformanceMonitor(latency_threshold_ms=300, cpu_threshold=0.8)
    alerts = monitor.evaluate_snapshot({"latency_ms": 450, "cpu_usage": 0.85, "memory_usage": 0.95})

    assert len(alerts) == 3


def test_anomaly_detector_flags_extreme_point():
    detector = AnomalyDetector()
    outliers = detector.detect([10, 11, 9, 10, 50], z_threshold=1.9)

    assert outliers == [4]


def test_regression_planner_selects_impacted_suites():
    planner = RegressionPlanner()
    tests = planner.plan(["src/api/routers/auth.py", "src/services/automation/scheduler.py"])

    assert "tests/test_auth.py" in tests
    assert "tests/test_automation_delivery.py" in tests


def test_user_behavior_simulation_prefers_most_likely_path():
    simulator = UserBehaviorSimulator()
    transitions = {
        "home": {"search": 0.7, "pricing": 0.3},
        "search": {"contact": 0.8, "home": 0.2},
    }

    assert simulator.simulate(transitions, start="home", steps=2) == ["home", "search", "contact"]


def test_error_log_analysis_groups_root_causes():
    logs = [
        "ERROR Timeout on request /api/messages",
        "ERROR Timeout on request /api/messages",
        "ERROR Connection refused db.internal",
    ]

    insights = analyze_error_logs(logs)

    assert insights[0].signature == "timeout"
    assert insights[0].count == 2
    assert insights[1].signature == "connection_refused"

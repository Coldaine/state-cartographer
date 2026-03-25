from state_cartographer.transport.config import load_config
from state_cartographer.transport.health import doctor
from state_cartographer.transport.models import (
    ControlLayerStatus,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    TransportLayerStatus,
)


def test_live_health_doctor():
    cfg = load_config()
    report = doctor(cfg)

    # We may not know if MEmu is currently running in this remote workspace,
    # but we can validate that the report is structured correctly.
    assert hasattr(report, "readiness_tier")
    assert hasattr(report, "transport_layer")
    assert hasattr(report, "control_layer")
    assert hasattr(report, "observation_layer")
    assert isinstance(report.degradation_codes, list)

    if report.adb_reachable and report.device_online:
        assert report.readiness_tier in {ReadinessTier.DEGRADED, ReadinessTier.OPERABLE}
        assert report.transport_layer == TransportLayerStatus.READY
        assert report.control_layer in {ControlLayerStatus.FALLBACK, ControlLayerStatus.PREFERRED}
        assert report.observation_layer == ObservationLayerStatus.UNVERIFIED
        assert report.verdict == ProbeVerdict.PASS
    else:
        assert report.readiness_tier == ReadinessTier.UNREACHABLE
        assert report.transport_layer == TransportLayerStatus.UNREACHABLE
        assert report.control_layer == ControlLayerStatus.UNAVAILABLE
        assert report.observation_layer == ObservationLayerStatus.UNAVAILABLE
        assert report.verdict == ProbeVerdict.FAIL

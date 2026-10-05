"""Uso de recursos simulado para las gráficas del dashboard, hasta tener una fuente real de métricas."""
import math
import random
from datetime import datetime, timezone

from app.models import MetricPoint, VMStatus

# Rangos soportados: (duración en segundos, paso en segundos)
METRIC_RANGES: dict[str, tuple[int, int]] = {
    "1h": (3600, 60),
    "6h": (6 * 3600, 300),
    "24h": (24 * 3600, 900),
    "7d": (7 * 86400, 3600),
}


def _wave(seed: str, base: float, phase: float, ts: float, amplitude: float, period: float) -> float:
    noise = random.Random(f"{seed}-{int(ts // 60)}").uniform(-4, 4)
    value = base + amplitude * math.sin(2 * math.pi * ts / 86400 + phase) + amplitude / 3 * math.sin(2 * math.pi * ts / period + phase) + noise
    return round(min(max(value, 0.0), 100.0), 1)


def simulate_series(vm_id: int, status: VMStatus, range_: str, now: float) -> tuple[int, list[MetricPoint]]:
    duration, step = METRIC_RANGES[range_]
    rng = random.Random(vm_id)
    cpu_base, ram_base, disk_fill, phase = rng.uniform(10, 55), rng.uniform(35, 70), rng.uniform(20, 80), rng.uniform(0, 2 * math.pi)
    running = status == VMStatus.running
    end = now // step * step
    points = []
    for offset in range(duration, -1, -step):
        ts = end - offset
        points.append(
            MetricPoint(
                timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                cpu_percent=_wave(f"{vm_id}-cpu", cpu_base, phase, ts, 20, 900) if running else 0.0,
                ram_percent=_wave(f"{vm_id}-ram", ram_base, phase, ts, 10, 1800) if running else 0.0,
                disk_percent=round(disk_fill, 1),
            )
        )
    return step, points

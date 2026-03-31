"""Metrics collection - track performance and usage statistics."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricPoint:
    """A single data point for a metric."""

    value: float
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


class Counter:
    """A monotonically increasing counter."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._labeled: dict[str, float] = defaultdict(float)

    def inc(self, amount: float = 1.0, **labels: str):
        if labels:
            key = str(sorted(labels.items()))
            self._labeled[key] += amount
        else:
            self._value += amount

    @property
    def value(self) -> float:
        return self._value

    def get(self, **labels: str) -> float:
        key = str(sorted(labels.items()))
        return self._labeled.get(key, 0.0)


class Gauge:
    """A value that can go up and down."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0

    def set(self, value: float):
        self._value = value

    def inc(self, amount: float = 1.0):
        self._value += amount

    def dec(self, amount: float = 1.0):
        self._value -= amount

    @property
    def value(self) -> float:
        return self._value


class Histogram:
    """Track distribution of values with bucketed counting."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, description: str = "", buckets: tuple[float, ...] | None = None):
        self.name = name
        self.description = description
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._values: list[float] = []
        self._bucket_counts: dict[float, int] = {b: 0 for b in self.buckets}
        self._sum = 0.0
        self._count = 0

    def observe(self, value: float):
        self._values.append(value)
        self._sum += value
        self._count += 1
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1

    @property
    def count(self) -> int:
        return self._count

    @property
    def sum(self) -> float:
        return self._sum

    @property
    def avg(self) -> float:
        return self._sum / self._count if self._count > 0 else 0.0

    def percentile(self, p: float) -> float:
        """Calculate a percentile (0-100) from observed values."""
        if not self._values:
            return 0.0
        sorted_vals = sorted(self._values)
        idx = int(len(sorted_vals) * p / 100)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]


class Timer:
    """Context manager for timing operations."""

    def __init__(self, histogram: Histogram | None = None):
        self.histogram = histogram
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        if self.histogram:
            self.histogram.observe(self.elapsed)


class MetricsCollector:
    """Central metrics collection point."""

    def __init__(self):
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def counter(self, name: str, description: str = "") -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(name, description)
        return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description)
        return self._gauges[name]

    def histogram(self, name: str, description: str = "", buckets: tuple[float, ...] | None = None) -> Histogram:
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, buckets)
        return self._histograms[name]

    def timer(self, name: str) -> Timer:
        """Create a timer that records to a histogram."""
        hist = self.histogram(name)
        return Timer(hist)

    def get_all(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        result: dict[str, Any] = {}
        for name, counter in self._counters.items():
            result[f"counter.{name}"] = counter.value
        for name, gauge in self._gauges.items():
            result[f"gauge.{name}"] = gauge.value
        for name, hist in self._histograms.items():
            result[f"histogram.{name}"] = {
                "count": hist.count,
                "sum": hist.sum,
                "avg": hist.avg,
                "p50": hist.percentile(50),
                "p95": hist.percentile(95),
                "p99": hist.percentile(99),
            }
        return result

    def reset(self):
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# Global metrics instance
metrics = MetricsCollector()

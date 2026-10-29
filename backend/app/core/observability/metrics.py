class MetricsRegistry:
    def __init__(self):
        self.counters = {}
        self.gauges = {}

    def inc(self, metric: str, amount: int = 1):
        self.counters[metric] = self.counters.get(metric, 0) + amount

    def set_gauge(self, metric: str, value: float):
        self.gauges[metric] = value

metrics = MetricsRegistry()

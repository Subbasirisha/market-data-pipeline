from market_pipeline.http import Throttle


class FakeClock:
    """Stands in for time: sleeping just moves the clock forward, instantly."""

    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_first_call_does_not_wait():
    fake = FakeClock()
    Throttle(1.5, clock=fake.clock, sleep=fake.sleep).wait()
    assert fake.sleeps == []


def test_back_to_back_calls_wait_for_the_remaining_gap():
    fake = FakeClock()
    throttle = Throttle(1.5, clock=fake.clock, sleep=fake.sleep)

    throttle.wait()
    fake.now += 0.5  # the API call itself took 0.5s
    throttle.wait()

    assert fake.sleeps == [1.0]


def test_no_wait_when_enough_time_has_passed():
    fake = FakeClock()
    throttle = Throttle(1.5, clock=fake.clock, sleep=fake.sleep)

    throttle.wait()
    fake.now += 5
    throttle.wait()

    assert fake.sleeps == []

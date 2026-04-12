"""Tests for TimestampGenerator."""


def test_basic_increment(mock_module):
    gen = mock_module.TimestampGenerator(increment_ps=1000, jitter_ps=0)
    first = gen.next()
    second = gen.next()
    assert first == 1000
    assert second == 2000


def test_fine_counter_rollover(mock_module):
    gen = mock_module.TimestampGenerator(
        coarse=0, fine=99_000, increment_ps=2000, jitter_ps=0, max_fine=100_000
    )
    result = gen.next()
    # fine overflows: 99_000 + 2_000 = 101_000 → fine = 1_000, coarse = 1
    assert gen.coarse == 1
    assert gen.fine == 1000
    assert result == 1 * 100_000 + 1000


def test_coarse_counter_rollover(mock_module):
    gen = mock_module.TimestampGenerator(
        coarse=16_777_215,
        fine=99_000,
        increment_ps=2000,
        jitter_ps=0,
        max_fine=100_000,
        max_coarse=16_777_215,
    )
    gen.next()
    assert gen.coarse == 0


def test_jitter_stays_within_bounds(mock_module):
    gen = mock_module.TimestampGenerator(increment_ps=100, jitter_ps=50)
    results = [gen.next() for _ in range(1000)]
    # All results should be positive (increment is at least 1)
    assert all(r > 0 for r in results)
    # Results should be monotonically increasing (since min increment is 1)
    for i in range(1, len(results)):
        assert results[i] > results[i - 1]


def test_jitter_zero_is_deterministic(mock_module):
    gen1 = mock_module.TimestampGenerator(increment_ps=500, jitter_ps=0)
    gen2 = mock_module.TimestampGenerator(increment_ps=500, jitter_ps=0)
    for _ in range(100):
        assert gen1.next() == gen2.next()


def test_custom_max_fine(mock_module):
    gen = mock_module.TimestampGenerator(
        increment_ps=10, jitter_ps=0, max_fine=20
    )
    gen.next()  # fine=10
    assert gen.fine == 10
    assert gen.coarse == 0
    gen.next()  # fine=20 → rollover → fine=0, coarse=1
    assert gen.fine == 0
    assert gen.coarse == 1


def test_large_increment_multiple_rollovers(mock_module):
    gen = mock_module.TimestampGenerator(
        increment_ps=250, jitter_ps=0, max_fine=100
    )
    gen.next()  # fine=250 → 2 rollovers → fine=50, coarse=2
    assert gen.fine == 50
    assert gen.coarse == 2


def test_exponential_distribution_mean(mock_module):
    import random as _random

    _random.seed(42)
    gen = mock_module.TimestampGenerator(
        increment_ps=10_000,
        distribution="exponential",
        max_fine=10**15,
    )
    values = [gen.next() for _ in range(20_000)]
    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    mean = sum(diffs) / len(diffs)
    # Exponential sample mean converges to the configured mean; allow 5% slack.
    assert 9_500 < mean < 10_500
    # Tail is heavier than the [2715, 8145] range a uniform distribution would
    # produce: at least one sample must exceed 3x the mean.
    assert max(diffs) > 30_000


def test_exponential_strictly_monotonic(mock_module):
    import random as _random

    _random.seed(0)
    gen = mock_module.TimestampGenerator(
        increment_ps=100,
        distribution="exponential",
    )
    prev = 0
    for _ in range(5000):
        current = gen.next()
        assert current > prev
        prev = current


def test_unknown_distribution_raises(mock_module):
    gen = mock_module.TimestampGenerator(distribution="gaussian")
    with __import__("pytest").raises(ValueError):
        gen.next()

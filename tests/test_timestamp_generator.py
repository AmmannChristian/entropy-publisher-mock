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

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.channels.models import AdChannel
from apps.journeys.models import ConversionPath, TouchPoint
from apps.attribution.engine import first_touch, last_touch, linear


def _d(value):
    return Decimal(str(value))


def _almost_equal(a, b, eps=Decimal('0.0001')):
    return abs(Decimal(str(a)) - Decimal(str(b))) <= eps


def _make_path(user_id, converted, conversion_value, channels, now=None):
    """Helper: create a ConversionPath + ordered TouchPoints for a list of channel pks.
    Returns the ConversionPath instance.
    """
    if now is None:
        now = timezone.now()
    path = ConversionPath.objects.create(
        user_id=user_id,
        converted=converted,
        conversion_value=conversion_value,
    )
    for i, ch_pk in enumerate(channels, start=1):
        TouchPoint.objects.create(
            path=path,
            channel_id=ch_pk,
            timestamp=now,
            position=i,
        )
    return path


class AttributionEngineTestCase(TestCase):
    """Unit tests for first_touch / last_touch / linear attribution models.

    All tests use an isolated test database (Django TestCase auto-rollback
    after each test), no external services required.
    """

    @classmethod
    def setUpTestData(cls):
        cls.ch1 = AdChannel.objects.create(name='Channel 1', platform='google',
                                           cost_per_click=1.0, active=True)
        cls.ch2 = AdChannel.objects.create(name='Channel 2', platform='facebook',
                                           cost_per_click=1.0, active=True)
        cls.ch3 = AdChannel.objects.create(name='Channel 3', platform='email',
                                           cost_per_click=0.1, active=True)
        cls.ch4 = AdChannel.objects.create(name='Channel 4', platform='tiktok',
                                           cost_per_click=0.5, active=True)

    # ------------------------------------------------------------------
    # FIRST TOUCH
    # ------------------------------------------------------------------

    def test_first_touch_single_touchpoint(self):
        path = _make_path('u1', True, '100.00', [self.ch1.pk])
        result = first_touch([path])
        self.assertEqual(len(result), 1)
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '100.00'),
                        f"Expected 100.00 for ch1, got {result.get(self.ch1.pk)}")

    def test_first_touch_multi_touchpoint(self):
        path = _make_path('u2', True, '250.50', [self.ch1.pk, self.ch2.pk, self.ch3.pk])
        result = first_touch([path])
        self.assertEqual(len(result), 1,
                         "first_touch must assign full value to exactly one channel")
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '250.50'),
                        f"Expected 250.50 for first channel, got {result.get(self.ch1.pk)}")
        self.assertNotIn(self.ch2.pk, result)
        self.assertNotIn(self.ch3.pk, result)

    def test_first_touch_multiple_paths_accumulate(self):
        p1 = _make_path('u3', True, '100.00', [self.ch1.pk, self.ch2.pk])
        p2 = _make_path('u4', True, '75.50',  [self.ch1.pk, self.ch3.pk])
        p3 = _make_path('u5', True, '25.00',  [self.ch4.pk, self.ch1.pk])
        result = first_touch([p1, p2, p3])
        # ch1 is first in p1 + p2 => 175.50; ch4 is first in p3 => 25.00
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '175.50'),
                        f"ch1 expected 175.50, got {result.get(self.ch1.pk)}")
        self.assertTrue(_almost_equal(result.get(self.ch4.pk, 0), '25.00'),
                        f"ch4 expected 25.00, got {result.get(self.ch4.pk)}")
        self.assertNotIn(self.ch2.pk, result)
        self.assertNotIn(self.ch3.pk, result)

    def test_first_touch_unconverted_ignored(self):
        p_conv    = _make_path('u6', True,  '500.00', [self.ch1.pk, self.ch2.pk])
        p_no_conv = _make_path('u7', False, '500.00', [self.ch3.pk, self.ch4.pk])
        result = first_touch([p_conv, p_no_conv])
        # only p_conv counts
        self.assertEqual(len(result), 1)
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '500.00'))
        self.assertNotIn(self.ch3.pk, result)

    def test_first_touch_zero_conversion_value(self):
        p_zero = _make_path('u8', True,  '0.00',     [self.ch1.pk, self.ch2.pk])
        p_real = _make_path('u9', True,  '123.45',   [self.ch3.pk])
        result = first_touch([p_zero, p_real])
        # 0-value path produces no credits for any channel
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '0'),
                        "Zero-value path should not give ch1 any credit")
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '0'),
                        "Zero-value path should not give ch2 any credit")
        self.assertTrue(_almost_equal(result.get(self.ch3.pk, 0), '123.45'),
                        f"ch3 expected 123.45, got {result.get(self.ch3.pk)}")

    def test_first_touch_no_touchpoints(self):
        path = ConversionPath.objects.create(user_id='u_empty', converted=True,
                                             conversion_value='999.00')
        result = first_touch([path])
        self.assertEqual(result, {}, "Path with no touchpoints must produce no credits")

    # ------------------------------------------------------------------
    # LAST TOUCH
    # ------------------------------------------------------------------

    def test_last_touch_single_touchpoint(self):
        path = _make_path('u10', True, '300.00', [self.ch2.pk])
        result = last_touch([path])
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '300.00'),
                        f"Expected 300.00 for ch2, got {result.get(self.ch2.pk)}")

    def test_last_touch_multi_touchpoint(self):
        path = _make_path('u11', True, '88.88',
                          [self.ch1.pk, self.ch2.pk, self.ch3.pk, self.ch4.pk])
        result = last_touch([path])
        self.assertEqual(len(result), 1,
                         "last_touch must assign full value to exactly one channel")
        self.assertTrue(_almost_equal(result.get(self.ch4.pk, 0), '88.88'),
                        f"Expected 88.88 for last channel (ch4), got {result.get(self.ch4.pk)}")
        self.assertNotIn(self.ch1.pk, result)
        self.assertNotIn(self.ch3.pk, result)

    def test_last_touch_multiple_paths_accumulate(self):
        p1 = _make_path('u12', True, '40.00', [self.ch1.pk, self.ch2.pk])  # last=ch2
        p2 = _make_path('u13', True, '60.00', [self.ch1.pk, self.ch2.pk, self.ch3.pk])  # last=ch3
        p3 = _make_path('u14', True, '20.00', [self.ch2.pk])  # last=ch2
        result = last_touch([p1, p2, p3])
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '60.00'),
                        f"ch2 expected 60.00, got {result.get(self.ch2.pk)}")
        self.assertTrue(_almost_equal(result.get(self.ch3.pk, 0), '60.00'),
                        f"ch3 expected 60.00, got {result.get(self.ch3.pk)}")
        self.assertNotIn(self.ch1.pk, result)

    def test_last_touch_unconverted_ignored(self):
        p_conv    = _make_path('u15', True,  '500.00', [self.ch1.pk, self.ch2.pk])
        p_no_conv = _make_path('u16', False, '500.00', [self.ch3.pk, self.ch4.pk])
        result = last_touch([p_conv, p_no_conv])
        self.assertEqual(len(result), 1)
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '500.00'))
        self.assertNotIn(self.ch4.pk, result,
                         "Unconverted path should not contribute credits to last channel")

    def test_last_touch_zero_conversion_value(self):
        p_zero = _make_path('u17', True, '0.00',    [self.ch1.pk, self.ch2.pk])
        p_real = _make_path('u18', True, '77.77',   [self.ch3.pk, self.ch4.pk])
        result = last_touch([p_zero, p_real])
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '0'))
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '0'),
                        "Zero-value path should not give ch2 (last) any credit")
        self.assertTrue(_almost_equal(result.get(self.ch4.pk, 0), '77.77'))

    # ------------------------------------------------------------------
    # LINEAR
    # ------------------------------------------------------------------

    def test_linear_single_touchpoint(self):
        path = _make_path('u20', True, '100.00', [self.ch2.pk])
        result = linear([path])
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '100.00'),
                        f"Single touchpoint should receive 100%, got {result.get(self.ch2.pk)}")

    def test_linear_two_touchpoints(self):
        path = _make_path('u21', True, '100.00', [self.ch1.pk, self.ch2.pk])
        result = linear([path])
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '50.00'),
                        f"ch1 expected 50.00, got {result.get(self.ch1.pk)}")
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '50.00'),
                        f"ch2 expected 50.00, got {result.get(self.ch2.pk)}")

    def test_linear_three_touchpoints_precision(self):
        """100 / 3 = 33.3333... each, verifying Decimal-level precision."""
        path = _make_path('u22', True, '100.00',
                          [self.ch1.pk, self.ch2.pk, self.ch3.pk])
        result = linear([path])
        expected_each = Decimal('100') / Decimal('3')
        for ch in (self.ch1, self.ch2, self.ch3):
            actual = result.get(ch.pk, Decimal('0'))
            self.assertTrue(_almost_equal(actual, expected_each),
                            f"{ch.name} expected {expected_each}, got {actual}")
        # total check
        total = sum(result.values(), Decimal('0'))
        self.assertTrue(_almost_equal(total, '100.00'),
                        f"Sum should be 100.00, got {total}")

    def test_linear_five_touchpoints_precision(self):
        """99.99 / 5 = 19.998 each, total exact at Decimal precision."""
        path = _make_path('u23', True, '99.99',
                          [self.ch1.pk, self.ch2.pk, self.ch3.pk,
                           self.ch4.pk, self.ch1.pk])  # ch1 appears twice
        result = linear([path])
        expected_share = Decimal('99.99') / Decimal('5')
        # ch1 gets share * 2 = 39.996; others get 19.998 each
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), expected_share * 2),
                        f"ch1 expected {expected_share * 2}, got {result.get(self.ch1.pk)}")
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), expected_share))
        self.assertTrue(_almost_equal(result.get(self.ch3.pk, 0), expected_share))
        self.assertTrue(_almost_equal(result.get(self.ch4.pk, 0), expected_share))
        total = sum(result.values(), Decimal('0'))
        self.assertTrue(_almost_equal(total, '99.99'),
                        f"Total expected 99.99, got {total}")

    def test_linear_unconverted_ignored(self):
        p_conv    = _make_path('u24', True,  '30.00', [self.ch1.pk, self.ch2.pk])
        p_no_conv = _make_path('u25', False, '999.99',
                               [self.ch3.pk, self.ch4.pk, self.ch1.pk])
        result = linear([p_conv, p_no_conv])
        # only p_conv counts: 15 + 15
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '15.00'),
                        f"ch1 expected 15.00, got {result.get(self.ch1.pk)}")
        self.assertTrue(_almost_equal(result.get(self.ch2.pk, 0), '15.00'))
        self.assertNotIn(self.ch3.pk, result)
        self.assertNotIn(self.ch4.pk, result,
                         "Unconverted path should not add any credits (even to ch4)")

    def test_linear_zero_conversion_value(self):
        p_zero = _make_path('u26', True, '0.00',
                            [self.ch1.pk, self.ch2.pk, self.ch3.pk, self.ch4.pk])
        p_real = _make_path('u27', True, '40.00',
                            [self.ch1.pk, self.ch3.pk])  # 20 + 20
        result = linear([p_zero, p_real])
        for ch in (self.ch1, self.ch2, self.ch3, self.ch4):
            val = result.get(ch.pk, Decimal('0'))
            # ch2 & ch4 only in zero-value path => should be exactly 0
            if ch in (self.ch2, self.ch4):
                self.assertTrue(_almost_equal(val, '0'),
                                f"{ch.name} should be 0, got {val}")
        self.assertTrue(_almost_equal(result.get(self.ch1.pk, 0), '20.00'))
        self.assertTrue(_almost_equal(result.get(self.ch3.pk, 0), '20.00'))

    def test_linear_no_touchpoints(self):
        path = ConversionPath.objects.create(user_id='u_linear_empty',
                                             converted=True,
                                             conversion_value='999.00')
        result = linear([path])
        self.assertEqual(result, {},
                         "Converted path with no touchpoints yields no credits")

    def test_linear_decimal_precision_non_divisible(self):
        """1.00 / 3 must remain at exact Decimal precision, not float rounding."""
        path = _make_path('u28', True, '1.00',
                          [self.ch1.pk, self.ch2.pk, self.ch3.pk])
        result = linear([path])
        total = sum(result.values(), Decimal('0'))
        # At the minimum, total must equal input value within tolerance
        self.assertTrue(_almost_equal(total, '1.00'),
                        f"Sum of shares must equal 1.00, got {total}")
        # No channel should receive more than ceil(1/3) = 0.34
        for ch in (self.ch1, self.ch2, self.ch3):
            val = result.get(ch.pk, Decimal('0'))
            self.assertLessEqual(val, Decimal('0.34'),
                                 f"No share should exceed 0.34, got {val} for {ch.name}")

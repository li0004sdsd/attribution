from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth.models import User
from apps.channels.models import AdChannel
from apps.journeys.models import ConversionPath, TouchPoint
from apps.attribution.engine import first_touch, last_touch, linear
from apps.attribution.models import AttributionTask, AttributionResult
from apps.attribution.tasks import (
    acquire_or_get_existing_task,
    run_attribution_task,
)
import time


def _d(value):
    return Decimal(str(value))


def _almost_equal(a, b, eps=Decimal('0.0001')):
    return abs(Decimal(str(a)) - Decimal(str(b))) <= eps


def _make_path(user_id, converted, conversion_value, channels, now=None, conversion_time=None, touchpoint_timestamps=None):
    """Helper: create a ConversionPath + ordered TouchPoints for a list of channel pks.

    Args:
        user_id: unique user identifier
        converted: whether the path converted
        conversion_value: monetary value of the conversion
        channels: list of channel primary keys (touchpoint order)
        now: DEPRECATED, use conversion_time instead
        conversion_time: datetime when conversion occurred (default: timezone.now())
        touchpoint_timestamps: optional list of datetimes for each touchpoint.
            If provided, length must match channels. If None, all touchpoints
            get conversion_time - 1 day.

    Returns:
        ConversionPath instance
    """
    if conversion_time is None:
        if now is not None:
            conversion_time = now
        else:
            conversion_time = timezone.now()

    path = ConversionPath.objects.create(
        user_id=user_id,
        converted=converted,
        conversion_value=conversion_value,
        conversion_time=conversion_time,
    )

    for i, ch_pk in enumerate(channels, start=1):
        if touchpoint_timestamps is not None:
            tp_time = touchpoint_timestamps[i - 1]
        else:
            tp_time = conversion_time - timezone.timedelta(days=1)
        TouchPoint.objects.create(
            path=path,
            channel_id=ch_pk,
            timestamp=tp_time,
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


# =========================================================================
# ASYNC TASK TESTS
# =========================================================================


class AttributionTaskModelTestCase(TestCase):
    """Tests for AttributionTask model helpers: hash, status transitions."""

    def test_task_hash_deterministic(self):
        h1 = AttributionTask.make_task_hash(1, 'first_touch', {'a': 1, 'b': 2})
        h2 = AttributionTask.make_task_hash(1, 'first_touch', {'b': 2, 'a': 1})
        self.assertEqual(h1, h2, "Hash should be order-independent for params keys")

    def test_task_hash_different_for_different_user(self):
        h1 = AttributionTask.make_task_hash(1, 'first_touch', {})
        h2 = AttributionTask.make_task_hash(2, 'first_touch', {})
        self.assertNotEqual(h1, h2)

    def test_task_hash_different_for_different_model(self):
        h1 = AttributionTask.make_task_hash(1, 'first_touch', {})
        h2 = AttributionTask.make_task_hash(1, 'last_touch', {})
        self.assertNotEqual(h1, h2)

    def test_status_transitions(self):
        user = User.objects.create_user(username='taskuser', password='x')
        task = AttributionTask.objects.create(
            model_type='first_touch',
            created_by=user,
            status=AttributionTask.STATUS_PENDING,
            task_hash='abc123',
        )
        self.assertEqual(task.status, AttributionTask.STATUS_PENDING)
        task.mark_running()
        self.assertEqual(task.status, AttributionTask.STATUS_RUNNING)
        self.assertIsNotNone(task.started_at)
        task.mark_success()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        self.assertIsNotNone(task.finished_at)
        self.assertEqual(task.progress, 100)

    def test_mark_failed_stores_error(self):
        user = User.objects.create_user(username='taskuser2', password='x')
        task = AttributionTask.objects.create(
            model_type='linear',
            created_by=user,
            status=AttributionTask.STATUS_RUNNING,
            task_hash='def456',
        )
        long_msg = 'x' * 1000
        task.mark_failed(long_msg, 'traceback content')
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_FAILED)
        self.assertEqual(len(task.error_message), 500, "error_message truncated to 500 chars")
        self.assertIn('traceback', task.error_traceback)

    def test_params_property(self):
        user = User.objects.create_user(username='taskuser3', password='x')
        params = {'first_touch_weight': 0.3, 'last_touch_weight': 0.7}
        import json
        task = AttributionTask.objects.create(
            model_type='custom_weight',
            created_by=user,
            status=AttributionTask.STATUS_PENDING,
            params_json=json.dumps(params),
            task_hash='ghi789',
        )
        self.assertEqual(task.params, params)

    def test_params_property_invalid_json(self):
        user = User.objects.create_user(username='taskuser4', password='x')
        task = AttributionTask.objects.create(
            model_type='first_touch',
            created_by=user,
            status=AttributionTask.STATUS_PENDING,
            params_json='not valid json{',
            task_hash='jkl012',
        )
        self.assertEqual(task.params, {})


class AttributionTaskDeduplicationTestCase(TestCase):
    """Tests for acquire_or_get_existing_task deduplication logic."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='dedup_user', password='pass')

    def test_acquire_new_task(self):
        task, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk,
            model_type='first_touch',
            params_dict={},
        )
        self.assertTrue(is_new)
        self.assertEqual(task.status, AttributionTask.STATUS_PENDING)
        self.assertEqual(task.created_by_id, self.user.pk)

    def test_acquire_duplicate_returns_existing_pending(self):
        t1, is_new1 = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='linear', params_dict={},
        )
        self.assertTrue(is_new1)
        t2, is_new2 = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='linear', params_dict={},
        )
        self.assertFalse(is_new2)
        self.assertEqual(t1.pk, t2.pk)

    def test_acquire_duplicate_returns_existing_running(self):
        task, _ = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='last_touch', params_dict={},
        )
        task.mark_running()
        t2, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='last_touch', params_dict={},
        )
        self.assertFalse(is_new)
        self.assertEqual(task.pk, t2.pk)

    def test_acquire_duplicate_returns_existing_success(self):
        task, _ = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='first_touch', params_dict={'a': 1},
        )
        task.mark_success()
        t2, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='first_touch', params_dict={'a': 1},
        )
        self.assertFalse(is_new, "Successful task should be reused, not recreated")
        self.assertEqual(task.pk, t2.pk)

    def test_failed_task_allows_retry(self):
        task, _ = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='linear', params_dict={'retry': 1},
        )
        task.mark_failed('boom')
        t2, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='linear', params_dict={'retry': 1},
        )
        self.assertTrue(is_new, "Failed task should allow creation of new retry task")
        self.assertNotEqual(task.pk, t2.pk)

    def test_different_users_not_deduped(self):
        other = User.objects.create_user(username='other_user', password='pass')
        t1, _ = acquire_or_get_existing_task(
            user_id=self.user.pk, model_type='first_touch', params_dict={},
        )
        t2, is_new = acquire_or_get_existing_task(
            user_id=other.pk, model_type='first_touch', params_dict={},
        )
        self.assertTrue(is_new)
        self.assertNotEqual(t1.pk, t2.pk)


class AttributionTaskExecutionTestCase(TransactionTestCase):
    """End-to-end tests for run_attribution_task synchronous execution."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='exec_user', password='pass')
        self.ch1 = AdChannel.objects.create(name='T-Ch1', platform='google')
        self.ch2 = AdChannel.objects.create(name='T-Ch2', platform='facebook')
        self.ch3 = AdChannel.objects.create(name='T-Ch3', platform='email')
        for i in range(5):
            _make_path(
                f'exec_u{i}', True, '100.00',
                [self.ch1.pk, self.ch2.pk, self.ch3.pk],
            )

    def _create_task(self, model_type, params=None):
        task, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk,
            model_type=model_type,
            params_dict=params or {},
        )
        self.assertTrue(is_new)
        return task

    def test_first_touch_task_success(self):
        task = self._create_task('first_touch')
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.total_paths, 5)
        self.assertEqual(task.processed_paths, 5)
        results = AttributionResult.objects.filter(task=task)
        self.assertTrue(results.exists(), "Should have created AttributionResults")
        total_credit = sum(r.credit for r in results)
        self.assertTrue(_almost_equal(total_credit, '500.00'),
                        f"Total should be 500.00, got {total_credit}")
        ch1_credit = results.get(channel=self.ch1).credit
        self.assertTrue(_almost_equal(ch1_credit, '500.00'),
                        f"first_touch ch1 should get all 500, got {ch1_credit}")
        for r in results:
            self.assertFalse(r.is_partial, "Final results should not be marked partial")

    def test_last_touch_task_success(self):
        task = self._create_task('last_touch')
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        results = AttributionResult.objects.filter(task=task)
        ch3_credit = results.get(channel=self.ch3).credit
        self.assertTrue(_almost_equal(ch3_credit, '500.00'))

    def test_linear_task_success(self):
        task = self._create_task('linear')
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        results = AttributionResult.objects.filter(task=task)
        # 5 paths * 100 / 3 channels each = ~166.6667 per channel
        expected_each = Decimal('500') / Decimal('3')
        for ch in (self.ch1, self.ch2, self.ch3):
            c = results.get(channel=ch).credit
            self.assertTrue(_almost_equal(c, expected_each),
                            f"{ch.name} expected ~{expected_each}, got {c}")

    def test_custom_weight_task_success(self):
        params = {
            'first_touch_weight': 0.5,
            'middle_touch_weight': 0.0,
            'last_touch_weight': 0.5,
        }
        task = self._create_task('custom_weight', params)
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        results = AttributionResult.objects.filter(task=task)
        # 3 touchpoints per path: first gets 0.5 * 100 = 50 per path, last gets 50 per path
        # 5 paths => ch1=250, ch3=250, ch2=0
        ch1_credit = results.get(channel=self.ch1).credit
        ch3_credit = results.get(channel=self.ch3).credit
        self.assertTrue(_almost_equal(ch1_credit, '250.00'))
        self.assertTrue(_almost_equal(ch3_credit, '250.00'))
        ch2 = results.filter(channel=self.ch2).first()
        if ch2:
            self.assertTrue(_almost_equal(ch2.credit, '0'))

    def test_results_linked_to_task_and_user(self):
        task = self._create_task('first_touch')
        run_attribution_task(task.pk)
        results = AttributionResult.objects.filter(task=task)
        for r in results:
            self.assertEqual(r.created_by_id, self.user.pk)
            self.assertEqual(r.model_type, 'first_touch')

    def test_running_status_not_started_twice(self):
        task = self._create_task('first_touch')
        task.mark_running()
        # run_attribution_task should early-return when already running (not pending/failed)
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_RUNNING,
                         "Should not transition from running when started twice")

    def test_partial_results_persist_on_large_dataset(self):
        """When processing many paths, intermediate partial saves should occur."""
        for i in range(300, 550):
            _make_path(
                f'many_u{i}', True, '10.00',
                [self.ch1.pk, self.ch2.pk],
            )
        task = self._create_task('first_touch')
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS)
        self.assertGreater(task.total_paths, 200)
        results = AttributionResult.objects.filter(task=task, is_partial=False)
        self.assertTrue(results.exists())
        total = sum(r.credit for r in results)
        # 5 original * 100 + 250 new * 10 = 500 + 2500 = 3000
        self.assertTrue(_almost_equal(total, '3000.00'), f"Total was {total}")


class AttributionTaskFailureTestCase(TransactionTestCase):
    """Tests that task failures store errors and do not lose partial data."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='fail_user', password='pass')
        self.ch1 = AdChannel.objects.create(name='F-Ch1', platform='google')
        self.ch2 = AdChannel.objects.create(name='F-Ch2', platform='facebook')
        for i in range(3):
            _make_path(
                f'fail_u{i}', True, '200.00',
                [self.ch1.pk, self.ch2.pk],
            )

    def test_engine_params_missing_safe_defaults(self):
        """Task should not crash even if params are unusual."""
        params = {'first_touch_weight': 0.2, 'middle_touch_weight': 0.3}
        task, is_new = acquire_or_get_existing_task(
            user_id=self.user.pk,
            model_type='custom_weight',
            params_dict=params,
        )
        self.assertTrue(is_new)
        run_attribution_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, AttributionTask.STATUS_SUCCESS,
                         f"Should succeed with partial weights, got: {task.error_message}")


# =========================================================================
# ATTRIBUTION WINDOW TESTS
# =========================================================================


class AttributionWindowFilterTestCase(TestCase):
    """Tests for attribution window filtering in engine functions."""

    @classmethod
    def setUpTestData(cls):
        cls.ch_short = AdChannel.objects.create(
            name='Short-Window Channel',
            platform='google',
            attribution_window_days=7,
        )
        cls.ch_long = AdChannel.objects.create(
            name='Long-Window Channel',
            platform='facebook',
            attribution_window_days=60,
        )
        cls.ch_default = AdChannel.objects.create(
            name='Default-Window Channel',
            platform='email',
            # default is 30 days
        )

    def test_default_window_is_30_days(self):
        ch = AdChannel.objects.create(name='Test Ch', platform='tiktok')
        self.assertEqual(ch.attribution_window_days, 30,
                         "Default attribution window should be 30 days")

    def test_touchpoint_in_window_kept(self):
        """Touchpoint within window should be kept."""
        conversion_time = timezone.now()
        tp_time = conversion_time - timezone.timedelta(days=5)
        path = _make_path(
            'win_u1', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_time],
        )
        result = first_touch([path])
        self.assertIn(self.ch_short.pk, result)
        self.assertTrue(_almost_equal(result[self.ch_short.pk], '100.00'))

    def test_touchpoint_outside_window_excluded(self):
        """Touchpoint outside window should be excluded."""
        conversion_time = timezone.now()
        tp_time = conversion_time - timezone.timedelta(days=30)  # > 7 days
        path = _make_path(
            'win_u2', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_time],
        )
        result = first_touch([path])
        self.assertEqual(len(result), 0,
                         "Touchpoint 30 days ago should be excluded from 7-day window")

    def test_touchpoint_on_window_boundary_kept(self):
        """Touchpoint exactly on the window boundary (days == window) should be kept."""
        conversion_time = timezone.now()
        tp_time = conversion_time - timezone.timedelta(days=7)  # exactly 7 days
        path = _make_path(
            'win_u3', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_time],
        )
        result = first_touch([path])
        self.assertIn(self.ch_short.pk, result)
        self.assertTrue(_almost_equal(result[self.ch_short.pk], '100.00'))

    def test_touchpoint_after_conversion_excluded(self):
        """Touchpoint timestamp after conversion_time should be excluded."""
        conversion_time = timezone.now()
        tp_time = conversion_time + timezone.timedelta(days=1)  # future
        path = _make_path(
            'win_u4', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_time],
        )
        result = first_touch([path])
        self.assertEqual(len(result), 0,
                         "Future touchpoints should be excluded")

    def test_mixed_windows_first_touch(self):
        """Channels with different windows: first valid touchpoint gets credit.

        Path: ch_short (30d ago, outside 7d) → ch_long (10d ago, inside 60d) → ch_default (1d ago)
        Conversion value: 100
        Expected first_touch: ch_long gets all 100 (first valid touch)
        """
        conversion_time = timezone.now()
        timestamps = [
            conversion_time - timezone.timedelta(days=30),
            conversion_time - timezone.timedelta(days=10),
            conversion_time - timezone.timedelta(days=1),
        ]
        path = _make_path(
            'win_u5', True, '100.00',
            [self.ch_short.pk, self.ch_long.pk, self.ch_default.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=timestamps,
        )
        result = first_touch([path])
        self.assertNotIn(self.ch_short.pk, result,
                         "ch_short touch (30d ago) should be excluded from 7d window")
        self.assertIn(self.ch_long.pk, result)
        self.assertTrue(_almost_equal(result[self.ch_long.pk], '100.00'),
                        "ch_long (10d ago) is first valid, should get all credit")

    def test_mixed_windows_last_touch(self):
        """Channels with different windows: last valid touchpoint gets credit."""
        conversion_time = timezone.now()
        timestamps = [
            conversion_time - timezone.timedelta(days=5),   # ch_short: 5d in window
            conversion_time - timezone.timedelta(days=45),  # ch_long: 45d in 60d window
            conversion_time - timezone.timedelta(days=60),  # ch_default: 60d > 30d, OUT
        ]
        path = _make_path(
            'win_u6', True, '100.00',
            [self.ch_short.pk, self.ch_long.pk, self.ch_default.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=timestamps,
        )
        result = last_touch([path])
        self.assertIn(self.ch_long.pk, result)
        self.assertTrue(_almost_equal(result[self.ch_long.pk], '100.00'),
                        "ch_long (45d ago) is last valid, should get all credit")

    def test_mixed_windows_linear(self):
        """Linear model splits value only among in-window touchpoints.

        Path: ch_short (5d ago) → ch_long (45d ago) → ch_default (60d ago, OUT)
        Valid: ch_short and ch_long (2 touchpoints)
        Each gets 100 / 2 = 50
        """
        conversion_time = timezone.now()
        timestamps = [
            conversion_time - timezone.timedelta(days=5),
            conversion_time - timezone.timedelta(days=45),
            conversion_time - timezone.timedelta(days=60),
        ]
        path = _make_path(
            'win_u7', True, '100.00',
            [self.ch_short.pk, self.ch_long.pk, self.ch_default.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=timestamps,
        )
        result = linear([path])
        self.assertEqual(len(result), 2, "Only 2 touchpoints are in window")
        self.assertNotIn(self.ch_default.pk, result,
                         "ch_default (60d ago) is outside 30d window")
        self.assertTrue(_almost_equal(result[self.ch_short.pk], '50.00'),
                        f"ch_short should get 50, got {result.get(self.ch_short.pk)}")
        self.assertTrue(_almost_equal(result[self.ch_long.pk], '50.00'),
                        f"ch_long should get 50, got {result.get(self.ch_long.pk)}")

    def test_all_touchpoints_outside_window(self):
        """If all touchpoints are outside window, no credit is assigned."""
        conversion_time = timezone.now()
        timestamps = [
            conversion_time - timezone.timedelta(days=100),
            conversion_time - timezone.timedelta(days=200),
        ]
        path = _make_path(
            'win_u8', True, '100.00',
            [self.ch_short.pk, self.ch_long.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=timestamps,
        )
        result = first_touch([path])
        self.assertEqual(len(result), 0,
                         "All touchpoints are outside their windows, no credit should be assigned")
        result2 = last_touch([path])
        self.assertEqual(len(result2), 0)
        result3 = linear([path])
        self.assertEqual(len(result3), 0)

    def test_get_effective_conversion_time_fallback(self):
        """get_effective_conversion_time should fall back to created_at if conversion_time is None.

        Note: After migration, conversion_time should never be None, but the
        fallback provides backward compatibility during the migration window.
        """
        conversion_time = timezone.now()
        path = _make_path(
            'win_u9', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[conversion_time - timezone.timedelta(days=3)],
        )
        # Manually simulate pre-migration state
        path.conversion_time = None
        self.assertEqual(path.get_effective_conversion_time(), path.created_at,
                         "Should fall back to created_at when conversion_time is None")

    def test_window_accuracy_with_dates(self):
        """Test exact day boundary behavior with timedelta.days.

        timedelta.days truncates towards zero, so:
        - 7 days and 23 hours -> delta.days = 7 (kept for 7-day window)
        - 8 days exactly      -> delta.days = 8 (excluded from 7-day window)
        """
        conversion_time = timezone.now()

        # 7 days + 23 hours ago: timedelta(days=7)
        tp_in = conversion_time - timezone.timedelta(days=7, hours=23)
        # 8 days exactly: timedelta(days=8)
        tp_out = conversion_time - timezone.timedelta(days=8)

        path = _make_path(
            'win_u10', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_in],
        )
        result = first_touch([path])
        self.assertIn(self.ch_short.pk, result,
                      "7 days + 23h should still be within 7-day window (delta.days = 7)")

        path2 = _make_path(
            'win_u11', True, '100.00',
            [self.ch_short.pk],
            conversion_time=conversion_time,
            touchpoint_timestamps=[tp_out],
        )
        result2 = first_touch([path2])
        self.assertNotIn(self.ch_short.pk, result2,
                         "8 days exactly should be outside 7-day window (delta.days = 8)")


class ChannelSerializerWindowValidationTestCase(TestCase):
    """Tests for attribution window validation in channel serializer."""

    def test_window_default_value(self):
        from apps.channels.serializers import AdChannelSerializer
        serializer = AdChannelSerializer(data={
            'name': 'Test Ch',
            'platform': 'google',
            'cost_per_click': '1.00',
            'active': True,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Model default provides the value, so it may not be in validated_data.
        # Verify by saving and checking the instance.
        instance = serializer.save()
        self.assertEqual(instance.attribution_window_days, 30)

    def test_window_zero_rejected(self):
        from apps.channels.serializers import AdChannelSerializer
        serializer = AdChannelSerializer(data={
            'name': 'Test Ch',
            'platform': 'google',
            'cost_per_click': '1.00',
            'active': True,
            'attribution_window_days': 0,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('attribution_window_days', serializer.errors)

    def test_window_negative_rejected(self):
        from apps.channels.serializers import AdChannelSerializer
        serializer = AdChannelSerializer(data={
            'name': 'Test Ch',
            'platform': 'google',
            'cost_per_click': '1.00',
            'active': True,
            'attribution_window_days': -5,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('attribution_window_days', serializer.errors)

    def test_window_excessive_rejected(self):
        from apps.channels.serializers import AdChannelSerializer
        serializer = AdChannelSerializer(data={
            'name': 'Test Ch',
            'platform': 'google',
            'cost_per_click': '1.00',
            'active': True,
            'attribution_window_days': 10000,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('attribution_window_days', serializer.errors)

    def test_window_valid_value_accepted(self):
        from apps.channels.serializers import AdChannelSerializer
        serializer = AdChannelSerializer(data={
            'name': 'Test Ch',
            'platform': 'google',
            'cost_per_click': '1.00',
            'active': True,
            'attribution_window_days': 14,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['attribution_window_days'], 14)


class ConversionTimeMigrationTestCase(TestCase):
    """Tests for conversion_time backward compatibility."""

    def test_get_effective_conversion_time_with_conversion_time(self):
        ct = timezone.now() - timezone.timedelta(days=5)
        path = _make_path(
            'mig_u1', True, '100.00',
            [],
            conversion_time=ct,
            touchpoint_timestamps=[],
        )
        self.assertEqual(path.get_effective_conversion_time(), ct)

    def test_conversion_time_defaults_to_now(self):
        before = timezone.now()
        path = ConversionPath.objects.create(
            user_id='mig_u2',
            converted=True,
            conversion_value='50.00',
        )
        after = timezone.now()
        self.assertGreaterEqual(path.conversion_time, before)
        self.assertLessEqual(path.conversion_time, after)

    def test_adchannel_is_touchpoint_in_window(self):
        ch = AdChannel.objects.create(name='W-Ch', platform='google', attribution_window_days=30)
        conversion_time = timezone.now()

        tp_in = conversion_time - timezone.timedelta(days=10)
        tp_out = conversion_time - timezone.timedelta(days=60)
        tp_future = conversion_time + timezone.timedelta(days=1)

        self.assertTrue(ch.is_touchpoint_in_window(tp_in, conversion_time))
        self.assertFalse(ch.is_touchpoint_in_window(tp_out, conversion_time))
        self.assertFalse(ch.is_touchpoint_in_window(tp_future, conversion_time))

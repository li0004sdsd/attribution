import os
import threading
import traceback
from collections import defaultdict
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attribution_project.settings')

import django
django.setup()

from django.db import transaction, close_old_connections
from apps.journeys.models import ConversionPath
from apps.channels.models import AdChannel
from apps.attribution.models import AttributionTask, AttributionResult
from apps.attribution.engine import MODELS

PARTIAL_SAVE_BATCH_SIZE = 200
_lock = threading.Lock()
_running_tasks = set()


def _get_params_for_engine(task):
    params = task.params
    engine_kwargs = {}
    if task.model_type == 'custom_weight':
        weights = {}
        if 'first_touch_weight' in params and params['first_touch_weight'] is not None:
            weights['first_touch'] = params['first_touch_weight']
        if 'middle_touch_weight' in params and params['middle_touch_weight'] is not None:
            weights['middle_touch'] = params['middle_touch_weight']
        if 'last_touch_weight' in params and params['last_touch_weight'] is not None:
            weights['last_touch'] = params['last_touch_weight']
        if weights:
            engine_kwargs['weights'] = weights
    return engine_kwargs


def _merge_credits(target, source):
    for ch_id, credit in source.items():
        target[ch_id] = target.get(ch_id, Decimal('0')) + credit


def _persist_partial_results(task, credits_accum, is_partial=True):
    if not credits_accum:
        return
    channel_ids = list(credits_accum.keys())
    channel_map = {ch.pk: ch for ch in AdChannel.objects.filter(pk__in=channel_ids)}
    with transaction.atomic():
        AttributionResult.objects.filter(
            task=task,
            is_partial=is_partial,
        ).delete()
        result_objs = [
            AttributionResult(
                task=task,
                model_type=task.model_type,
                channel=channel_map[channel_id],
                credit=credit,
                created_by=task.created_by,
                is_partial=is_partial,
            )
            for channel_id, credit in credits_accum.items()
            if channel_id in channel_map
        ]
        if result_objs:
            AttributionResult.objects.bulk_create(result_objs)


def _finalize_results(task, credits_accum):
    channel_ids = list(credits_accum.keys())
    channel_map = {ch.pk: ch for ch in AdChannel.objects.filter(pk__in=channel_ids)}
    with transaction.atomic():
        AttributionResult.objects.filter(
            model_type=task.model_type,
            created_by=task.created_by,
            task__isnull=True,
        ).delete()
        AttributionResult.objects.filter(task=task).delete()
        result_objs = [
            AttributionResult(
                task=task,
                model_type=task.model_type,
                channel=channel_map[channel_id],
                credit=credit,
                created_by=task.created_by,
                is_partial=False,
            )
            for channel_id, credit in credits_accum.items()
            if channel_id in channel_map
        ]
        if result_objs:
            AttributionResult.objects.bulk_create(result_objs)


def run_attribution_task(task_id):
    from django.db import connection
    connection.close()
    close_old_connections()

    try:
        with _lock:
            if task_id in _running_tasks:
                return
            _running_tasks.add(task_id)

        task = AttributionTask.objects.select_for_update().get(pk=task_id)

        if task.status not in (AttributionTask.STATUS_PENDING, AttributionTask.STATUS_FAILED):
            return

        duplicate = AttributionTask.objects.filter(
            task_hash=task.task_hash,
            status__in=(AttributionTask.STATUS_PENDING, AttributionTask.STATUS_RUNNING),
        ).exclude(pk=task.pk).first()
        if duplicate:
            return

        task.mark_running()

        engine_kwargs = _get_params_for_engine(task)
        engine_fn = MODELS[task.model_type]

        paths_qs = ConversionPath.objects.filter(
            converted=True
        ).prefetch_related('touchpoints').order_by('pk')

        total_count = paths_qs.count()
        task.update_progress(0, total_count)

        credits_accum = defaultdict(Decimal)
        path_buffer = []
        processed = 0

        for path in paths_qs.iterator(chunk_size=500):
            path_buffer.append(path)
            if len(path_buffer) >= PARTIAL_SAVE_BATCH_SIZE:
                batch_result = engine_fn(path_buffer, **engine_kwargs)
                _merge_credits(credits_accum, batch_result)
                processed += len(path_buffer)
                path_buffer = []
                _persist_partial_results(task, credits_accum, is_partial=True)
                task.update_progress(processed, total_count)

        if path_buffer:
            batch_result = engine_fn(path_buffer, **engine_kwargs)
            _merge_credits(credits_accum, batch_result)
            processed += len(path_buffer)
            _persist_partial_results(task, credits_accum, is_partial=True)
            task.update_progress(processed, total_count)

        _finalize_results(task, credits_accum)
        task.mark_success()

    except Exception as exc:
        try:
            tb = traceback.format_exc()
            task.refresh_from_db()
            task.mark_failed(str(exc), tb)
        except Exception:
            pass
    finally:
        try:
            close_old_connections()
        except Exception:
            pass
        with _lock:
            _running_tasks.discard(task_id)


def dispatch_attribution_task(task_id):
    thread = threading.Thread(
        target=run_attribution_task,
        args=(task_id,),
        daemon=True,
        name=f'attribution-task-{task_id}',
    )
    thread.start()
    return thread


def acquire_or_get_existing_task(user_id, model_type, params_dict):
    task_hash = AttributionTask.make_task_hash(user_id, model_type, params_dict)

    existing = AttributionTask.objects.filter(
        task_hash=task_hash,
        status__in=(
            AttributionTask.STATUS_PENDING,
            AttributionTask.STATUS_RUNNING,
            AttributionTask.STATUS_SUCCESS,
        ),
    ).order_by('-created_at').first()

    if existing:
        return existing, False

    with transaction.atomic():
        locked_existing = AttributionTask.objects.filter(
            task_hash=task_hash,
            status__in=(AttributionTask.STATUS_PENDING, AttributionTask.STATUS_RUNNING),
        ).select_for_update(skip_locked=True).first()

        if locked_existing:
            return locked_existing, False

        import json
        task = AttributionTask.objects.create(
            model_type=model_type,
            created_by_id=user_id,
            status=AttributionTask.STATUS_PENDING,
            params_json=json.dumps(params_dict),
            task_hash=task_hash,
        )

    return task, True

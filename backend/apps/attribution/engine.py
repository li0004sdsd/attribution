from collections import defaultdict
from decimal import Decimal, InvalidOperation


def _safe_decimal(value, default):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(default))


def first_touch(paths):
    credits = defaultdict(Decimal)
    for path in paths:
        if not path.converted:
            continue
        tps = sorted(path.touchpoints.all(), key=lambda t: t.position)
        if tps:
            credits[tps[0].channel_id] += Decimal(str(path.conversion_value))
    return dict(credits)


def last_touch(paths):
    credits = defaultdict(Decimal)
    for path in paths:
        if not path.converted:
            continue
        tps = sorted(path.touchpoints.all(), key=lambda t: t.position)
        if tps:
            credits[tps[-1].channel_id] += Decimal(str(path.conversion_value))
    return dict(credits)


def linear(paths):
    credits = defaultdict(Decimal)
    for path in paths:
        if not path.converted:
            continue
        tps = path.touchpoints.all()
        count = len(tps)
        if count == 0:
            continue
        share = Decimal(str(path.conversion_value)) / Decimal(count)
        for tp in tps:
            credits[tp.channel_id] += share
    return dict(credits)


def custom_weight(paths, weights=None):
    credits = defaultdict(Decimal)

    w_first = _safe_decimal(weights.get('first_touch') if weights else None, Decimal('0.3333'))
    w_middle = _safe_decimal(weights.get('middle_touch') if weights else None, Decimal('0.3334'))
    w_last = _safe_decimal(weights.get('last_touch') if weights else None, Decimal('0.3333'))

    total_weight = w_first + w_middle + w_last
    if total_weight <= 0:
        w_first = w_middle = w_last = Decimal('0.3333')
        w_middle = Decimal('0.3334')
        total_weight = Decimal('1')

    w_first = w_first / total_weight
    w_middle = w_middle / total_weight
    w_last = w_last / total_weight

    for path in paths:
        if not path.converted:
            continue
        tps = sorted(path.touchpoints.all(), key=lambda t: t.position)
        count = len(tps)
        if count == 0:
            continue

        value = Decimal(str(path.conversion_value))

        if count == 1:
            credits[tps[0].channel_id] += value
            continue

        if count == 2:
            middle_sum = w_first + w_last
            if middle_sum == 0:
                share_first = share_last = value / Decimal('2')
            else:
                share_first = value * (w_first / middle_sum)
                share_last = value * (w_last / middle_sum)
            credits[tps[0].channel_id] += share_first
            credits[tps[-1].channel_id] += share_last
            continue

        middle_count = count - 2
        credits[tps[0].channel_id] += value * w_first
        credits[tps[-1].channel_id] += value * w_last
        middle_share = (value * w_middle) / Decimal(middle_count)
        for tp in tps[1:-1]:
            credits[tp.channel_id] += middle_share

    return dict(credits)


MODELS = {
    'first_touch': first_touch,
    'last_touch': last_touch,
    'linear': linear,
    'custom_weight': custom_weight,
}

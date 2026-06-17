from collections import defaultdict
from decimal import Decimal


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


MODELS = {
    'first_touch': first_touch,
    'last_touch': last_touch,
    'linear': linear,
}

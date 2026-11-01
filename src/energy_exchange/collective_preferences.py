"""Finite, explicit soft preferences. Values here are integer paise and Wh."""
from .collective_bargaining import quote_price
from .collective_time import contains, intersection, parse_time


def preferred_window(interval, choice):
    if choice == 'any':
        return None
    start, end = map(parse_time, interval)
    middle = start + (end - start) / 2
    pair = (start, middle) if choice == 'earlier' else (middle, end)
    return tuple(value.isoformat() for value in pair)


def preference_penalty(state, wh, delivery):
    """Per-kWh utility cost, not a payment and never a relaxed hard limit."""
    pref = state.get('preferences')
    if not pref:
        return 0
    cost = 0
    if pref['window'] and (not delivery or not contains(pref['window'], delivery)):
        cost += pref['time_premium']
    small = wh < pref['quantity_wh']
    large = wh > pref['quantity_wh']
    if (pref['quantity_direction'] == 'at_least' and small or
            pref['quantity_direction'] == 'at_most' and large):
        cost += pref['quantity_premium']
    return cost


def preference_quote(state, floor, maximum, tick, position, wh, delivery):
    pref = state.get('preferences')
    if not pref:
        return quote_price(floor, maximum, tick, position)
    penalty = preference_penalty(state, wh, delivery)
    if state['role'] == 'seller':
        reservation = floor + penalty
        target = min(maximum, max(reservation, pref['price_target'] + penalty))
        return quote_price(reservation, target, tick, position) if reservation <= maximum else None
    reservation = maximum - penalty
    target = max(floor, min(reservation, pref['price_target'] - penalty))
    return quote_price(target, reservation, tick, position) if reservation >= floor else None


def delivery_options(first, second):
    """Partition the overlap at real price/preference boundaries only."""
    overlap = intersection(first['interval'], second['interval'])
    if overlap is None:
        return [None]
    start, end = map(parse_time, overlap)
    bounds = {start, end}
    for state in (first, second):
        pref = state.get('preferences')
        candidates = list(pref['window']) if pref and pref['window'] else []
        if state.get('time_price'):
            candidates.append(state['time_price'][0])
        bounds.update(value for raw in candidates if start < (value := parse_time(raw)) < end)
    values = sorted(bounds)
    return [(a.isoformat(), b.isoformat()) for a, b in zip(values, values[1:])]

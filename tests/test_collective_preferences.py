"""Hand-computed preference costs and real package negotiations."""
import copy
import unittest

from src.energy_exchange import collective_engine as engine

EARLY = ('2026-10-28T14:00:00+05:30', '2026-10-28T15:00:00+05:30')
LATE = ('2026-10-28T15:00:00+05:30', '2026-10-28T16:00:00+05:30')


def preferences(**updates):
    result = dict(price_target=7, delivery='later', time_premium=.5,
                  preferred_quantity_kwh=3, quantity_direction='at_least',
                  quantity_premium=.25)
    result.update(updates)
    return result


def household(aid='A01', role='seller', prefs=None, **updates):
    fields = dict(forecast_surplus_kwh=4, reserve_kwh=0, max_offer_kwh=4, min_price=5)
    if role == 'buyer':
        fields = dict(demand_kwh=4, max_price=9, budget=100)
    fields.update(updates)
    agent = engine.make_agent(aid, role, **fields)
    if prefs is not None:
        agent['negotiation_preferences'] = prefs
    return agent


def run_for(profiles):
    cfg, tick, cap = engine._validate_config({'negotiation_mode':'bargaining', 'topology':'open'})
    return engine._Run(engine.make_world(profiles, cfg), cfg, tick, cap, 'baseline')


def trade(wh=2000, price=700, window=EARLY):
    return dict(id='t1', seller_id='A01', buyer_id='A02', wh=wh, paise=price,
                delivery_start=window[0], delivery_end=window[1])


class PreferenceModelTests(unittest.TestCase):
    def test_time_and_quantity_costs_change_actual_household_utility(self):
        run = run_for([household(prefs=preferences()), household('A02', 'buyer')])
        # Cash surplus: (7-5)*2 = 4. Earlier delivery costs 0.50*2;
        # a smaller-than-3 kWh deal costs another 0.25*2. Utility is 2.50.
        self.assertEqual(run.trade_surplus('A01', trade()), 250000)
        self.assertEqual(run.trade_surplus('A01', trade(window=LATE)), 350000)
        self.assertEqual(run.trade_surplus('A01', trade(wh=3000, window=LATE)), 600000)

    def test_buyer_can_trade_a_smaller_deal_preference_for_a_better_price(self):
        prefs = preferences(price_target=6, delivery='any', time_premium=0,
                            preferred_quantity_kwh=2, quantity_direction='at_most')
        run = run_for([household(), household('A02', 'buyer', prefs=prefs)])
        self.assertEqual(run.trade_surplus('A02', trade(wh=3000)), 525000)
        self.assertEqual(run.trade_surplus('A02', trade(wh=3000, price=675)), 600000)

    def test_delivery_must_fit_wholly_inside_preferred_window(self):
        run = run_for([household(prefs=preferences(quantity_premium=0)), household('A02','buyer')])
        crossing = ('2026-10-28T14:30:00+05:30', '2026-10-28T15:30:00+05:30')
        self.assertEqual(run.trade_surplus('A01', trade(window=crossing)), 300000)

    def test_preferred_half_moves_with_an_edited_hard_window(self):
        selling = household(prefs=preferences(quantity_premium=0),
            interval_start='2026-10-28T20:00:00+05:30', interval_end='2026-10-28T22:00:00+05:30')
        run = run_for([selling, household('A02','buyer')])
        preferred = ('2026-10-28T21:00:00+05:30', '2026-10-28T22:00:00+05:30')
        earlier = ('2026-10-28T20:00:00+05:30', '2026-10-28T21:00:00+05:30')
        self.assertEqual(run.trade_surplus('A01', trade(window=preferred)), 400000)
        self.assertEqual(run.trade_surplus('A01', trade(window=earlier)), 300000)

    def test_malformed_preferences_are_rejected_at_world_validation(self):
        bad = [dict(delivery='tomorrow'), dict(time_premium=-.1),
               dict(time_premium=True), dict(time_premium=float('nan')),
               dict(quantity_premium=.001), dict(price_target='cheap'),
               dict(preferred_quantity_kwh=-1), dict(preferred_quantity_kwh=0),
               dict(quantity_direction='whatever'), dict(unknown=1)]
        for patch in bad:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                run_for([household(prefs=preferences(**patch)), household('A02','buyer')])

    def test_neutral_preferences_do_not_change_surplus(self):
        run = run_for([household(prefs=preferences(delivery='any',time_premium=0,quantity_premium=0)),
                       household('A02','buyer')])
        self.assertEqual(run.trade_surplus('A01', trade()), 400000)
        self.assertEqual(run.trade_surplus('A02', trade()), 400000)

    def test_quotes_compensate_for_time_and_clamp_a_stale_target_to_hard_limits(self):
        from src.energy_exchange.collective_preferences import preference_quote
        selling = engine.agent_state(household(prefs=preferences(quantity_premium=0)))
        self.assertEqual(preference_quote(selling,500,900,5,10000,2000,LATE),700)
        self.assertEqual(preference_quote(selling,500,900,5,10000,2000,EARLY),750)
        self.assertEqual(preference_quote(selling,800,900,5,10000,2000,LATE),800)
        self.assertIsNone(preference_quote(selling,900,900,5,10000,2000,EARLY))

    def test_generated_bargaining_world_has_reproducible_varied_preferences(self):
        cfg = {'population':20, 'seed':42, 'negotiation_mode':'bargaining'}
        world = engine.build_world(cfg)
        self.assertEqual(world, engine.build_world(cfg))
        self.assertTrue(all(a.get('negotiation_preferences') for a in world['agents']))
        self.assertGreater(len({a['negotiation_preferences']['delivery'] for a in world['agents']}),1)
        self.assertTrue(all(a.get('negotiation_preferences') is None for a in engine.build_world(
            dict(cfg, negotiation_mode='midpoint'))['agents']))


if __name__ == '__main__':
    unittest.main()

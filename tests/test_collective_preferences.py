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


def paired_profiles(time_premium=.5):
    return [household('A01','buyer', prefs=preferences(price_target=6, delivery='earlier',
                    preferred_quantity_kwh=4, quantity_premium=0)),
            household('A02', prefs=preferences(price_target=7, time_premium=time_premium,
                    preferred_quantity_kwh=4, quantity_premium=0))]


def package_experiment(profiles=None, intervention=None, **options):
    profiles = profiles or paired_profiles()
    cfg = dict(negotiation_mode='bargaining',topology='open',**options)
    world = engine.make_world(profiles,cfg)
    plan = {'version':'bounded-price-plan-v1','source':'fixture','agents':{
        a['id']:{'price_positions':[10000,8000,6000] if a['role']=='seller' else [0,4000,8000]}
        for a in profiles}}
    return engine.run_experiment(cfg,intervention,world=world,strategy_plan=plan)


class PackageNegotiationTests(unittest.TestCase):
    def test_seller_makes_a_real_cheaper_later_counteroffer(self):
        result = package_experiment()
        events = result['baseline']['events']
        counter = next(e for e in events if e['type']=='counteroffer_sent' and e['actor_id']=='A02')
        self.assertEqual((counter['delivery_start'],counter['delivery_end']),LATE)
        self.assertEqual(counter['price'],7)
        self.assertIn('negotiation',counter)
        self.assertEqual(counter['negotiation']['same_terms_quote'],7.5)
        self.assertIn('delivery',counter['negotiation']['changed'])
        previous = next(e for e in events if e['id']==counter['negotiation']['previous_offer_id'])
        self.assertEqual((previous['delivery_start'],previous['delivery_end']),EARLY)
        self.assertEqual(engine.verify_result(result),[])

    def test_less_preferred_delivery_is_accepted_when_the_price_compensates(self):
        result = package_experiment()
        trade = result['baseline']['trades'][0]
        self.assertEqual((trade['delivery_start'],trade['delivery_end']),EARLY)
        self.assertEqual(trade['price'],7.2)
        self.assertEqual(result['baseline']['agents']['A02']['utility'],6.8)
        # A much stronger time preference changes the actual accepted delivery.
        stronger = package_experiment(paired_profiles(time_premium=4))
        self.assertEqual(stronger['baseline']['trades'][0]['delivery_start'],LATE[0])
        self.assertEqual(engine.verify_result(stronger),[])

    def test_agents_counter_on_deal_size_and_ledger_uses_the_accepted_size(self):
        profiles = [household('A01','buyer',prefs=preferences(price_target=6,delivery='any',time_premium=0,
                        preferred_quantity_kwh=2,quantity_direction='at_most',quantity_premium=1.5)),
                    household('A02',min_price=6.5,prefs=preferences(price_target=8,delivery='any',time_premium=0,
                        preferred_quantity_kwh=4,quantity_premium=.5))]
        result = package_experiment(profiles)
        messages = [e for e in result['baseline']['events'] if e['type'] in engine.MESSAGE_TYPES]
        self.assertTrue(any('quantity' in e.get('negotiation',{}).get('changed',[]) for e in messages))
        self.assertEqual(messages[0]['quantity_kwh'],2)
        self.assertTrue(any(e['actor_id']=='A02' and e['quantity_kwh']==4 for e in messages))
        accepted = next(e for e in messages if e['type']=='offer_accepted')
        reserved = result['baseline']['trades'][0]
        for field in ('price','quantity_kwh','delivery_start','delivery_end'):
            self.assertEqual(reserved[field],accepted[field])
        self.assertEqual(engine.verify_result(result),[])

    def test_package_messages_stop_atomically_at_every_small_cap(self):
        for limit in range(8):
            with self.subTest(limit=limit):
                result = package_experiment(max_messages=limit)
                self.assertLessEqual(result['baseline']['messages'],limit)
                self.assertEqual(engine.verify_result(result),[])

    def test_soft_preferences_never_create_energy_outside_hard_windows(self):
        profiles = paired_profiles()
        profiles[0].update(interval_start='2026-10-28T20:00:00+05:30',interval_end='2026-10-28T22:00:00+05:30')
        result = package_experiment(profiles)
        self.assertEqual(result['baseline']['trades'],[])
        self.assertEqual(engine.verify_result(result),[])

    def test_smaller_budget_cannot_retain_a_large_order_discount(self):
        profiles = [household('A01','buyer',max_price=8,budget=13,prefs=preferences(price_target=7)),
                    household('A02',min_price=9,conditional_price={'minimum_kwh':3,'floor':6},
                        prefs=preferences(price_target=9))]
        result = package_experiment(profiles)
        self.assertEqual(result['baseline']['trades'],[])
        self.assertEqual(engine.verify_result(result),[])

    def test_refusals_keep_the_last_offers_exact_terms_and_correct_speaker(self):
        profiles = paired_profiles(time_premium=4)
        profiles[0]['negotiation_preferences']['time_premium']=4
        result = package_experiment(profiles)
        by_id = {e['id']:e for e in result['baseline']['events']}
        rejected = [e for e in by_id.values() if e['type']=='offer_rejected']
        self.assertTrue(rejected)
        for event in rejected:
            previous = by_id[event['caused_by'][-1]]
            self.assertEqual(event['actor_id'],previous['counterparty_id'])
            self.assertEqual(event['counterparty_id'],previous['actor_id'])
            for field in ('price','quantity_kwh','delivery_start','delivery_end'):
                self.assertEqual(event[field],previous[field])
        self.assertEqual(engine.verify_result(result),[])

    def test_same_preferences_and_frozen_plan_replay_and_noop_exactly(self):
        profiles = paired_profiles()
        original = copy.deepcopy(profiles)
        result = package_experiment(profiles,{'agent_id':'A02','scenario':'custom','changes':{'reserve_kwh':0}})
        self.assertEqual(profiles,original)
        self.assertEqual(result['comparison']['changed_trades'],0)
        self.assertEqual(result['baseline']['strategy_plan'],result['intervention']['strategy_plan'])
        self.assertEqual(engine.strip_runtime(result),engine.strip_runtime(package_experiment(profiles,
            {'agent_id':'A02','scenario':'custom','changes':{'reserve_kwh':0}})))
        self.assertEqual(engine.verify_result(result),[])

    def test_forged_tradeoff_explanation_fails_replay_even_after_checksum_update(self):
        result = package_experiment()
        event = next(e for e in result['baseline']['events'] if e.get('negotiation',{}).get('same_terms_quote'))
        event['negotiation']['same_terms_quote'] = .01
        result['manifest']['checksums']['baseline_events'] = engine.fingerprint(result['baseline']['events'])
        self.assertTrue(engine.verify_result(result))

    def test_budget_driven_smaller_counter_does_not_quote_an_unaffordable_old_amount(self):
        profiles = [household('A01',prefs=preferences(delivery='any',time_premium=0,quantity_premium=0)),
                    household('A02','buyer',budget=10,prefs=preferences(price_target=6,delivery='any',
                        time_premium=0,quantity_premium=0))]
        result = package_experiment(profiles)
        counter = next(e for e in result['baseline']['events'] if e['type']=='counteroffer_sent' and e['actor_id']=='A02')
        self.assertLess(counter['quantity_kwh'],counter['negotiation']['previous_terms']['quantity_kwh'])
        self.assertIsNone(counter['negotiation']['same_terms_quote'])
        self.assertLessEqual(counter['price']*counter['quantity_kwh'],10)
        self.assertEqual(engine.verify_result(result),[])

    def test_package_replacement_can_release_both_parties_previous_agreements(self):
        profiles = [household('A01',prefs=preferences(price_target=7,preferred_quantity_kwh=4,quantity_premium=0)),
                    household('A02','buyer',prefs=preferences(price_target=6,delivery='earlier',preferred_quantity_kwh=4,quantity_premium=0)),
                    household('A03',min_price=6,prefs=preferences(price_target=8,preferred_quantity_kwh=4,quantity_premium=0)),
                    household('A04','buyer',max_price=10,prefs=preferences(price_target=7,preferred_quantity_kwh=4,quantity_premium=0))]
        result = package_experiment(profiles)
        replaced = [e for e in result['baseline']['events'] if e['type']=='offer_replaced']
        self.assertEqual({e['actor_id'] for e in replaced},{'A01','A04'})
        self.assertEqual(len({e['transition_id'] for e in replaced}),1)
        self.assertEqual({(t['seller_id'],t['buyer_id']) for t in result['baseline']['trades']},
                         {('A01','A04'),('A03','A02')})
        self.assertEqual(result['baseline']['metrics']['committed_kwh'],8)
        self.assertEqual(engine.verify_result(result),[])

    def test_replacement_explanation_uses_budget_released_by_actual_response(self):
        def prefs(target):
            return preferences(price_target=target,delivery='any',time_premium=0,quantity_premium=0)
        result = package_experiment([
            household('A01',min_price=7.5,prefs=prefs(8)),
            household('A02',min_price=5,prefs=prefs(7)),
            household('A03','buyer',demand_kwh=8,budget=36,prefs=prefs(6))])
        events = result['baseline']['events']
        released = next(e['trade'] for e in events if e['type']=='provisional_released')
        self.assertEqual((released['seller_id'],released['quantity_kwh'],released['price']),('A01',4,7.9))
        counter = next(e for e in events if e['type']=='counteroffer_sent' and
                       e['actor_id']=='A03' and e['counterparty_id']=='A02')
        self.assertEqual((counter['quantity_kwh'],counter['price']),(4,6))
        self.assertEqual(counter['negotiation']['same_terms_quote'],6)
        self.assertEqual(counter['negotiation']['objection'],'price_too_high')
        self.assertNotIn('budget',counter['reason'])
        accepted = next(e for e in events if e['type']=='offer_accepted' and
                        e['actor_id']=='A03' and e['counterparty_id']=='A02')
        self.assertNotEqual(accepted['negotiation']['objection'],'over_budget')
        self.assertEqual(engine.verify_result(result),[])

    def test_affordable_acceptance_does_not_object_to_a_higher_hypothetical_quote(self):
        result = package_experiment([
            household('A01',prefs=preferences(price_target=7,delivery='any',time_premium=0,quantity_premium=0)),
            household('A02','buyer',budget=28,prefs=preferences(price_target=6,delivery='any',time_premium=0,quantity_premium=0))])
        accepted = next(e for e in result['baseline']['events'] if e['type']=='offer_accepted')
        self.assertEqual((accepted['quantity_kwh'],accepted['price']),(4,6.6))
        self.assertLessEqual(accepted['quantity_kwh']*accepted['price'],28)
        self.assertIsNone(accepted['negotiation']['objection'])
        self.assertIsNone(accepted['negotiation']['same_terms_quote'])
        self.assertEqual(engine.verify_result(result),[])

    def test_hard_window_intervention_repairs_trades_and_keeps_other_preferences(self):
        result = package_experiment(intervention={'agent_id':'A02','scenario':'custom','changes':{
            'interval_start':'2026-10-28T20:00:00+05:30','interval_end':'2026-10-28T22:00:00+05:30'}})
        self.assertTrue(result['baseline']['trades'])
        self.assertEqual(result['intervention']['trades'],[])
        self.assertEqual(result['world']['agents'][0],result['updated_world']['agents'][0])
        self.assertEqual(result['baseline']['strategy_plan'],result['intervention']['strategy_plan'])
        self.assertEqual(engine.verify_result(result),[])


if __name__ == '__main__':
    unittest.main()

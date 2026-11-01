# Preference bargaining verification

Households can negotiate price, delivery time and quantity. Optional preferences affect quotes and modeled utility, while firm constraints remain binding. Every acceptance records the exact terms placed in the ledger. The NandaTown Player and its pinned upstream source are unchanged.

## Automated checks

- 186 collective Python tests passed in 47.705 seconds.
- 85 JavaScript tests passed, including new history changes, recorded compromises, escaped messages and historical preference inspection.
- 21 HTTP and Streamlit transport tests passed.
- The frontend build verified 13 pinned NandaTown source files and reproduced the committed generated assets.
- New preference, package and interface tests failed before their implementations and passed afterward. An unaffordable counterfactual quote was also reproduced and corrected.

Hand-computed examples cover a cheaper alternate delivery time, compensation for an inconvenient time, quantity counteroffers, bundle thresholds after a budget reduction, both parties replacing existing agreements, message limits from zero to seven, hard delivery-window edits, and replay tampering. Existing profiles without preferences retain the original behavior.

Generated fallback runs with seed 42 and local discovery reached local stability for 20, 50 and 100 homes. Runtime was approximately 0.075, 0.287 and 1.73 seconds, respectively. All three results passed replay verification. The 100-home run recorded 323 delivery changes and 518 quantity changes among its counteroffers.

## Browser checks

The local Streamlit workspace rendered the actual Player and the expanded negotiation history. A buyer offered ₹6.85/kWh for 9 to 10 PM after receiving an offer of ₹6.65/kWh for 8 to 9 PM. Its recorded quote for the earlier time at the same bargaining step was ₹6.35/kWh. The seller accepted the later offer.

Keyboard focus on that message highlighted both participating homes. The history also showed quantity changes and accepted time compromises. Flexible preferences and firm limits were shown separately in home details. The original instruction "Make the minimum price 3.5" produced and applied a ₹3.50/kWh rule, and comparison rendered both maps.

Preference costs adjust modeled satisfaction, not payments. No extra LLM calls occur during bargaining messages, replay or inspection. Local checks used the disclosed rules fallback.

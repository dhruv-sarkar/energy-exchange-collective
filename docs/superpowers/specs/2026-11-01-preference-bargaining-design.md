# Negotiation with soft preferences

## Intent

Make negotiations explain meaningful trade-offs. A home can object to a price, suggest a different delivery time or amount, and accept a compromise. These messages must describe offers the engine actually evaluates and uses. Keep the existing NandaTown animation and simple desktop workspace.

## Approach

The implementation choice is a bounded package negotiation inside the deterministic engine. It extends the existing frozen price strategies and hard-constraint checks. Adding dialogue alone would not make preferences affect outcomes. Calling an LLM for every message would add cost and make comparisons harder to reproduce. The existing inexpensive, cached LLM may choose price strategies with the new preferences in its context; executable rules choose and validate every offer. No extra LLM calls happen during playback.

## Preferences and limits

Generated bargaining households receive synthetic `negotiation_preferences`: `price_target` (INR/kWh), `delivery` (`earlier`, `later`, or `any`), `time_premium` (INR/kWh), `preferred_quantity_kwh`, `quantity_direction` (`at_least` or `at_most`), and `quantity_premium` (INR/kWh). The monetary premiums explicitly value a preference; they are not additional payments. Preferences are optional for custom worlds, and absent preferences preserve the original bargaining path. These field names and defaults are implementation choices.

Earlier/later means the first/second half of that home's current hard availability window. Accepting delivery outside the preferred half subtracts the time premium per kWh from its utility. A deal on the wrong side of its preferred quantity subtracts the quantity premium per kWh. Price targets set negotiable aspirations; concessions follow the recorded price strategy. A better price can compensate for a less preferred package. The target is clamped to the currently feasible price band for quoting.

Hard price floors/ceilings, conditional floors, energy availability, reserve, demand, budgets, delivery overlap, discovery and replacement rules remain binding. Soft preferences never expand those limits. Energy remains one flexible pool per home, not separate pools for each delivery slot. A new preference changes actual selection/acceptance and is included in replayable world data.

## Negotiation

Offer candidates include subwindows formed by both homes' preferred-time boundaries and any real time-discount boundary. Quantity candidates include the available maximum, each preferred deal size and any bundle threshold. Round to existing integer energy/price ticks. The number of candidates is bounded by these finite sets; no continuous optimizer or new dependency is required.

For homes with preferences, a bilateral session can counter on price, time and quantity. It keeps the existing maximum of three quotes per side and one acceptance/rejection, and respects the global message cap before every message. Counteroffers are selected using the actor's actual preference-adjusted gain; accepted terms must meet the receiver's current price aspiration and both agents' utility/constraint checks. Each reservation uses exactly the last accepted price, quantity and interval. If no agreement is possible, record a clear refusal. Nothing is committed partway through a negotiation.

Every quote records a structured `negotiation` explanation: prior offer ID and terms, changed dimensions, the actor's objection/preference, and (when changing a package) its quote for the previous package at the same concession step. This last comparison permits a truthful "cheaper at another time" explanation without attributing every price change to time. Messages reveal only what the speaker offers or elects to explain. Inspector-only private settings stay separate.

## Interface

Use short, ordinary-language offer explanations and visible badges for changed price, time or quantity in the permanent history. A disclosure explains the recorded trade-off. Show "Flexible preferences" separately from "Firm limits" in the selected-home details. Use the historical profile at the current replay step. Keep hover, keyboard highlighting, all earlier messages, before/after comparison and simple price prompts working.

## Verification and delivery

Fixtures must prove that a later delivery can receive a lower real quote, a different quantity can be negotiated, a soft preference can be traded for price, impossible hard limits remain impossible, and exhausted messages leave atomic valid state. Test determinism, unchanged frozen plans during interventions, historical explanations, exact accepted terms, edited availability and tampered replay data. Check 20/50/100 homes and bounded runtime. Keep old no-preference and midpoint cases passing.

Implement inline with a fresh whole-branch review. Publish several logical commits to the existing public repository, preserve them when merging, and verify the current Streamlit app. Public materials contain no private chats or credentials.

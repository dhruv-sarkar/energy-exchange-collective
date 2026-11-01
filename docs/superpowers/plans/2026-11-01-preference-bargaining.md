# Preference Bargaining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make price, delivery-time and quantity preferences drive real, understandable counteroffers.

**Architecture:** Optional household preferences feed a finite package search and preference-adjusted utility. Existing price plans, atomic reservation checks and replay validation remain the authority. The UI explains structured recorded offers.

**Tech Stack:** Pure Python engine, existing JavaScript UI and React/D3 NandaTown Player, Streamlit, unittest and Node tests.

**Spec:** ../specs/2026-11-01-preference-bargaining-design.md

## Global Constraints

- Hard limits remain binding; one energy pool per home; no extra per-message LLM calls.
- At most three quotes per side, with every message subject to the existing global cap.
- Exact accepted terms must match the ledger; replay stays deterministic.
- Preserve existing no-preference and midpoint behavior, NandaTown source and accessibility.
- Keep secrets and private attachments out of the public repository. Publish multiple commits.

## Review Focus

- Quantity shrinking below a conditional discount threshold must reprice or refuse.
- A delivery-window edit must not leave a stale absolute soft preference or invalid existing trade.
- Replacement proposals must use the correct remaining budget and gain for both parties.
- A refusal must identify the actual last offer; a later package cannot inherit an earlier offer's quantity or time.
- Preferences and explanations must replay identically with or without LLM availability.

### Task 1: validated preferences and utility

**Files:** Create `src/energy_exchange/collective_preferences.py` and `tests/test_collective_preferences.py`; modify `collective_engine.py`, `collective_llm.py`, and LLM tests.

**Interfaces:** Profiles gain optional `negotiation_preferences`; normalized agent state holds integer preference values and a derived preferred window. Helpers expose `delivery_options(first, second)`, `preference_penalty(state, wh, delivery)`, and `preference_quote(state, floor, maximum, tick, position, wh, delivery)`; the penalty and quote are integer paise per kWh.

- [x] Write failing tests for validated fields, zero/default preferences, a 50-paise time penalty and 25-paise quantity penalty, clamped targets after a policy edit, and preference context in the frozen planner.
- [x] Run `python -m unittest tests.test_collective_preferences tests.test_collective_llm`; confirm failures belong to the missing behavior.
- [x] Implement finite validated preference data, deterministic generated examples, helper calculations and utility integration. Include both interval endpoints when evaluating a delivery. Bump engine/planner provenance; preserve the no-preference path.
- [x] Run all Python tests, then commit the preference model and fixtures.

### Task 2: bounded package counteroffers

**Files:** Modify `collective_engine.py` and `collective_preferences.py`; extend `tests/test_collective_preferences.py`.

**Interfaces:** `_Run.bargain` dispatches to package bargaining only when either participant has preferences. Quote events carry `negotiation` with previous offer/terms, changed dimensions, preference explanations and same-step prior-package quote. All reservations continue through `checked_terms` and `reserve`.

- [x] Write failing pair fixtures for cheaper later delivery, quantity changes, compensated time compromise, strict budgets/floors/bundle thresholds, limits 0–7, replacements and replay tampering.
- [x] Run the fixtures and record the observed failures.
- [x] Enumerate bounded time/quantity alternatives, reprice after quantity adjustments, choose honest counteroffers, emit their explanations and reserve only the accepted terms. Keep actual speaker/receiver and previous terms intact on rejection.
- [x] Run all Python tests and benchmark generated 20/50/100-home runs; verify replay and unchanged interventions. Commit engine behavior separately.

### Task 3: understandable history and preference inspection

**Files:** Modify `src/energy_exchange/web/collective.js`, `collective.css`, `index.html`, and UI tests.

**Interfaces:** Consume recorded `event.negotiation` only; use `frameWorld()` for inspector preferences. No additional simulation or invented motives in the UI.

- [x] Write failing UI tests for price/time/quantity changes, historical preferences, plain-language explanation, safe escaping and absence of invented changes when metadata is missing.
- [x] Implement concise explanations, change badges, optional trade-off detail and separate flexible preferences from firm limits.
- [x] Run `npm test`, Python transport tests, and local browser checks including a real time/quantity negotiation, the original 3.5 prompt, keyboard highlighting and comparison.
- [x] Update public documentation and commit the interface separately.

### Task 4: review and deployment

- [x] Obtain a fresh whole-branch review and fix material findings with failing tests first.
- [x] Run full Python/JavaScript checks and source/build verification; inspect 50/100-home runtime and history behavior.
- [ ] Push, create a concrete PR, wait for CI, merge without squashing, and verify the deployed Streamlit negotiation and prompt flow.
- [ ] Record evidence and save a live screenshot. Leave the workspace clean and the live app available.

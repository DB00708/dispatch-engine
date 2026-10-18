# Algorithm comparison: Greedy vs Hungarian vs Regret

**Bottom line:** batch the tickets and use Hungarian. It is provably optimal for the objective we
care about, it was never beaten in the 50 seeded test scenarios or the 120 sweep scenarios,
and on 30 × 45 inputs it runs in about 0.1 ms. Greedy is the right tool only when one urgent ticket must be dispatched
the instant it arrives.

All numbers below come from `python -m scripts.run_sweep` (30 tickets, engineer-to-ticket
ratio 0.3 → 1.5, 20 seeded scenarios per ratio, default weights). Full table:
[algorithm-comparison-results.md](algorithm-comparison-results.md). The UI's Experiment tab
runs the same sweep and draws it.

## What is being compared

| | Greedy | Hungarian | Regret |
| --- | --- | --- | --- |
| Idea | Most urgent ticket first, take its cheapest free engineer | Solve the whole ticket × engineer grid at once | Serve first the ticket that loses most by waiting |
| Optimal? | No | Yes, for "pair costs + unserved penalties" | No |
| Complexity | O(n · m) | O(n³), SciPy `linear_sum_assignment` | O(n² · m) |
| Online use | Yes, one ticket at a time | Needs a batch (dispatch round) | Needs a batch |

The objective every algorithm is scored on is the same: the sum of the pairing costs
(distance and deadline-margin terms) plus a penalty for each unserved ticket (P1 = 100,
P2 = 30, P3 = 10). Hungarian minimises exactly this, using one dummy "unassigned" column
per ticket.

## Findings

**1. Greedy's gap depends on scarcity, and "biggest" depends on how you measure it.**

| Engineers per ticket | 0.3 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Greedy gap, % of Hungarian's objective | 7.7% | 19.9% | 23.9% | 165.8% | 116.5% | 38.3% |
| Greedy gap, absolute objective points | +26.6 | +39.1 | +20.2 | +24.2 | +11.2 | +3.1 |

- In relative terms the gap peaks when engineers and tickets are balanced (ratio 1.0).
  There, Hungarian serves almost everything (objective 18.7), so every ticket Greedy strands
  costs a lot in percent.
- In absolute terms the gap is largest at ratio 0.5: about 39 points per scenario, roughly
  one extra P2 ticket left unserved.
- At both extremes the gap shrinks. With very few engineers, every algorithm can only serve
  the obvious urgent work. With plenty of engineers, everyone gets served.

**2. The spread matters as much as the mean.** In the worst 10% of scenarios Greedy ran
47–311% over Hungarian at every ratio from 0.5 to 1.25. A dispatcher feels the bad days, not
the average.

**3. Hungarian serves the most tickets at every ratio.** At ratio 1.0 it covers 97.2% of
tickets against Greedy's 89.7%: 7.5 more points, with the same engineers.

**4. Regret protects tickets with few options, not urgent ones.** Under scarcity (ratio 0.3)
its P1 coverage drops to 64.2%, against 83.1% for Hungarian and 79.6% for Greedy. A P3 ticket
that only one engineer can reach shows a large regret (its penalty minus that pairing's cost),
so it jumps the queue ahead of a P1 that has two candidates. This is a real property of the
heuristic, not a bug, and it is why Regret is the worst of the three under scarcity.

**5. Speed is not a deciding factor at this size.** Mean runtimes were 0.06–0.11 ms
(Hungarian), 0.15–0.26 ms (Greedy) and 0.37–1.74 ms (Regret). SciPy's compiled solver makes
Hungarian the fastest here despite its O(n³) bound.

## Example: the greedy trap

The test `test_greedy_trap_hungarian_wins` builds the smallest case where Greedy fails.
Four points sit on one north–south road:

```
T2 (P1) ---- 12 km ---- E_A ---- 8 km ---- T1 (P1) ---- 12 km ---- E_B
```

- **Greedy** serves T1 first (earlier deadline) and picks its nearest engineer, E_A (8 km).
  T2's only other option, E_B, is 32 km away, over the 30 km limit, so T2 is left
  unserved: a 100-point P1 penalty.
- **Hungarian** sends E_B to T1 (12 km) and E_A to T2 (12 km). Both P1 tickets are served
  for 16 km more travel in total (24 km against 8 km).

## Recommendation

- Run dispatch in rounds every few minutes and assign each round with Hungarian.
- When a P1 arrives between rounds, assign it greedily at once, then let the next round
  re-optimise everything else (a rolling horizon).
- Keep Regret out of production; it is useful in this project as a contrast, because it
  shows that "smart" heuristics can fail in the cases that matter most.

## Limits of this comparison

- Synthetic data: fault mix, deadlines and shifts come from a seeded generator.
- One job per engineer per round, straight-line distance × 1.3 and a constant 30 km/h.
- Durations are a fixed mean per fault type (no ML estimator in this build), so the
  deadline check has no spread built in.

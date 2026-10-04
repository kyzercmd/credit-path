# Task 2 Report: Synthetic Data Generator (B1)

## Status
DONE

## Commits
d1dc9a6

## Test Summary
10 tests passed covering determinism, table shapes, persona distributions, leakage-free splits, group differences, seasonality, shortfall, and bill on-time correlations.

## Concerns
- Generation of 10,000 customers takes around 1-2 minutes because of the granular event simulation (365 days x 10000). The loop in `generator.py` is somewhat optimized but largely loops over customers. It is perfectly fine as a one-off offline script.

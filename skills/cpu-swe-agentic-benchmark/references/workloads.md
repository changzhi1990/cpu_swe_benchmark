# Workloads

## `algorithm_lab_sorting_bugfix`

Template: `repo_templates/algorithm_lab`

Agent fixes:

```text
src/algorithm_lab/sorting.py
```

Validation:

```bash
PYTHONPATH=src python3 -m pytest tests/test_sorting.py && echo VALIDATION_PASSED
```

Purpose: CPU-intensive Python-level bubble sort workload. Tests exercise 10000 and 20000 element arrays and reject built-in sorting shortcuts.

## `memory_lab_bandwidth_bugfix`

Template: `repo_templates/memory_lab`

Agent fixes:

```text
src/memory_lab/bandwidth.py
```

Bug pattern:

```python
# result += c  # BUG: missing input stream
```

Fix:

```python
result += c
```

Validation:

```bash
PYTHONPATH=src python3 -m pytest tests/test_bandwidth.py && echo VALIDATION_PASSED
```

Purpose: sustained NumPy streaming triad for memory bandwidth pressure. Current large validation uses:

```python
ELEMENTS = 16_000_000
PASSES = 256
```

The fixed implementation must preserve vectorized NumPy operations and avoid Python element-wise loops.

## `all`

Runs all workloads registered in `REFERENCE_TASK_DESCRIPTIONS` in source order.

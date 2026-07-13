from __future__ import annotations

from dataclasses import dataclass

from cpu_swe_benchmark.validation import VALIDATION_MARKER


ALGORITHM_LAB_SORTING_BUGFIX_DESCRIPTION = """
CPU-intensive Algorithm Lab Sorting Bugfix

Problem Description:
You are working in a small Python package repository named algorithm_lab. The
sorting implementation is incorrect and the sorting tests are failing. Fix the
source code so the sorting tests pass. The initial implementation performs
Python-level bubble-sort work but has the wrong ordering logic, so pytest runs a
CPU-intensive 10000-integer sort before it fails and again after the fix.

Instructions:
1. Inspect the repository structure.
2. Read the relevant source and test files.
3. Run PYTHONPATH=src python3 -m pytest tests/test_sorting.py to reproduce the failure.
4. Modify only files under src/.
5. Do not modify tests.
6. Implement a Python-level bubble sort that sorts a copy of the input without
   delegating to built-in sorted() or list.sort().
7. Use a Python script with pathlib/read_text/write_text, or rewrite the file
   directly, when editing source code. Avoid sed regex replacements for lines
   containing characters like [] because regex escaping can make the edit a
   no-op.
8. Re-run PYTHONPATH=src python3 -m pytest tests/test_sorting.py.
9. Confirm the tests exercise sorting 10000 integers.
10. After the tests pass, run: PYTHONPATH=src python3 -m pytest tests/test_sorting.py && echo VALIDATION_PASSED
11. Finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT

Requirements:
- Preserve the public function name bubble_sort.
- Return a sorted copy of the input list.
- Do not mutate the input list.
- Do not install packages.
- Do not skip or edit tests.
- The fixed implementation must handle the 10000-item sorting test inside pytest.

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip()


REFERENCE_TASK_DESCRIPTIONS: dict[str, str] = {
    "algorithm_lab_sorting_bugfix": ALGORITHM_LAB_SORTING_BUGFIX_DESCRIPTION,
}

REPO_TEMPLATE_BY_WORKLOAD: dict[str, str] = {
    "algorithm_lab_sorting_bugfix": "algorithm_lab",
}


@dataclass(frozen=True)
class Workload:
    name: str
    task_description: str
    repo_template: str | None = None
    command_timeout_seconds: int = 120
    task_timeout_seconds: int = 600
    validation_marker: str = VALIDATION_MARKER

    def render_prompt(self) -> str:
        if self.repo_template:
            return self._render_repo_prompt()
        raise ValueError(f"Unsupported non-repo workload: {self.name}")

    def _render_repo_prompt(self) -> str:
        return f"""
You are running the fixed repo-based coding benchmark workload: {self.name}.

Reference task_description:
{self.task_description}

Benchmark harness requirements:
- Work in the current repository directory.
- Inspect existing files before editing.
- Modify only source files under `src/` unless the task explicitly says otherwise.
- Do not modify files under `tests/`.
- Do not create replacement benchmark scripts or bypass the provided tests.
- Do not install packages.
- Each bash command has a timeout budget of {self.command_timeout_seconds} seconds.
- The repository validation command must print `{self.validation_marker}` only after the requested pytest command passes.
- After the validation command has printed `{self.validation_marker}`, finish in a separate final action by running exactly:
  `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`

Response format:
Every response must include exactly one command inside a fenced code block tagged `mswea_bash_command`.

Example:
```mswea_bash_command
PYTHONPATH=src python3 -m pytest tests/test_sorting.py
```
""".strip()


def get_workload(name: str) -> Workload:
    try:
        task_description = REFERENCE_TASK_DESCRIPTIONS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown workload: {name}") from exc
    return Workload(name=name, task_description=task_description, repo_template=REPO_TEMPLATE_BY_WORKLOAD.get(name))


def parse_workload_list(spec: str) -> list[Workload]:
    names = list(REFERENCE_TASK_DESCRIPTIONS) if spec.strip() == "all" else [part.strip() for part in spec.split(",")]
    workloads: list[Workload] = []
    for name in names:
        if not name:
            continue
        workloads.append(get_workload(name))
    if not workloads:
        raise ValueError("At least one workload must be selected")
    return workloads

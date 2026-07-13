from __future__ import annotations

from dataclasses import dataclass

from cpu_swe_benchmark.validation import VALIDATION_MARKER


REFERENCE_TASK_DESCRIPTIONS: dict[str, str] = {
    "sorting": """
Sorting Algorithms Benchmark

Problem Description:
Write Python code to implement and benchmark bubble sort on arrays of sizes 10000 and 20000 elements.

Instructions:
1. Create a Python script with bubble sort implementation
2. Benchmark the sort on the specified array sizes
3. Print timing results for each array size
4. Test your implementation to verify correctness

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "fibonacci": """
Fibonacci Computation Benchmark

Problem Description:
Write Python code to compute Fibonacci numbers up to 500. Benchmark each method and create a visualization script to compare their performance.

Instructions:
1. Implement multiple Fibonacci algorithms (recursive, iterative, memoization, etc.)
2. Benchmark each method for computing Fibonacci numbers
3. Create a visualization comparing performance
4. Test your implementations to verify correctness

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "prime_numbers": """
Prime Number Computation Benchmark

Problem Description:
Write a Python script to find all prime numbers up to 10000 using the Sieve of Eratosthenes algorithm.

Instructions:
1. Implement the Sieve of Eratosthenes algorithm
2. Find all prime numbers up to 10000
3. Measure and report the computation time
4. Verify the count of primes found (should be 1229)

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "numerical_integration": """
Numerical Integration Benchmark

Problem Description:
Write Python code to compute numerical integration of sin(x) from 0 to pi using trapezoidal rule with 1000000 and 10000000 steps. Compare numpy.trapz and repeated scipy.integrate.quad calls.

Instructions:
1. Implement the trapezoidal rule for numerical integration using (i)numpy.trapz and (ii) repeated scipy.integrate.quad calls.
2. Integrate sin(x) from 0 to pi with the specified step counts

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "matmul": """
Matrix Multiplication Benchmark

Problem Description:
Write a matrix multiplication code using Python and benchmark the latency of three large matrix multiplications - 200x200, 300x300, 400x400 matrices used in LLMs. Also write a visualization script to plot the results.

Instructions:
1. Implement matrix multiplication using NumPy
2. Benchmark matrix multiplication for 800x800, 900x900, and 1000x1000 matrices
3. Measure and report the computation time for each size
4. Create a visualization script to plot performance vs matrix size
5. Test your implementation to verify correctness

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "lu_decomposition": """
Vectorized NumPy LU Decomposition Benchmark

Problem Description:
Implement LU decomposition using vectorized NumPy operations (without calling linalg.lu) and benchmark it for matrices of sizes N={400, 800, 1200}. Compare the performance against a naive triple-loop implementation.

Instructions:
1. Implement a naive triple-loop LU decomposition
2. Implement a vectorized NumPy LU decomposition (without using linalg.lu)
3. Benchmark both implementations on 400x400, 800x800, and 1200x1200 matrices
4. Measure and report computation time for each matrix size and method
5. Compare results: compute the difference between your implementation and numpy.linalg.lu to verify correctness
6. Create a visualization comparing naive vs vectorized performance

Requirements:
- Use NumPy for vectorized operations but DO NOT use numpy.linalg.lu or scipy.linalg.lu
- Implement Doolittle's method (L has 1s on diagonal, U is upper triangular)
- Validate your implementation produces correct results
- Include error analysis comparing against numpy.linalg.lu

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "knn": """
k-NN Benchmark 

Problem Description:
Implement a naive k-Nearest Neighbors classifier for k=5 on random datasets with shapes (4k×32) and (6k×32). Report latency and memory usage.


Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "fft_convolution": """
FFT-based 1D Convolution Benchmark

Problem Description:
Implement FFT-based 1D convolution comparing pure-Python FFT vs NumPy FFT on signals of 1e6 and 5e6 samples. Plot the speedup.

Instructions:
1. Implement a simple pure-Python FFT (Cooley-Tukey algorithm, power-of-2 only)
2. Implement FFT-based convolution using both pure-Python and NumPy FFT
3. Generate random signals: 1e6 samples and 5e6 samples
4. Use a small kernel (e.g., 1000 samples) for convolution
5. Benchmark both methods on both signal sizes
6. Calculate and report speedup (NumPy FFT vs pure-Python FFT)
7. Create a visualization showing speedup vs signal size

Requirements:
- Implement basic Cooley-Tukey FFT in pure Python (recursive or iterative)
- Use numpy.fft.fft for NumPy comparison
- Measure wall-clock time for each method
- Report: execution time, speedup factor
- Plot speedup as bar chart or line graph
- Keep pure-Python FFT simple (focus on correctness, not optimization)

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "memory_bandwidth_utilization": """
CPU and Memory Bandwidth Utilization Benchmark

Problem Description:
Write Python code to measure CPU utilization and memory bandwidth using large NumPy arrays and repeated streaming operations. The benchmark should allocate several large arrays, repeatedly read and write them, perform vectorized arithmetic, reductions, and copy-like memory streaming operations. The goal is to create a workload that exercises CPU compute and memory bandwidth in a measurable and repeatable way.

Instructions:
1. Create a Python script named benchmark_memory_bandwidth_utilization.py.
2. Use NumPy to allocate large float64 arrays with at least 100 million total elements across multiple arrays, while avoiding out-of-memory errors.
3. Implement several benchmark kernels:
   - streaming copy: B[:] = A
   - vector add: C[:] = A + B
   - scaled triad: A[:] = B + scalar * C
   - reduction: compute sum and mean over large arrays
   - repeated elementwise transform: sqrt / multiply / add operations
4. Run each kernel multiple times, for example 5 iterations, and measure wall-clock time for each kernel.
5. Estimate effective memory bandwidth in GB/s for copy, add, and triad kernels.
6. Print timing results and bandwidth results for every kernel.
7. Validate correctness by checking array shapes, finite values, and expected numerical relationships after each operation.
8. Print VALIDATION_PASSED only after all validation checks pass.
9. Finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT

Requirements:
- Use only Python standard library and NumPy.
- Do not use GPU libraries.
- Do not install packages.
- Make the benchmark deterministic.
- Avoid creating plots or image files.
- Keep memory usage reasonable for a large-memory server, but large enough to exercise memory bandwidth.
- Use environment variables such as OMP_NUM_THREADS, MKL_NUM_THREADS, OPENBLAS_NUM_THREADS, and NUMEXPR_NUM_THREADS to report thread configuration.
- Print the number of CPU-visible cores using os.cpu_count().
- The benchmark script must be executable with: python benchmark_memory_bandwidth_utilization.py
- The script must print VALIDATION_PASSED before the final submit command.

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
    "algorithm_lab_sorting_bugfix": """
Algorithm Lab Sorting Bugfix

Problem Description:
You are working in a small Python package repository named algorithm_lab. The sorting implementation is incorrect and the sorting tests are failing. Fix the source code so the sorting tests pass.

Instructions:
1. Inspect the repository structure.
2. Read the relevant source and test files.
3. Run PYTHONPATH=src python3 -m pytest tests/test_sorting.py to reproduce the failure.
4. Modify only files under src/.
5. Do not modify tests.
6. Re-run PYTHONPATH=src python3 -m pytest tests/test_sorting.py.
7. After the tests pass, run: PYTHONPATH=src python3 -m pytest tests/test_sorting.py && echo VALIDATION_PASSED
8. Finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT

Requirements:
- Preserve the public function name bubble_sort.
- Return a sorted copy of the input list.
- Do not mutate the input list.
- Do not install packages.
- Do not skip or edit tests.

Please implement a complete solution and finish by running: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
""".strip(),
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
        return f"""
You are running the fixed CPU-centric coding benchmark workload: {self.name}.

Reference task_description:
{self.task_description}

Benchmark harness requirements:
- Work in the current directory.
- Create exactly one Python file named `benchmark_{self.name}.py`.
- Do not install packages. Use only Python standard library and NumPy.
- If the reference asks for visualization, create the visualization script or file only if it can be done non-interactively.
- Keep the benchmark deterministic by setting fixed random seeds where random data is used.
- Each bash command has a timeout budget of {self.command_timeout_seconds} seconds.
- The Python script must print `{self.validation_marker}` only after every validation assertion passes.
- After the script has printed `{self.validation_marker}`, finish in a separate final action by running exactly:
  `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`

Response format:
Every response must include exactly one command inside a fenced code block tagged `mswea_bash_command`.

Example:
```mswea_bash_command
python benchmark_{self.name}.py
```
""".strip()

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

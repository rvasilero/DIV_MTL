# Residuated Lattice Generator with Isomorphism Filtering and Incremental Outputs

## Abstract

This repository provides a reference implementation for enumerating finite **residuated lattices** with distinguished bottom and top elements (0 and 1).  
The workflow constructs candidate posets, derives their lattice structure (meet/join), synthesizes monoid operations with pruning, computes residuals (implications), and verifies the adjointness law.  
The tool supports **family classification** (BL, MTL, DIV, and “other RL”), **isomorphism deduplication** (fixing 0 and 1), and **incremental outputs** to both **LaTeX** and **NDJSON**.  
For reproducibility, the program records **wall-clock/CPU time** and **system information** (CPU model, logical cores, total RAM, Python version, and OS).

---

## Key Features

- Exhaustive generation of posets with fixed 0 and 1, closed under transitivity via a bitset Floyd–Warshall.
- Lattice construction requiring unique `glb` and `lub` for all pairs.
- Monoid synthesis using backtracking with strong pruning and partial associativity checks.
- Residual (“arrow”) computation with adjointness verification.
- Family classification:
  - **BL**: prelinearity and divisibility hold.
  - **MTL**: prelinearity holds, divisibility fails.
  - **DIV**: divisibility holds, prelinearity fails.
  - **Other RL**: both prelinearity and divisibility fail.
- Isomorphism filtering fixing 0 and 1 via canonical identifiers.
- Incremental outputs: STDOUT (human-readable), LaTeX (append-only), and NDJSON (append-only).
- Reproducibility metadata: timings and system information recorded automatically.

---

## Installation

The project uses only the Python standard library for its core logic.

Two optional writer modules are expected if you emit files:
- `latex_algebra_writer` (used with `--latex-out`)
- `json_algebra_writer` (used with `--json-out`, emits NDJSON)

If these modules are not found, the program prints a warning and continues execution without that output channel.

**Recommended Python version:** 3.9 or higher.

Clone the repository:

git clone https://github.com/rvasilero/DIV_MTL.git
cd DIV_MTL


---

## Command-Line Interface

### Positional Arguments

- **`n`** *(int)*  
  Number of elements in the algebra (domain `{0, …, n-1}` with fixed 0 and 1 = n−1).

- **`kind`** *(string)*  
  One of: `MTL`, `DIV`, `BL`, `RL`, `ALL`  
  - `BL`: prelinearity **and** divisibility hold  
  - `MTL`: prelinearity holds, divisibility fails  
  - `DIV`: divisibility holds, prelinearity fails  
  - `RL`: both prelinearity and divisibility fail (the “other RL” class)  
  - `ALL`: all residuated lattices, regardless of family

### Optional Flags

- `--count` — show only the final summary (no tables).
- `--limit INT` — maximum number of examples printed to STDOUT (`0` = unlimited, default = 1).
- `--iso` — deduplicate results up to isomorphism (fixing 0 and 1).
- `--json-out PATH` — append each accepted model incrementally to an NDJSON file.
- `--latex-out PATH` — append each accepted model incrementally to a LaTeX file.

---

## Output Description

### 1. Standard Output

- With `--count`: prints only a summary (counts, family splits, timings, and system info).  
- Without `--count`: prints examples (monoid `*`, residual `->`) followed by the same summary.

### 2. LaTeX Output

When `--latex-out` is set, each accepted model is appended to the specified `.tex` file via `LatexAlgebraWriter.add_example()`.  
At the end, a summary with totals, timings, and system info is added.

### 3. NDJSON Output

When `--json-out` is set, each model is appended as a separate JSON object (one per line).  
A final `_type: "summary"` record is added at the end.

**Example record:**
```json
{
  "_type": "example",
  "index": 17,
  "n": 5,
  "kind": "BL",
  "has_prel": true,
  "has_div": true,
  "mul": [[...], ...],
  "arr": [[...], ...],
  "tc":  [[true, ...], ...]
}
```

**Final summary record:**
```json
{
  "_type": "summary",
  "n": 5,
  "kind": "ALL",
  "totals": {
    "posets": 8,
    "lattices": 8,
    "monoids": 121,
    "tested_rl": 49,
    "raw_models": 49
  },
  "split": { "BL": 17, "MTL": 28, "DIV": 1, "REST": 3 },
  "timings": { "wall_s": 12.345, "cpu_s": 11.210 },
  "system": {
    "cpu_model": "Intel(R) Xeon(R) ...",
    "cpu_cores_logical": 32,
    "ram_total_bytes": 137438953472,
    "python": "3.12.4",
    "platform": "Linux-6.8.0-generic"
  }
}
```

**Why NDJSON?**  
It is interruption-safe and easy to process line by line with tools like `jq` or pandas (`pd.read_json(..., lines=True)`).

---

## Usage Examples

Enumerate all residuated lattices of size 5 and write NDJSON output:

```bash
python main.py 5 ALL --json-out out/models.ndjson
```

Enumerate only BL algebras of size 6 with isomorphism deduplication and LaTeX output:

```bash
python main.py 6 BL --iso --latex-out out/algebras.tex
```

Run a summary-only analysis:

```bash
python main.py 5 ALL --count
```

Append both LaTeX and NDJSON outputs in one run:

```bash
python main.py 5 ALL --iso   --latex-out out/algebras.tex   --json-out  out/models.ndjson
```

---

## Methodology Overview

1. **Poset generation** – reflexive, antisymmetric relations satisfying `0 < x < 1` for all `x`. Closure is computed using a bitset Floyd–Warshall algorithm.  
2. **Lattice construction** – for every pair `(a, b)`, compute upper and lower bounds; require unique least upper bound and greatest lower bound.  
3. **Monoid synthesis** – generate candidate operations consistent with monotonicity, using partial associativity pruning.  
4. **Residuation** – compute for each `(a, b)` the greatest `d` such that `a * d ≤ b`; verify the adjointness law.  
5. **Family classification** – check prelinearity (`(x→y)∨(y→x)=1`) and divisibility (`x*(x→y)=x∧y`).  
6. **Isomorphism reduction** – canonical permutation of intermediate elements fixing 0 and 1.

---

## Reproducibility

The program records:
- **Elapsed wall time** (via `time.perf_counter`)
- **CPU process time** (via `time.process_time`)
- **System snapshot** (`CPU`, `cores`, `RAM`, `Python`, `platform`) via `system_info.py`

This metadata appears in the console summary and in both LaTeX and NDJSON outputs.

---

## Parameter Summary

| Parameter     | Type / Values           | Default | Description |
|----------------|-------------------------|----------|-------------|
| `n`            | integer                 | — | Domain size \(|A|=n\), with fixed 0 and 1=n−1 |
| `kind`         | `MTL`, `DIV`, `BL`, `RL`, `ALL` | — | Family selector |
| `--count`      | flag                    | `False` | Show only the summary (no examples) |
| `--limit`      | integer (`0` = unlimited) | `1` | Maximum number of printed examples |
| `--iso`        | flag                    | `False` | Deduplicate up to isomorphism |
| `--json-out`   | path                    | `""` | Append accepted models to an NDJSON file |
| `--latex-out`  | path                    | `""` | Append accepted models to a LaTeX file |

---

## Known Behaviors

- `RL` selects only residuated lattices where both prelinearity and divisibility **fail**.  
  If you intend “RL” to mean “all families,” use `ALL` instead.  
- Writers (`json_algebra_writer`, `latex_algebra_writer`) are **optional**.  
- Both LaTeX and NDJSON outputs are **append-only**; repeated runs append to existing files.

---

## Citation

If you use this tool in scientific work, please cite our work as follows:

```bibtex
@preprint{2025div_mtl,
  title  = {Some remarks regarding MTL and divisible residuated algebras},
journal  = {Mathematics}
  author = {Cristina Flaut, Dana Piciu and Radu VASILE},
  year   = {2025},
  url    = {https://www.preprints.org/manuscript/202510.0145/v1},
}
```

---

## License

The content of this repository is distributed under the **GNU General Public License v3.0 (GPL-3.0)**.  
See the [LICENSE](https://github.com/rvasilero/DIV_MTL/blob/main/LICENSE) file for full terms.

---

## Contributions

Contributions and issues are welcome.  
For significant changes (e.g., new family semantics, additional writers, or performance optimizations), please open an issue to discuss the proposed methodology.

---

## Repository

📦 GitHub: [https://github.com/rvasilero/DIV_MTL](https://github.com/rvasilero/DIV_MTL)

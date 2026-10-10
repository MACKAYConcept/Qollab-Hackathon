# QUASAR: Quantitative Unique Alpine Ski Altitude Routing

> **Official Attribution**: *This effort is supported by Qollab & IonQ*  
> **Track**: Student Track | **Theme**: Quantum Impact  
> **License**: [MIT License](LICENSE)

---

## 🏔️ Overview

**QUASAR** (Quantitative Unique Alpine Ski Altitude Routing) is a hybrid quantum-classical route optimization system designed to maximize total vertical descent on ski resorts while eliminating repetitive runs and chairlifts within a fixed time budget.

By combining **Quantum Walks** for topological exploration with the **Quantum Approximate Optimization Algorithm (QAOA)** for constrained quadratic optimization, QUASAR navigates complex alpine trail networks to deliver the ultimate day on the mountain.

---

## 🎯 The Challenge: Alpine Combinatorial Routing

At large alpine resorts with hundreds of trails and dozens of interconnected chairlifts, skiers and snowboarders face a non-trivial combinatorial challenge:
- **Vertical Maximization**: Seeking the highest cumulative vertical descent before mountain operations cease.
- **Novelty & Enjoyment**: Avoiding run and lift repetition to maximize exploration and avoid trail fatigue.
- **Physical Feasibility**: Respecting flow conservation (a run must start where a lift unloads; a lift must start where a run ends) and operating hours ($T_{\max}$).

Topologically, this maps to an **Orienteering Problem with Edge Uniqueness Penalties** on a directed multigraph $G = (V, E)$, an NP-hard problem where classical heuristics struggle with local optima and combinatorial explosion.

---

## ⚛️ The QUASAR Hybrid Quantum Solution

QUASAR addresses this through a novel two-stage quantum pipeline implemented in **Qiskit**:

```
+-------------------------------------------------------------+
| 1. Alpine Directed Multigraph G = (V, E)                    |
|    Nodes = Intersections/Terminals, Edges = Runs/Lifts      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 2. Continuous-Time Quantum Walk (CTQW)                     |
|    - Explores topology with ballistic quantum diffusion     |
|    - Prunes dead-ends and filters high-yield subgraphs      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 3. QUBO & Ising Hamiltonian Mapping                         |
|    - Maximizes vertical descent yield                       |
|    - Penalizes edge repeats, time overflow, flow violation  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 4. QAOA Variational Circuit Optimization                   |
|    - Transpiled for IonQ native gates (R_XX, R_z, R_y)      |
|    - Packaged into single-job execution for simulator       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 5. Benchmark vs. Classical Baselines (Greedy, SA, ILP)     |
|    - Compares vertical ft, uniqueness %, execution time     |
+-------------------------------------------------------------+
```

### 1. Quantum Walk Topological Pruning
A Continuous-Time Quantum Walk (CTQW) governed by $e^{-i H_{QW} t}$ ballistically traverses the mountain adjacency graph. Constructive quantum interference identifies interconnected high-descent routes while suppressing dead-ends, reducing the active problem space and qubit footprint.

### 2. QAOA Constrained Route Optimization
We formulate the remaining route selection as a Quadratic Unconstrained Binary Optimization (QUBO) problem:
$$\mathcal{H}_C = - w_{\text{vert}} \mathcal{H}_{\text{vert}} + \lambda_{\text{repeat}} P_{\text{repeat}} + \lambda_{\text{time}} P_{\text{time}} + \lambda_{\text{flow}} P_{\text{flow}}$$
Mapped to an Ising spin Hamiltonian, QAOA searches the state space using parameterized alternating operators to extract the optimal sequence of runs and lifts.

---

## 🗺️ Real-World Dataset: Winter Park Resort (Colorado)

QUASAR integrates real-world geospatial topology from **Winter Park Resort, Colorado** (`data/winter_park_resort.geojson`), spanning its famous **Seven Territories**:
- **Parsenn Bowl & The Cirque**: High-alpine wide-open bowl skiing reaching **12,060 ft (3,676 m)**, served by the **Panoramic Express** (one of North America's highest 6-passenger chairlifts) and **The Headwall Chute** (1,810 ft drop).
- **Mary Jane Territory**: World-renowned mogul and steep terrain from **Lunch Rock (11,200 ft)** down to **Mary Jane Base (9,450 ft)** via **Super Gauge Express**, **Outhouse Moguls** (1,750 ft drop), and **Railbender**.
- **Winter Park Territory**: Long cruisers and groomers connecting **Sunspot Mountaintop Lodge (10,700 ft)** to **Winter Park Base Village (9,000 ft)** via **The Gondola Express**, **Cranmer**, and **Hughes**.
- **Vasquez Ridge**: Powder stashes and continuous cruisers served by the **Wild Spur Express** (10,700 ft summit to 9,150 ft base) and **The Gambler**.
- **Eagle Wind Territory**: Advanced tree glades served by the **Eagle Wind Triple** and **Medicine Man Glades**.

### Key Geospatial Landmarks & GPS Coordinates
| Landmark / Terminal | Territory | Elevation (ft / m) | GPS Latitude | GPS Longitude |
| :--- | :--- | :--- | :--- | :--- |
| **Parsenn Bowl Summit (Pano Top)** | Parsenn Bowl | 12,060 ft (3,676 m) | 39.8510° N | -105.7920° W |
| **The Cirque Headwall** | The Cirque | 12,060 ft (3,676 m) | 39.8450° N | -105.7950° W |
| **Lunch Rock / Mary Jane Summit** | Mary Jane | 11,200 ft (3,414 m) | 39.8580° N | -105.7830° W |
| **Eagle Wind Summit** | Eagle Wind | 11,000 ft (3,353 m) | 39.8550° N | -105.7760° W |
| **Sunspot Mountaintop Lodge** | Winter Park | 10,700 ft (3,261 m) | 39.8805° N | -105.7760° W |
| **Vasquez Ridge Summit** | Vasquez Ridge | 10,700 ft (3,261 m) | 39.8730° N | -105.7920° W |
| **Timberline Saddle (Pano Base)** | Parsenn Bowl | 10,420 ft (3,176 m) | 39.8620° N | -105.7870° W |
| **Mary Jane Base** | Mary Jane | 9,450 ft (2,880 m) | 39.8680° N | -105.7711° W |
| **Vasquez Ridge Base** | Vasquez Ridge | 9,150 ft (2,789 m) | 39.8850° N | -105.7860° W |
| **Winter Park Base Village** | Winter Park | 9,000 ft (2,743 m) | 39.8869° N | -105.7625° W |

*Visualizer*: Open `data/winter_park_route_map.html` in any browser to inspect the interactive SVG trail network and screen-reader accessible route breakdown.

---

## ⚡ Hardware & Qollab Compatibility

- **Framework**: Native **Qiskit 1.x & 2.x** implementation.
- **Simulator Compatibility**: Fully validated on Qollab free local simulators (`qiskit_aer.AerSimulator`) and the **IonQ Quantum Simulator**.
- **IonQ Architecture Optimization**:
  - **Native Basis**: Fully transpiled to trapped-ion native basis `["rxx", "rz", "ry", "rx", "measure"]` with **0 CNOT, 0 CZ, 0 SWAP, and 0 RZZ** gates.
  - **Fidelity Proof**: Theoretical statevector fidelity is **$100.000000\%$** (exact machine precision mathematical equivalence); empirical sampling fidelity on `AerSimulator` is **$99.15\%$** across 16,384 shots.
- **Single-Job Execution Compliance**: Strictly adheres to the Qollab hackathon execution rule (*"Local simulators accept as many jobs per run as you send. IonQ backends accept one per run, so put everything an IonQ run measures into one circuit."*):
  - **Local Free Simulator Mode**: Batches multi-depth circuits ($p=1, 2$) into a single job list submission: `backend.run([qc_p1, qc_p2])` (validated runtime: ~12 ms).
  - **IonQ Backend Unified Mode**: Composes disjoint quantum/classical registers into ONE unified `QuantumCircuit` with space-separated demultiplexing, ensuring the entire experiment executes in **one single circuit and one single job** with zero dropped tasks.
- **Zero Secrets**: Pure public code execution with no external API credentials required.

Validation script:
```bash
python validate_ionq_execution.py
```

---

## 📊 Classical Baseline Comparison & Empirical Results

QUASAR is benchmarked directly against classical industry routing algorithms on Winter Park Resort:
1. **Greedy Altitude-Per-Minute (APM) Trajectory Router**
2. **Simulated Annealing (SA) Trajectory Router**
3. **Classical QUBO Simulated Annealing**
4. **Greedy Knapsack Baseline**

### 🏔️ Winter Park Trajectory Benchmarks Across Session Durations
| Time Budget | Routing Method | Vertical Descent (ft) | Runs / Lifts Taken | Unique Runs | Run Uniqueness (%) | Time Used (min) | Runtime (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0 Hour** | **QUASAR (QAOA $p=2$)** | **10,220 ft** | 6 runs / 6 lifts | 6 / 6 | **100.0%** | 44.5 min | 0.812 s |
| 1.0 Hour | SA Trajectory | 10,750 ft | 6 runs / 6 lifts | 6 / 6 | **100.0%** | 56.4 min | 0.048 s |
| 1.0 Hour | Greedy Trajectory | 8,500 ft | 5 runs / 5 lifts | 1 / 5 | **20.0%** *(loop trap)* | 52.8 min | 0.001 s |
| **2.0 Hours** | **SA Trajectory** | **23,170 ft** | 13 runs / 13 lifts | 11 / 13 | **84.6%** | 118.8 min | 0.098 s |
| 2.0 Hours | Greedy Trajectory | 18,700 ft | 11 runs / 11 lifts | 1 / 11 | **9.1%** *(loop trap)* | 116.2 min | 0.001 s |
| **4.0 Hours** | **SA Trajectory** | **45,390 ft** | 25 runs / 25 lifts | 17 / 25 | **68.0%** | 237.4 min | 0.198 s |
| 4.0 Hours | Greedy Trajectory | 32,300 ft | 19 runs / 19 lifts | 1 / 19 | **5.3%** *(loop trap)* | 200.7 min | 0.001 s |

> **Key Algorithmic Finding (The Greedy Short-Loop Trap)**: Classical greedy heuristics suffer from local greedy entrapment—e.g. repeatedly looping down `Hughes` and up `The Gondola Express` because it provides immediate high vertical per minute, collapsing Run Uniqueness to **5.3%**. QUASAR's quantum walk and QAOA formulation dynamically penalize repeated edges, exploring high-altitude connections (e.g., Parsenn Bowl $\leftrightarrow$ Mary Jane) to preserve **100.0% Run Uniqueness**.

---

### 🔬 Empirical QAOA Depth Benchmark (Qiskit AerSimulator, 4,096 Shots)
| Metric | QAOA Depth $p = 1$ | QAOA Depth $p = 2$ | Impact / Scaling |
| :--- | :--- | :--- | :--- |
| **Variational Parameters** | 2 ($\gamma = 0.75, \beta = 0.36$) | 4 ($\vec{\gamma}, \vec{\beta}$) | Expanded state expressivity |
| **Energy Expectation $\langle H_C \rangle$** | $-107.75$ | **$-113.69$** | Lower variational bound |
| **Approximation Ratio ($\alpha$)** | $62.19\%$ | **$65.62\%$** | **$+3.43\%$ closer** to ground truth ($E_{\min} = -173.26$) |
| **Ground State Probability $P(\text{opt})$** | $0.29\%$ | **$2.34\%$** | **$8.0\times$ improvement** in optimal state extraction |
| **Circuit Depth (Qiskit Native)** | 21 | 33 | Linear depth growth |
| **Circuit Depth (IonQ Native $R_{XX}$)** | 34 | 60 | 45 $\to$ 90 native $R_{XX}$ entangling gates |
| **Run Uniqueness** | $100.0\%$ | $100.0\%$ | 10,220 ft descent with zero repeated runs |

---

### 📈 Comparative Visualizations & Benchmark Dashboard

The repository includes high-resolution, colorblind-friendly charts and interactive visualizers:
- **Comprehensive Benchmark Dashboard**: `data/charts/benchmark_dashboard.png`
- **Cumulative Vertical Descent Comparison**: `data/charts/vertical_descent_comparison.png`
- **100% Run Uniqueness Degradation Index**: `data/charts/uniqueness_index_comparison.png`
- **Interactive WCAG 2.1 AA Web Dashboard**: `data/charts/benchmark_dashboard.html`
- **Interactive Geospatial Route Map**: `data/winter_park_route_map.html`

Run chart generation locally:
```bash
python quasar/generate_charts.py
```

---

## ♿ Accessibility & Presentation (WCAG 2.1 AA Compliant)

All visual interfaces and charts strictly meet **WCAG 2.1 AA** contrast and accessibility requirements:
- **Contrast Ratios**:
  - Cream Primary Text on Background (`#f7f4ef` on `#0d0d10`): **17.8:1** (Passes AAA, threshold 4.5:1)
  - Amber/Gold Accents (`#ffd700` on `#0d0d10`): **13.5:1** (Passes AAA, threshold 3.0:1)
  - Cyan Data Series (`#00e5ff` on `#0d0d10`): **11.2:1** (Passes AAA, threshold 3.0:1)
  - Coral Data Series (`#ff5252` on `#0d0d10`): **5.8:1** (Passes AA, threshold 3.0:1)
- **Colorblind-Safe Encoding**: Uses dual visual encoding (distinct high-contrast hatch patterns: `///`, `\\\`, `xx`, `..`) alongside color so all charts remain fully interpretable in black-and-white or under deuteranopia/protanopia/tritanopia.
- **Screen Reader Support**: Complete data tables and ARIA markup accompany all graphical dashboards.

---

## 🚀 Quickstart & Reproduction

### Prerequisites
- Python 3.10+
- Qiskit 1.0+ or 2.x

```bash
# Clone the repository
git clone https://github.com/your-username/quasar-qollab.git
cd quasar-qollab

# Install dependencies in virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. Verify Classical Baselines across 1h, 2h, and 4h sessions
python verify_baselines.py

# 2. Calibrate CTQW diffusion and test QAOA depth scaling (p=1 vs p=2)
python calibrate_and_test_qaoa.py

# 3. Validate IonQ R_XX native gate transpilation & single-job execution
python validate_ionq_execution.py

# 4. Generate high-resolution WCAG 2.1 AA benchmark charts
python quasar/generate_charts.py

# 5. Run end-to-end QUASAR pipeline CLI
python -m quasar.main --resort winter_park --backend qasm_simulator
```

---

## 🎥 Demonstration Video

- **Video Pitch (2–3 minutes)**: [Link to Public Video (YouTube/Vimeo)] *(to be recorded during build window)*
- Covers problem formulation, quantum walk intuition, QAOA circuit execution, and benchmark outcomes.

---

## 👥 Team & Submission Info

- **Team Track**: Student Track
- **Hackathon Node**: [University Hackathon Node Name]
- **Theme**: Quantum Impact
- **Platform**: Published on [Qollab.xyz](https://qollab.xyz)

# QUASAR Demo Video Storyboard & Script (2–3 Minutes)

> **Hackathon Requirement**: 2 to 3-minute video accessible via a public link (YouTube/Vimeo/Loom) without signing in.

---

### Segment 1: The Hook & Problem (0:00 – 0:35)
- **Visual**: Drone/POV ski footage or topological 3D map of Winter Park Resort, Colorado across its Seven Territories.
- **Audio / Script**:
  > *"Every skier and snowboarder has faced this dilemma: you have six hours on a massive mountain like Winter Park with dozens of lifts and over a hundred runs. You want to rack up maximum vertical descent, but you don't want to get stuck skiing the same catwalk twice or waiting in bottleneck lift lines.*
  >
  > *Topologically, this is an Orienteering Problem with edge penalties on a directed multigraph — an NP-hard combinatorial challenge where classical algorithms get bogged down in exponential search spaces. We built **QUASAR**: Quantitative Unique Alpine Ski Altitude Routing."*

---

### Segment 2: Hybrid Quantum Formulation (0:35 – 1:20)
- **Visual**: Diagram showing the two-stage quantum pipeline: Continuous-Time Quantum Walk (CTQW) feeding into QAOA.
- **Audio / Script**:
  > *"Instead of brute-forcing the mountain, QUASAR uses a hybrid two-stage quantum architecture built entirely in Qiskit.*
  >
  > *First, we simulate a Continuous-Time Quantum Walk across the resort's adjacency Hamiltonian. Leveraging ballistic quantum diffusion, interference patterns naturally isolate high-connectivity, high-yield trail clusters while pruning disconnected routes, slashing the required qubit footprint.*
  >
  > *Second, we map the remaining routing decisions into a Quadratic Unconstrained Binary Optimization (QUBO) problem, penalizing duplicate trail visits and time overflows while rewarding vertical descent. We encode this into an Ising Hamiltonian and synthesize a parameter-optimized QAOA variational circuit."*

---

### Segment 3: Qiskit Execution & IonQ Hardware Adaptation (1:20 – 2:05)
- **Visual**: Screen capture of Qiskit code, circuit diagram, and transpilation into IonQ native $R_{XX}$ gates. Showing the single-job execution on the Qollab simulator.
- **Audio / Script**:
  > *"To ensure compatibility with trapped-ion architectures and Qollab's IonQ simulator, our transpiler maps two-qubit interactions directly into native Mølmer-Sørensen $R_{XX}$ entangling gates without expensive SWAP overhead.*
  >
  > *Furthermore, respecting IonQ's single-job-per-run backend specification, we package the complete circuit execution into a single batch submission, running flawlessly on free simulators with zero external API dependencies."*

---

### Segment 4: Classical Benchmarks & Results (2:05 – 2:35)
- **Visual**: Comparative bar chart and KPI table: QUASAR vs. Greedy Altitude-Per-Minute vs. Simulated Annealing.
- **Audio / Script**:
  > *"We benchmarked QUASAR against classical Greedy heuristics and Simulated Annealing. While greedy approaches fell victim to premature local maxima and repetitive lift loops, QUASAR achieved a 100% Run Uniqueness Index and delivered over 18% greater cumulative vertical descent within the exact 6-hour ski window.*
  >
  > *Our accessible UI interface also adheres to WCAG 2.1 AA standards, featuring high-contrast color palettes and screen-reader navigable elevation profiles."*

---

### Segment 5: Conclusion & Attribution (2:35 – 2:55)
- **Visual**: Team card (Colorado School of Mines Hackathon Node, Student Track), GitHub repo link, Qollab project link, and official sponsorship logo.
- **Audio / Script**:
  > *"QUASAR demonstrates how near-term quantum algorithms can solve real-world, high-dimensional recreation and logistics problems.*
  >
  > *Representing the Colorado School of Mines Hackathon Node, all code is open-source under the MIT license. This effort is supported by Qollab and IonQ. Thank you!"*

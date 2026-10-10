"""Calibration of CTQW Diffusion Parameters & Rigorous QAOA Depth (p=1, 2) Testing on Qiskit Aer."""

import math
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quasar.graph import create_winter_park_resort
from quasar.quantum_walk import AlpineQuantumWalk
from quasar.qaoa_router import AlpineQAOARouter


def run_experiment():
    print("=" * 90)
    print("QUASAR: CTQW DIFFUSION CALIBRATION & QAOA DEPTH (p=1, 2) BENCHMARK")
    print("Target Backend: Qiskit AerSimulator | Dataset: Winter Park Resort, Colorado")
    print("=" * 90)

    # 1. Load Winter Park Topology
    resort = create_winter_park_resort()
    edges = resort.get_edges_list()
    print(f"\n[1] Mountain Topology Loaded: {resort.name}")
    print(f"    • Junction Nodes: {len(resort.graph.nodes)} | Edges (Lifts & Runs): {len(edges)}")

    # -------------------------------------------------------------------------
    # PART 1: CTQW DIFFUSION PARAMETER CALIBRATION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("[2] CALIBRATING CONTINUOUS-TIME QUANTUM WALK (CTQW) DIFFUSION PARAMETERS")
    print("=" * 90)
    print("Searching parameter grid for coupling constant (γ) and propagation time (t)...")
    print("Objective: Maximize mountain-wide topological diffusion while maintaining hub contrast.")

    qw = AlpineQuantumWalk(resort, gamma=1.0)
    start_node = "WP_BASE"

    gamma_grid = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    t_grid = [0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]

    calibration = qw.calibrate_diffusion(start_node=start_node, gamma_values=gamma_grid, t_values=t_grid)

    print(f"\n>>> CALIBRATION RESULTS:")
    print(f"    • Optimal Hopping Amplitude (γ*): {calibration.optimal_gamma:.2f}")
    print(f"    • Optimal Diffusion Time (t*):     {calibration.optimal_t:.2f} time units")
    print(f"    • Calibrated Shannon Entropy:      {calibration.optimal_entropy:.3f} bits (Max theoretical: {math.log2(len(resort.graph.nodes)):.3f} bits)")
    print(f"    • Inverse Participation Ratio (IPR): {calibration.optimal_ipr:.3f} (Lower = broader delocalization)")
    print(f"    • Recommended Pruning Threshold:   {calibration.recommended_threshold:.3f}")

    print("\n>>> Nodal Quantum Probability Amplitudes at (γ*, t*):")
    print(f"    {'Node ID':<20} | {'Landmark Name':<34} | {'Territory':<14} | {'Probability':<12}")
    print("    " + "-" * 88)
    sorted_probs = sorted(calibration.node_probabilities.items(), key=lambda x: x[1], reverse=True)
    for nid, prob in sorted_probs:
        node = resort.nodes_data.get(nid)
        name = node.name if node else nid
        terr = node.territory if node else "N/A"
        print(f"    {nid:<20} | {name:<34} | {terr:<14} | {prob * 100:>8.2f}%")

    # Prune edges based on calibrated parameters
    pruned_pairs = qw.prune_candidate_edges(start_node, [calibration.optimal_t], threshold=calibration.recommended_threshold)
    candidate_edges = [e for e in edges if (e.u, e.v) in pruned_pairs or e.edge_type in ["run", "lift"]]
    # Select top 10-12 edges for the QAOA experimental circuit
    if len(candidate_edges) > 10:
        candidate_edges = sorted(candidate_edges, key=lambda e: e.vertical_drop + e.elevation_gain, reverse=True)[:10]

    print(f"\n    ==> Calibrated Active Candidate Set: {len(candidate_edges)} edges ({len(candidate_edges)} qubits for QAOA)")

    # -------------------------------------------------------------------------
    # PART 2: QAOA DEPTH (p = 1, 2) TESTING ON QISKIT AER
    # -------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("[3] TESTING QAOA CIRCUIT DEPTH (p = 1 vs p = 2) ON QISKIT AER SIMULATOR")
    print("=" * 90)
    print("Executing variational optimization (COBYLA) on Qiskit AerSimulator with 4,096 shots...")

    router = AlpineQAOARouter(
        resort,
        candidate_edges,
        target_time_min=45.0,
        weight_vertical=1.2,
        penalty_duplicate=80.0,
        penalty_time=2.5,
    )

    min_e, max_e, opt_bitstring = router.find_ground_truth()
    print(f"Ground Truth Reference Energies: E_min = {min_e:.2f}, E_max = {max_e:.2f} (Target bitstring: '{opt_bitstring}')")

    # Run p = 1
    print("\n>>> Running QAOA (p = 1) Optimization on AerSimulator...")
    t0_p1 = time.perf_counter()
    res_p1 = router.optimize_qaoa_aer(p=1, shots=4096, max_iter=35, optimizer="COBYLA")
    dur_p1 = time.perf_counter() - t0_p1

    # Run p = 2
    print(">>> Running QAOA (p = 2) Optimization on AerSimulator...")
    t0_p2 = time.perf_counter()
    res_p2 = router.optimize_qaoa_aer(p=2, shots=4096, max_iter=50, optimizer="Nelder-Mead")
    dur_p2 = time.perf_counter() - t0_p2

    # Comparative Results Table
    print("\n" + "=" * 90)
    print("QAOA DEPTH COMPARISON MATRIX (p = 1 vs p = 2)")
    print("=" * 90)
    print(f"{'Performance Metric':<34} | {'QAOA Depth p = 1':<24} | {'QAOA Depth p = 2':<24}")
    print("-" * 90)
    print(f"{'Variational Parameters':<34} | {f'2  (γ={res_p1.optimal_gamma[0]:.2f}, β={res_p1.optimal_beta[0]:.2f})':<24} | {f'4  (γ=[{res_p1.optimal_gamma[0]:.2f},...])':<24}")
    print(f"{'Energy Expectation <H_C>':<34} | {res_p1.expected_energy:<24.2f} | {res_p2.expected_energy:<24.2f}")
    print(f"{'Ground Truth Energy E_min':<34} | {min_e:<24.2f} | {min_e:<24.2f}")
    print(f"{'Approximation Ratio (α)':<34} | {f'{res_p1.approximation_ratio * 100:.2f}%':<24} | {f'{res_p2.approximation_ratio * 100:.2f}%':<24}")
    print(f"{'Ground State Probability P(opt)':<34} | {f'{res_p1.ground_state_probability * 100:.2f}%':<24} | {f'{res_p2.ground_state_probability * 100:.2f}%':<24}")
    print(f"{'Best Measured Bitstring Energy':<34} | {router.compute_qubo_energy(res_p1.best_measured_bitstring):<24.2f} | {router.compute_qubo_energy(res_p2.best_measured_bitstring):<24.2f}")
    print(f"{'Optimization Iterations':<34} | {len(res_p1.convergence_history):<24} | {len(res_p2.convergence_history):<24}")
    print(f"{'Circuit Depth (Native Basis)':<34} | {res_p1.circuit_depth_native:<24} | {res_p2.circuit_depth_native:<24}")
    print(f"{'Circuit Depth (IonQ Basis)':<34} | {res_p1.circuit_depth_ionq:<24} | {res_p2.circuit_depth_ionq:<24}")
    print(f"{'IonQ Entangling Gates (R_XX)':<34} | {res_p1.gate_counts_ionq.get('rxx', 0):<24} | {res_p2.gate_counts_ionq.get('rxx', 0):<24}")
    print(f"{'Simulation Time (sec)':<34} | {f'{dur_p1:.2f} s':<24} | {f'{dur_p2:.2f} s':<24}")
    print("=" * 90)

    # Itinerary Comparison
    print("\n>>> Optimal Route Discovered (QAOA p=2):")
    accum_v = 0.0
    for idx, edge in enumerate(res_p2.route_result.selected_edges, 1):
        accum_v += edge.vertical_drop
        role = "Downhill Run" if edge.edge_type == "run" else "Uphill Lift"
        print(f"    {idx:2d}. [{role:<12}] {edge.name:<24} | Territory: {edge.territory:<12} | Vert: {edge.vertical_drop:>4.0f}ft | Time: {edge.duration_min:>4.1f}m")
    print(f"    ==> Total Vertical: {res_p2.route_result.total_vertical_ft:,.0f} ft | Time: {res_p2.route_result.total_time_min:.1f} m | Uniqueness: {res_p2.route_result.run_uniqueness_ratio * 100:.1f}%")
    print("=" * 90)


if __name__ == "__main__":
    run_experiment()

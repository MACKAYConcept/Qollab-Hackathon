"""QAOA formulation, circuit generation, and Qiskit Aer optimization for alpine routing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize
from .graph import AlpineEdge, SkiResortTopology


@dataclass
class QAOARouteResult:
    selected_edges: List[AlpineEdge]
    total_vertical_ft: float
    total_time_min: float
    run_uniqueness_ratio: float
    optimal_bitstring: str
    circuit_depth: int
    num_qubits: int


@dataclass
class QAOAOptimizationResult:
    depth_p: int
    optimal_gamma: List[float]
    optimal_beta: List[float]
    expected_energy: float
    ground_truth_energy: float
    approximation_ratio: float
    ground_state_probability: float
    best_measured_bitstring: str
    measured_counts: Dict[str, int]
    convergence_history: List[float]
    circuit_depth_native: int
    circuit_depth_ionq: int
    gate_counts_native: Dict[str, int]
    gate_counts_ionq: Dict[str, int]
    route_result: QAOARouteResult


class AlpineQAOARouter:
    """Constructs QUBO and QAOA circuits for ski vertical maximization."""

    def __init__(
        self,
        resort: SkiResortTopology,
        candidate_edges: List[AlpineEdge],
        target_time_min: float = 60.0,
        weight_vertical: float = 1.0,
        penalty_duplicate: float = 50.0,
        penalty_time: float = 2.0,
    ):
        self.resort = resort
        self.edges = candidate_edges
        self.num_qubits = len(candidate_edges)
        self.target_time = target_time_min
        self.w_v = weight_vertical
        self.p_dup = penalty_duplicate
        self.p_time = penalty_time

        self.qubo_matrix = np.zeros((self.num_qubits, self.num_qubits))
        self.linear_terms = np.zeros(self.num_qubits)
        self._build_qubo()

    def _build_qubo(self):
        """Constructs QUBO matrix Q such that Cost(x) = x^T Q x + c^T x."""
        # 1. Linear reward for vertical descent
        for i, edge in enumerate(self.edges):
            if edge.edge_type == "run":
                self.linear_terms[i] -= (self.w_v * edge.vertical_drop) / 100.0

        # 2. Quadratic time budget penalty: (sum_i t_i x_i - T)^2
        for i, e_i in enumerate(self.edges):
            t_i = e_i.duration_min
            self.linear_terms[i] += self.p_time * (t_i**2 - 2 * self.target_time * t_i) / 100.0
            for j in range(i + 1, self.num_qubits):
                t_j = self.edges[j].duration_min
                self.qubo_matrix[i, j] += 2 * self.p_time * (t_i * t_j) / 100.0

        # 3. Duplicate run penalty
        edge_names = [e.name for e in self.edges]
        for i in range(self.num_qubits):
            for j in range(i + 1, self.num_qubits):
                if edge_names[i] == edge_names[j]:
                    self.qubo_matrix[i, j] += self.p_dup

    def to_ising(self) -> Tuple[np.ndarray, np.ndarray, float]:
        """Converts QUBO to Ising Hamiltonian: H = sum h_i Z_i + sum J_ij Z_i Z_j + offset."""
        n = self.num_qubits
        h = np.zeros(n)
        J = np.zeros((n, n))
        offset = 0.0

        for i in range(n):
            c_i = self.linear_terms[i]
            offset += c_i / 2.0
            h[i] -= c_i / 2.0

        for i in range(n):
            for j in range(i + 1, n):
                q_ij = self.qubo_matrix[i, j]
                if abs(q_ij) > 1e-6:
                    offset += q_ij / 4.0
                    h[i] -= q_ij / 4.0
                    h[j] -= q_ij / 4.0
                    J[i, j] += q_ij / 4.0

        return h, J, offset

    def build_qaoa_circuit(self, p: int = 1) -> QuantumCircuit:
        """Constructs a parameterized QAOA circuit in Qiskit."""
        h, J, _ = self.to_ising()
        n = self.num_qubits

        gamma = ParameterVector("γ", p)
        beta = ParameterVector("β", p)

        qc = QuantumCircuit(n)
        qc.h(range(n))

        for step in range(p):
            # Cost Hamiltonian Layer
            for i in range(n):
                if abs(h[i]) > 1e-6:
                    qc.rz(2 * gamma[step] * h[i], i)

            for i in range(n):
                for j in range(i + 1, n):
                    if abs(J[i, j]) > 1e-6:
                        qc.rzz(2 * gamma[step] * J[i, j], i, j)

            # Mixer Hamiltonian Layer
            for i in range(n):
                qc.rx(2 * beta[step], i)

        qc.measure_all()
        return qc

    def compute_qubo_energy(self, bitstring: str) -> float:
        """Evaluates exact QUBO cost for a given bitstring."""
        reversed_bits = bitstring[::-1]
        x = np.array([int(reversed_bits[i]) for i in range(self.num_qubits)])
        return float(x @ self.qubo_matrix @ x + self.linear_terms @ x)

    def find_ground_truth(self) -> Tuple[float, float, str]:
        """Exhaustively scans the candidate space to establish exact theoretical minimum and maximum energies."""
        n = self.num_qubits
        min_e = float("inf")
        max_e = -float("inf")
        best_str = ""

        for b in range(2**n):
            bits = "".join(str((b >> i) & 1) for i in reversed(range(n)))
            e = self.compute_qubo_energy(bits)
            if e < min_e:
                min_e = e
                best_str = bits
            if e > max_e:
                max_e = e

        return min_e, max_e, best_str

    def optimize_qaoa_aer(
        self,
        p: int = 1,
        shots: int = 2048,
        max_iter: int = 40,
        optimizer: str = "COBYLA",
    ) -> QAOAOptimizationResult:
        """Optimizes variational parameters (gamma, beta) using Qiskit AerSimulator."""
        from .ionq_utils import IonQBackendAdapter

        sim = AerSimulator()
        qc = self.build_qaoa_circuit(p=p)
        n = self.num_qubits

        gamma_params = [p for p in qc.parameters if p.name.startswith("γ")]
        beta_params = [p for p in qc.parameters if p.name.startswith("β")]

        # Ground truth reference
        min_e, max_e, opt_bitstring = self.find_ground_truth()

        convergence_history = []

        def objective(params: np.ndarray) -> float:
            gamma_vals = params[:p]
            beta_vals = params[p:]

            param_dict = {}
            for i in range(p):
                param_dict[gamma_params[i]] = gamma_vals[i]
                param_dict[beta_params[i]] = beta_vals[i]

            bound_qc = qc.assign_parameters(param_dict)
            job = sim.run(bound_qc, shots=shots)
            counts = job.result().get_counts()

            # Expectation value <H_C>
            energy_sum = 0.0
            for bits, count in counts.items():
                energy_sum += count * self.compute_qubo_energy(bits)

            expected_energy = energy_sum / shots
            convergence_history.append(expected_energy)
            return expected_energy

        # Initial parameter heuristics (small angles)
        init_gamma = [0.4 * (i + 1) for i in range(p)]
        init_beta = [0.3 * (p - i) for i in range(p)]
        initial_params = np.array(init_gamma + init_beta)

        opt_options = {"maxiter": max_iter}
        if optimizer.upper() == "COBYLA":
            opt_options["rhobeg"] = 0.3

        res = minimize(
            objective,
            initial_params,
            method=optimizer,
            options=opt_options,
        )

        opt_gamma = res.x[:p].tolist()
        opt_beta = res.x[p:].tolist()

        # Run final circuit with optimal parameters
        final_dict = {}
        for i in range(p):
            final_dict[gamma_params[i]] = opt_gamma[i]
            final_dict[beta_params[i]] = opt_beta[i]

        final_qc = qc.assign_parameters(final_dict)
        final_job = sim.run(final_qc, shots=shots)
        final_counts = final_job.result().get_counts()

        # Extract best bitstring from measurements
        best_measured = min(final_counts.keys(), key=lambda b: self.compute_qubo_energy(b))
        best_measured_e = self.compute_qubo_energy(best_measured)

        # Ground state probability
        opt_shots = final_counts.get(opt_bitstring, 0)
        p_opt = opt_shots / shots

        # Expected energy of final state
        final_expected = sum(cnt * self.compute_qubo_energy(b) for b, cnt in final_counts.items()) / shots

        # Approximation Ratio: (E_exp - E_max) / (E_min - E_max)
        denom = (min_e - max_e) if abs(min_e - max_e) > 1e-6 else 1.0
        approx_ratio = float((final_expected - max_e) / denom)

        # Transpile to IonQ native basis for gate metric comparison
        ionq_qc = IonQBackendAdapter.transpile_for_ionq(final_qc)

        route_summary = self.evaluate_bitstring(best_measured)

        return QAOAOptimizationResult(
            depth_p=p,
            optimal_gamma=opt_gamma,
            optimal_beta=opt_beta,
            expected_energy=final_expected,
            ground_truth_energy=min_e,
            approximation_ratio=approx_ratio,
            ground_state_probability=p_opt,
            best_measured_bitstring=best_measured,
            measured_counts=final_counts,
            convergence_history=convergence_history,
            circuit_depth_native=final_qc.depth(),
            circuit_depth_ionq=ionq_qc.depth(),
            gate_counts_native=dict(final_qc.count_ops()),
            gate_counts_ionq=dict(ionq_qc.count_ops()),
            route_result=route_summary,
        )

    def evaluate_bitstring(self, bitstring: str) -> QAOARouteResult:
        """Decodes measured bitstring into an alpine route summary."""
        reversed_bits = bitstring[::-1]
        selected = []
        total_vert = 0.0
        total_time = 0.0
        run_names = []

        for i, bit in enumerate(reversed_bits[: self.num_qubits]):
            if bit == "1":
                edge = self.edges[i]
                selected.append(edge)
                if edge.edge_type == "run":
                    total_vert += edge.vertical_drop
                    run_names.append(edge.name)
                total_time += edge.duration_min

        unique_runs = len(set(run_names))
        total_runs = len(run_names)
        uniqueness_ratio = (unique_runs / total_runs) if total_runs > 0 else 1.0

        return QAOARouteResult(
            selected_edges=selected,
            total_vertical_ft=total_vert,
            total_time_min=total_time,
            run_uniqueness_ratio=uniqueness_ratio,
            optimal_bitstring=bitstring,
            circuit_depth=0,
            num_qubits=self.num_qubits,
        )

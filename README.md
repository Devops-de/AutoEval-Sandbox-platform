# AutoEval Sandbox: Ephemeral AI Code Evaluation & Algorithmic Benchmarking Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-cgroups%20v2-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![Redis](https://img.shields.io/badge/Redis-Job%20Queue-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-Distributed%20Workers-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![AWS ECS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/ecs)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC.svg?logo=terraform&logoColor=white)](https://www.terraform.io)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen.svg)](#-testing--validation)

An enterprise-grade, asynchronous code evaluation platform engineered to safely benchmark and grade untrusted LLM-generated code under strict isolation constraints.



---

## 🔬 About AutoEval Sandbox

**AutoEval Sandbox** is an automated, secure execution and benchmarking engine engineered to evaluate untrusted LLM-generated Python code at scale. It combines **Linux kernel-level sandboxing (cgroups v2)**, **pre-execution AST security filtering**, and **mathematical Big-O runtime profiling** to deliver production-grade code evaluation without security or performance risks.

Modern Large Language Models (LLMs) trained on code synthesis present a critical infrastructure challenge: **how to evaluate non-deterministic, untrusted code generated at scale without compromising host infrastructure, introducing network pivot vulnerabilities, or suffering resource-exhaustion denial of service.**

AutoEval solves this by establishing a defense-in-depth pipeline that validates code across three essential axes: **Safety**, **Correctness**, and **Algorithmic Efficiency**.

---

### 🎯 Why AutoEval? Traditional Runners vs. AutoEval Sandbox

| Feature | Naive In-Process (`exec` / `subprocess`) | Standard Docker Containers | 🛡️ **AutoEval Sandbox** |
| :--- | :---: | :---: | :---: |
| **Network Egress** | ❌ Full Host Access | ⚠️ Allowed by Default | ✅ **Isolated (`--net=none`, zero egress)** |
| **Resource Bounds** | ❌ Unbounded (Host Freeze) | ⚠️ Uncapped unless configured | ✅ **Strict cgroups (256MB RAM / 0.5 vCPU)** |
| **Pre-Execution Safety** | ❌ None | ❌ None | ✅ **Static AST Gatekeeper & Bandit SAST** |
| **Algorithmic Profiling** | ❌ Single-point timing | ❌ Basic runtime only | ✅ **Empirical Big-O Curve Fitting ($O(1)$ to $O(2^N)$)** |
| **Sandbox Breakout Defense**| ❌ Host Compromised | ⚠️ Vulnerable to setuid / caps | ✅ **Dropped Capabilities (`ALL`) & Non-Root (UID 10001)** |
| **Batch Scalability** | ❌ Blocks Web Thread | ⚠️ Manual container scaling | ✅ **Asynchronous Redis + Celery Worker Pool** |
| **Automated Grading** | ❌ Pass/Fail Boolean | ❌ Exit code only | ✅ **Structured 100-Point Alignment Rubric** |

---

### 🧩 Core Platform Capabilities

- **🛡️ Kernel-Enforced Isolation**: Executes every evaluation in an ephemeral, unprivileged container with hard memory ceilings (`256MB`), CPU bandwidth throttling (`0.5 vCPU`), zero network access (`--net=none`), and an immutable read-only root filesystem with memory-backed tmpfs.
- **🔍 Static AST Gatekeeper**: Parses Python Abstract Syntax Trees before execution to intercept malicious imports (`os`, `sys`, `subprocess`, `socket`), dangerous builtins (`eval`, `exec`, `open`), and Python object model escape gadgets (`__subclasses__`, `__globals__`).
- **📈 Empirical Big-O Complexity Profiling**: Scales input sizes $N \in [50, \dots, 1600]$ to measure empirical wall-clock time and memory consumption, applying Ordinary Least Squares (OLS) regression to verify asymptotic algorithmic complexity.
- **🧪 Deterministic Test Runner**: Executes user/benchmark test suites deterministically, isolating stdout/stderr and recording millisecond-level execution durations per test case.
- **⚡ High-Throughput Asynchronous Queue**: Decouples API ingestion from execution using Redis and Celery distributed workers with strict worker prefetch controls.
- **📊 100-Point Alignment Rubric**: Emits structured, machine-readable JSON reports compliant with AI lab alignment standards, scoring Correctness (40%), Security (30%), Big-O Complexity (20%), and Resource Efficiency (10%).

---

### 🔄 How It Works in 4 Steps

```
[1. Submit]  ──> Client submits code, test suite, and expected complexity via FastAPI
[2. Screen]  ──> Static AST Gatekeeper validates syntax & blocks security violations
[3. Isolate] ──> Ephemeral container executes code under cgroup limits & zero network
[4. Grade]   ──> System runs pytest + Big-O profiler & returns a 100-point JSON rubric
```

---

## 🏗 Technical Architecture & Data Flow

```mermaid
flowchart TD
    Client["Client / LLM Benchmark Suite"] -->|HTTP POST /api/v1/evaluations| API["FastAPI Gateway (AsyncIO)"]
    API -->|Enqueue Evaluation Task| Redis[("Redis Broker & Result Store")]
    API -->|HTTP GET /api/v1/evaluations/{id}| Client
    
    subgraph WorkerNode ["Celery Worker & Sandboxing Engine"]
        Redis -->|Consume Task (prefetch=1)| Worker["Celery Evaluation Worker"]
        
        subgraph StaticAnalysis ["Phase 1: Pre-Execution AST Gatekeeper"]
            Worker --> AST["Static AST Analyzer & Bandit SAST"]
            AST -->|Banned imports, calls, or dunders detected?| SecurityCheck{"Passed AST Check?"}
        end

        subgraph EphemeralSandbox ["Phase 2: Hardened Ephemeral Sandbox"]
            SecurityCheck -->|Yes| DockerEngine["Docker Sandbox Engine"]
            DockerEngine -->|Spawn isolated container| Container["Ephemeral Python Container"]
            Container --- Cgroups["cgroups: 256MB RAM / 0.5 vCPU"]
            Container --- NetNone["Network: --net=none"]
            Container --- ReadOnly["Filesystem: read-only + tmpfs"]
            Container --- Caps["Capabilities: cap_drop=['ALL']"]
            Container --- NonRoot["User: UID 10001:10001"]
        end

        subgraph Benchmarking ["Phase 3: Deterministic Test & Complexity Engine"]
            Container --> PytestRunner["Deterministic Pytest Harness"]
            Container --> BigOProfiler["Empirical Big-O Profiler (N vs Time/Memory)"]
        end
        
        subgraph Reporting ["Phase 4: Rubric Generation"]
            SecurityCheck -->|Violations found| RubricGen["Rubric Scoring Engine"]
            PytestRunner --> RubricGen
            BigOProfiler --> RubricGen
            RubricGen --> JSONReport["Standardized 100-Point JSON Report"]
        end
    end
    
    JSONReport -->|Persist state & metrics| Redis
```

---

## 🛡️ Kernel-Level Security & Defense-in-Depth Matrix

AutoEval enforces a multi-tier defense boundary designed to withstand malicious payloads, fork bombs, and container breakout exploits:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Host Operating System                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Docker Daemon Engine                   │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │               Hardened Sandbox Container            │  │  │
│  │  │  • Linux cgroups v2 (CPU CFS quota, hard RAM cap)    │  │  │
│  │  │  • Network Namespace: CLONE_NEWNET (--net=none)     │  │  │
│  │  │  • Read-only Root Filesystem (read_only=True)       │  │  │
│  │  │  • Memory-backed /tmp (rw,noexec,nosuid,size=32m)   │  │  │
│  │  │  • Dropped Linux Capabilities (cap_drop=['ALL'])     │  │  │
│  │  │  • PR_SET_NO_NEW_PRIVS (no-new-privileges:true)     │  │  │
│  │  │  • Unprivileged Execution (UID 10001:10001)         │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │              Execution Target                 │  │  │  │
│  │  │  │  • Pre-Execution AST Static Gatekeeper       │  │  │  │
│  │  │  │  • Pytest Deterministic Harness               │  │  │  │
│  │  │  │  • Big-O Parametric Profiler                  │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Security Mechanism | Technical Specification | Threat Mitigated |
| :--- | :--- | :--- | :--- |
| **AST Parser** | Static AST node visitor (`ast.NodeVisitor`) | Pre-execution AST walk inspection blocking disallowed modules, builtins, and attribute lookups. | Blocks RCE, unauthorized filesystem calls, and socket initialization prior to execution. |
| **Dunder Shield** | Attribute blacklist verification | Prohibits `__subclasses__`, `__bases__`, `__mro__`, `__globals__`, `__code__`, `__builtins__`. | Prevents Python object model sandbox escapes and gadget chain invocations. |
| **Memory cgroup** | Linux cgroups v2 Memory Controller | `mem_limit="256m"`, `memswap_limit="256m"` (`memory.max=268435456`, `memory.swap.max=0`). | Eliminates host memory exhaustion, OOM cascades, and swap thrashing. |
| **CPU CFS Quota** | Completely Fair Scheduler (CFS) bandwidth control | `cpu_period=100000`, `cpu_quota=50000` (Enforcing max $0.5$ vCPU execution rate). | Prevents CPU-starvation denial-of-service from infinite loops (`while True`). |
| **Network Jail** | Network namespace unsharing (`CLONE_NEWNET`) | Docker `network_mode="none"` (zero loopback egress, zero external routing). | Prevents data exfiltration, reverse TCP shells, SSRF, and command & control (C2) beacons. |
| **Filesystem Jail** | Immutable root mount | `read_only=True`, isolated RAM tmpfs mounted at `/tmp` (`size=32m,noexec,nosuid`). | Eliminates rootkit installation, script injection, and persistent file mutations. |
| **Privilege Filter** | Linux Capability bounding set & privilege escalation clamp | `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]`, UID `10001:10001`. | Prevents container breakout, setuid binary execution, and root privilege escalation. |

---

## 📈 Empirical Algorithmic Big-O Profiling Methodology

Unlike traditional evaluation engines that merely record execution runtime for a single test input, AutoEval profiles asymptotic time complexity:

1. **Parametric Input Scaling**: Generates synthetic, deterministic inputs across scaled dimensions:
   $$N \in [50, 100, 200, 400, 800, 1600]$$
2. **Noise Rejection**: Runs multiple execution trials per $N$ and selects the minimum wall-clock duration ($\Delta t$) to eliminate kernel context-switching anomalies and OS scheduling jitter.
3. **High-Resolution Resource Tracking**: Utilizes `time.perf_counter_ns` for nanosecond timing and `tracemalloc` for peak heap allocation tracking.
4. **Ordinary Least Squares (OLS) Curve Fitting**: Transforms $(N, T(N))$ coordinates and computes the Coefficient of Determination ($R^2$) across standard complexity hypotheses:
   - **Constant**: $T(N) = c$
   - **Logarithmic**: $T(N) = a \ln(N) + b$
   - **Linear**: $T(N) = a N + b$
   - **Linearithmic**: $T(N) = a (N \ln N) + b$
   - **Quadratic**: $T(N) = a N^2 + b$
   - **Cubic**: $T(N) = a N^3 + b$
5. **Occam's Razor / Parsimony Selection**: Implements statistical parsimony: when quadratic and cubic fits both achieve high correlation ($R^2 \ge 0.98$), the engine prefers the lower-order polynomial to prevent overfitting noise.

---

## 📊 100-Point Alignment Evaluation Rubric

AutoEval evaluates submissions against an enterprise 4-pillar alignment rubric:

```
Total Rubric Score: 100 Points
├── 🧪 Correctness (40 pts)
│   └── Formula: (passed_tests / total_tests) * 40.0
├── 🔒 Security & Safety (30 pts)
│   ├── Clean AST Verification: 30.0 pts
│   └── AST Policy Violation: 0.0 pts (Triggers immediate SECURITY_VIOLATION verdict)
├── ⚡ Algorithmic Complexity (20 pts)
│   ├── Exact Match (Inferred == Expected): 20.0 pts
│   ├── Near-Optimal Match (e.g., O(N) vs O(N log N)): 14.0 pts
│   └── Discrepant Complexity (e.g., O(N^2) vs Expected O(N)): 5.0 - 8.0 pts
└── 📈 Resource & Efficiency (10 pts)
    ├── Fast Execution (< 25% timeout quota): 10.0 pts
    ├── Moderate Execution (< 75% timeout quota): 7.0 pts
    └── Near-Quota Execution (>= 75% timeout quota): 4.0 pts
```

---

## 🚀 Quickstart Guide

### 1. Local Development Setup

```bash
# Clone the repository
git clone https://github.com/Devops-de/AutoEval-Sandbox-platform.git
cd AutoEval-Sandbox-platform

# Create virtual environment & install dependencies
python -m venv venv
source venv/bin/activate  # Or `.\venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run the full test suite
pytest -v
```

### 2. Start API Gateway Locally

```bash
uvicorn autoeval.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 3. Run Full Distributed Stack via Docker Compose

```bash
docker compose -f docker/docker-compose.yml up --build
```

Services initialized:
1. `autoeval-redis`: Redis 7 in-memory task broker and result store.
2. `autoeval-api`: FastAPI asynchronous gateway service.
3. `autoeval-worker`: Celery worker with access to Docker daemon for ephemeral sandbox instantiation.

---

## 📡 API Reference

### Synchronous Evaluation: `POST /api/v1/evaluations/sync`
Evaluates code in real-time and returns the complete JSON rubric report:

```json
{
  "code": "def quick_sort(arr):\n    if len(arr) <= 1: return arr\n    pivot = arr[len(arr) // 2]\n    return quick_sort([x for x in arr if x < pivot]) + [x for x in arr if x == pivot] + quick_sort([x for x in arr if x > pivot])",
  "test_suite": "def test_sort():\n    assert quick_sort([3, 1, 2]) == [1, 2, 3]\n    assert quick_sort([]) == []",
  "entrypoint": "quick_sort",
  "expected_complexity": "O(N log N)",
  "timeout_seconds": 10.0,
  "memory_limit_mb": 256
}
```

#### Example Output Report:

```json
{
  "task_id": "a9a7a61c-aa69-4b81-945a-1354d6eda64d",
  "status": "COMPLETED",
  "verdict": "PASSED",
  "score_breakdown": {
    "correctness_score": 40.0,
    "security_score": 30.0,
    "complexity_score": 20.0,
    "efficiency_score": 10.0,
    "total_score": 100.0
  },
  "security_analysis": {
    "is_safe": true,
    "violations": [],
    "max_loop_depth": 0,
    "has_recursion": true
  },
  "test_results": {
    "total_tests": 2,
    "passed": 2,
    "failed": 0,
    "pass_rate": 1.0,
    "duration_ms": 1.39
  },
  "algorithmic_complexity": {
    "inferred_complexity": "O(N log N)",
    "expected_complexity": "O(N log N)",
    "complexity_matched": true,
    "r_squared": 0.9997,
    "data_points": [
      { "n": 50, "wall_time_ms": 0.156, "memory_peak_kb": 99.26 },
      { "n": 100, "wall_time_ms": 0.317, "memory_peak_kb": 3.65 },
      { "n": 200, "wall_time_ms": 0.667, "memory_peak_kb": 6.33 },
      { "n": 400, "wall_time_ms": 1.458, "memory_peak_kb": 16.92 },
      { "n": 800, "wall_time_ms": 3.073, "memory_peak_kb": 39.43 },
      { "n": 1600, "wall_time_ms": 6.514, "memory_peak_kb": 95.75 }
    ]
  },
  "resource_utilization": {
    "wall_clock_time_ms": 46.29,
    "cpu_time_ms": 46.29,
    "peak_memory_mb": 0.85,
    "memory_limit_mb": 256
  }
}
```

### Asynchronous Evaluation: `POST /api/v1/evaluations`
Enqueues the job and immediately returns HTTP 202 Accepted with a task ID and polling URL:

```json
{
  "task_id": "4a1d7f6c-829b-4392-a169-dc9a473188fa",
  "status": "QUEUED",
  "poll_url": "/api/v1/evaluations/4a1d7f6c-829b-4392-a169-dc9a473188fa",
  "message": "Evaluation job queued for execution in isolated sandbox."
}
```

---

## ☁️ Terraform Infrastructure Deployment (AWS)

The `terraform/` directory provisions production infrastructure:
- **AWS VPC**: Multi-AZ with public & private subnets.
- **AWS ECS Fargate Cluster**: Scalable serverless container tasks.
- **AWS ElastiCache Redis**: High-throughput message broker and task result cache.
- **Application Load Balancer (ALB)**: TLS termination and traffic routing.
- **AWS CloudWatch**: Centralized logging and container metric streams.

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## 🧪 Testing & Validation

```bash
# Run all unit and integration tests (28 tests)
pytest -v
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

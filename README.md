# AutoEval Sandbox: Ephemeral AI Code Evaluation & Algorithmic Benchmarking Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-cgroups%20v2-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![Redis](https://img.shields.io/badge/Redis-Job%20Queue-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-Distributed%20Workers-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![AWS ECS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/ecs)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC.svg?logo=terraform&logoColor=white)](https://www.terraform.io)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-grade, asynchronous code evaluation platform engineered to safely benchmark and grade untrusted LLM-generated code under strict isolation constraints.

> **Target Audience**: AI Labs (OpenAI, Scale AI, Anthropic), Alignerr, and Senior Python / Platform / DevOps Engineering teams building evaluation harnesses for AI model alignment and code generation benchmarks.

---

## 📌 How to Put It on Your Resume

> **AutoEval Sandboxed Benchmarking Platform**: Architected an automated evaluation engine using Python (FastAPI) and Docker SDK to safely execute untrusted code in hardened, resource-constrained Linux sandboxes; automated deterministic test harnesses (pytest), AST security parsing, and algorithmic Big-O profiling for LLM benchmark alignment.

### Key Competencies Demonstrated:
- **Defense-in-Depth Container Sandboxing**: Linux cgroups v2 (`256MB` RAM, `0.5 vCPU`), isolated network namespace (`--net=none`), read-only root filesystems, and dropped Linux capabilities.
- **Pre-Execution AST Static Security**: Abstract Syntax Tree parsing to preemptively block RCE, malicious dunder gadgets (`__subclasses__`, `__globals__`), and unauthorized network/file I/O.
- **Empirical Big-O Profiling Engine**: Dynamic runtime benchmarking scaling across input sizes $N \in [10, 50, \dots, 2500]$ with Ordinary Least Squares regression to classify algorithmic time complexity ($O(1)$, $O(\log N)$, $O(N)$, $O(N \log N)$, $O(N^2)$, $O(2^N)$).
- **Asynchronous Architecture**: Non-blocking FastAPI gateway backed by Redis and Celery distributed task queues.
- **Production Cloud Infrastructure**: Infrastructure as Code (Terraform) deploying AWS ECS/Fargate, ElastiCache Redis, VPC networking, and Application Load Balancers.

---

## 🏗 System Architecture

```
[Client / LLM Benchmark Suite]
              │
              ▼ HTTP POST /api/v1/evaluations
   [FastAPI Gateway (AsyncIO)] 
              │
              ▼ Enqueue Task
    [Redis Broker / Celery Queue]
              │
              ▼ Dispatch
 [Worker: Ephemeral Docker Sandbox Engine]
 ├── Pre-Execution AST Static Security (Block RCE, sys, os, eval, dunder exploits)
 ├── Linux cgroups (256MB RAM quota, 0.5 vCPU throttling)
 ├── Isolated Network Namespace (--net=none, no egress)
 ├── Deterministic Test Runner (pytest / assertion captures)
 └── Empirical Big-O Profiler (Wall-clock time & memory scaling vs N)
              │
              ▼
 [Structured Evaluation Rubric (0-100) & JSON Report]
```

---

## 🛡️ Defense-in-Depth Security Matrix

| Layer | Security Mechanism | Threat Prevented |
| :--- | :--- | :--- |
| **AST Parser** | Static inspection of AST nodes (`ast.NodeVisitor`) | Blocks dangerous imports (`os`, `sys`, `subprocess`, `socket`, `pickle`), calls (`eval`, `exec`, `open`), and dunder exploits (`__subclasses__`). |
| **Linux cgroups** | Memory limit (`mem_limit=256m`, `memswap_limit=256m`) | Prevents memory-exhaustion DoS attacks (`[0] * 10**9`). |
| **CPU Quotas** | CPU throttling (`cpu_period=100000`, `cpu_quota=50000`) | Throttles CPU-intensive infinite loops (`while True: pass`). |
| **Network Isolation** | Container network namespace (`--net=none`) | Eliminates data exfiltration, socket connections, and reverse shells. |
| **Filesystem Hardening** | `read_only=True`, isolated `tmpfs` (`/tmp:size=32m,noexec,nosuid`) | Blocks filesystem modification, rootkit installations, or persistence. |
| **Privilege Dropping** | `cap_drop=['ALL']`, `no-new-privileges:true`, UID `10001` | Mitigates container breakout and privilege escalation vulnerabilities. |

---

## 📊 100-Point Alignment Evaluation Rubric

AutoEval automatically grades submissions using a standardized 4-dimensional alignment rubric:

```
Total Score: 100 Points
├── 🧪 Correctness (40%): Pass rate of unit tests (pass_rate * 40.0)
├── 🔒 Security & Safety (30%): Zero AST violations & clean SAST scan
├── ⚡ Algorithmic Big-O (20%): Match between inferred vs expected Big-O complexity
└── 📈 Resource Efficiency (10%): Wall-clock duration & memory usage within bounds
```

---

## 🚀 Quickstart Guide

### 1. Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/autoeval-sandbox.git
cd autoeval-sandbox

# Create virtual environment & install dependencies
python -m venv venv
source venv/bin/activate  # Or `.\venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run the test suite
pytest -v
```

### 2. Start API Gateway Locally

```bash
uvicorn autoeval.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Run Full Distributed Stack via Docker Compose

```bash
docker compose -f docker/docker-compose.yml up --build
```

This launches:
1. `autoeval-redis` (Redis 7 In-Memory Broker)
2. `autoeval-api` (FastAPI Gateway)
3. `autoeval-worker` (Celery Distributed Evaluation Worker with Docker socket access)

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

#### Example JSON Rubric Response:

```json
{
  "task_id": "967664e5-472d-41da-ae3a-8610ebfd7e42",
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
    "duration_ms": 1.25
  },
  "algorithmic_complexity": {
    "inferred_complexity": "O(N log N)",
    "expected_complexity": "O(N log N)",
    "complexity_matched": true,
    "r_squared": 0.9842,
    "data_points": [
      { "n": 50, "wall_time_ms": 0.08, "memory_peak_kb": 12.4 },
      { "n": 100, "wall_time_ms": 0.17, "memory_peak_kb": 22.8 },
      { "n": 200, "wall_time_ms": 0.38, "memory_peak_kb": 43.1 },
      { "n": 400, "wall_time_ms": 0.82, "memory_peak_kb": 85.0 }
    ]
  },
  "resource_utilization": {
    "wall_clock_time_ms": 42.15,
    "cpu_time_ms": 42.15,
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
# Run all unit and integration tests
pytest -v

# Run with coverage report
pytest --cov=autoeval --cov-report=term-missing
```

---

## 📄 License

MIT License. Designed for portfolio demonstration, LLM alignment benchmarking, and production engineering evaluation platforms.

**PRD v1.0** cho AgentOps theo đúng định hướng:

* Bootstrap
* Dev startup
* SDK-first
* Debug & replay focused
* Không enterprise-heavy

---

# 📄 PRD v1.0 — AgentOps (Dev-first AI Agent Control Plane)

---

# 1️⃣ Executive Summary

AgentOps là một dev tool giúp AI startup:

* Trace từng bước thực thi của AI agent
* Hiểu cost/token usage theo run
* Replay lại execution để debug
* So sánh prompt/model dễ dàng

Mục tiêu:

> Biến AI agent từ “black box” thành “debuggable system”.

---

# 2️⃣ Problem Statement

AI agents trong production gặp các vấn đề:

1. Không thấy intermediate steps
2. Không biết tool call nào fail
3. Không reproduce được bug
4. Cost tăng đột biến không rõ nguyên nhân
5. Prompt changes khó so sánh impact

Logs truyền thống không đủ vì:

* LLM calls là dynamic
* Tool calls nested
* Context state khó theo dõi

---

# 3️⃣ Target Users (ICP)

Primary:

* AI SaaS founders (2–20 engineers)
* Dev build multi-step AI workflows
* Startup dùng OpenAI / Anthropic SDK

Secondary:

* Indie hackers
* AI product engineers

Không target:

* Enterprise risk teams
* Compliance departments
* Research labs

---

# 4️⃣ Product Vision

> AgentOps là Sentry cho AI agents.

Tập trung vào:

* Debug visibility
* Cost transparency
* Replay safety

Không làm:

* Enterprise governance suite
* Full AI observability platform
* Model evaluation research tool

---

# 5️⃣ Core Use Cases

### UC1 — Debug failing agent run

Dev xem:

* Timeline
* Tool call payload
* LLM response
* Error trace

### UC2 — Investigate cost spike

Dev xem:

* Cost per run
* Cost per model
* Cost per workflow

### UC3 — Test prompt change safely

Dev:

* Replay run
* Change model/temp
* Compare outputs

---

# 6️⃣ Feature Scope — MVP

---

## 6.1 SDK

### Requirements

* Python SDK
* OpenAI + Anthropic support
* `@track()` decorator
* Async event batching
* Auto run_id + span_id
* Basic redaction hook

### Non-goals

* Auto instrumentation mọi framework
* Support mọi provider

---

## 6.2 Run Trace

### Functional Requirements

* List runs (latest first)
* View run detail
* Timeline view of spans
* Display:

  * type (llm/tool)
  * model
  * tokens
  * latency
  * status
* Expand to view input/output (truncated)

### Non-functional

* Load run detail < 500ms
* Support 100k runs/project initial

---

## 6.3 Cost Tracking

### Functional

* Aggregate:

  * Total cost per run
  * Daily cost
  * Model breakdown
* Filter by date

### Non-goals

* Budget enforcement
* Alerting (v2)

---

## 6.4 Prompt Versioning

### Functional

* Store prompt key + version
* Link run to prompt version
* Compare prompt content diff

### Non-goals

* Prompt editing UI
* Prompt experiment framework

---

## 6.5 Replay (LLM-only v1)

### Functional

* Create replay from run
* Override:

  * model
  * temperature
* Generate new run
* Side-by-side output compare

### Constraints

* Tool spans not re-executed
* Replay limited to LLM spans only

---

# 7️⃣ Technical Architecture

### Components

* FastAPI backend
* Postgres
* Redis (Arq worker)
* Object storage (optional for large payloads)
* React/Next.js dashboard

### Data Flow

SDK → Ingest API → raw_events → worker normalize → runs/spans → dashboard

Replay:

Dashboard → Replay API → worker execute LLM → new run stored

---

# 8️⃣ Metrics of Success (MVP)

### Activation

* Dev installs SDK
* First run appears in dashboard < 5 minutes

### Engagement

* 70% beta users view >3 runs
* 30% use replay at least once

### Retention

* 40% users active after 30 days

### Revenue

* Convert 5–10% free → paid in 3 months

---

# 9️⃣ Pricing Model (Bootstrap-aligned)

Free:

* 1k runs/month
* 7-day retention

Pro ($49–$99):

* 30-day retention
* Replay enabled
* Team view

Startup ($199):

* Higher limits
* Priority support

---

# 🔟 Non-Goals (để không overbuild)

* SOC2
* Multi-org enterprise RBAC
* Budget approval workflows
* Custom on-prem deployment
* Alerting engine
* Advanced eval scoring

---

# 1️⃣1️⃣ Risks & Mitigation

### Risk 1 — Commoditization

Mitigation:

* Focus on ultra simple DX
* Fast iteration
* Dev niche clarity

### Risk 2 — Overbuilding infra

Mitigation:

* Append-only raw_events
* No microservices early

### Risk 3 — Low willingness to pay

Mitigation:

* Make replay feature Pro-only
* Strong value messaging around debugging time saved

---

# 1️⃣2️⃣ Future Roadmap (Not MVP)

* Tool span replay
* Drift detection
* Cost anomaly alerts
* OpenTelemetry compatibility
* Multi-agent graph visualization
* Evaluation scoring API

---

# 1️⃣3️⃣ Definition of Done (MVP Launch Criteria)

* SDK pip installable
* 10-line integration
* Trace timeline functional
* Replay works
* Stripe payment integrated
* Public docs live
* Demo project working

---

# 🔥 Strategic Note

Với bootstrap strategy, thành công không phải:

> “Feature complete.”

Mà là:

> “Dev cài xong và nói: damn, cái này cứu tôi 3 tiếng debug.”


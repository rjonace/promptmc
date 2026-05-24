# Development Roadmap

**Project Vision (v2.x / v3.x):** We are building `PromptMC`, an advanced web-based SaaS platform that wraps the `OpenMC` nuclear physics engine. It translates natural language into complex Monte Carlo simulations, visualizes them, optimizes them autonomously, and orchestrates the heavy compute on the cloud.

### Phase 1: Core Functionality (Current)
- [x] Project scaffolding with Poetry
- [x] CLI architecture with Typer
- [x] OpenTelemetry integration
- [x] CI/CD pipeline
- [x] Documentation foundation

### Phase 2: OpenMC Integration
- [x] OpenMC Python API wrapper
- [x] Subprocess invocation support
- [x] Input file validation
- [x] Configuration file generation
- [x] Output parsing and analysis

### Phase 3: Advanced Features
- [x] Parallel execution support
- [x] Result visualization
- [x] Configuration templates
- [x] Batch simulation runner
- [x] Performance optimization tools

### Phase 4: Production Features (v1.0)
- [x] Configuration file schema validation
- [x] Advanced error handling
- [x] Progress reporting
- [x] Resource management
- [x] Plugin system
- [x] CLI Phase 4 integration (`schema-check`, `list-plugins`, `--schema` flag)
- [x] Natural-language assistant command (`ask`) with optional OpenAI-compatible LLM mode
- [x] 218 tests, 82% coverage, and zero lint warnings

## Version 2.0 (Future)

### Phase 5: Cloud & Advanced AI
- [ ] **Cloud-Native Orchestration**: Deploy parallel/batch workloads to cloud environments (GCP/Kubernetes) for large-scale parameter sweeps.
- [ ] **Expanded Agentic Capabilities**: LLM analysis of simulation outputs to autonomously suggest geometry, material, or optimization tweaks.
- [ ] **Pre-Run Visualizations**: Lightweight terminal-based visual feedback of geometry and materials prior to execution.

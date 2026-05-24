# Development Roadmap

**Project Vision:** We are building `PromptMC`, an advanced web-based SaaS platform that wraps the `OpenMC` nuclear physics engine. It translates natural language into complex Monte Carlo simulations, visualizes them, optimizes them autonomously, and orchestrates the heavy compute on the cloud.

### Phase 1: Core Functionality
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

## Version 3.0 (Future)

### Phase 6: The SaaS Web Platform
- [ ] **Interactive Web Interface**: A modern frontend (Next.js/React) for chatting with the PromptMC agent and viewing live 3D geometry rendering (WebGL/VTK.js).
- [ ] **REST/GraphQL API Layer**: A robust backend bridging natural language requests to the Python wrapper and queuing cloud jobs.
- [ ] **Multi-Tenant Architecture**: User accounts, project workspaces, secure authentication, and cloud compute billing/credits.
- [ ] **Real-Time Telemetry Dashboard**: Web-based exposure of OpenTelemetry data to watch batches run in real-time, track particles, and monitor usage.
- [ ] **Collaborative Hub**: Publish and share "PromptMC Recipes" (validated reactor/shielding setups) for others to fork and run.

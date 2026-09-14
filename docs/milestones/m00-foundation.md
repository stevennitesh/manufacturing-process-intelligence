# M0 — Repository foundation

**Status:** `✓ Complete`

**Objective:** establish a reproducible Python project and automated engineering
quality gates without adding modeling.

```mermaid
flowchart LR
    R["✓ Runtime<br/>Python 3.12, uv, lockfile"]
    P["✓ Package<br/>src/mpi and CLI shell"]
    C["✓ Application core<br/>configuration"]
    Q["✓ Quality system<br/>pytest, Ruff, Pyright, pre-commit"]
    D["✓ Repository system<br/>data hygiene, agent guidance, private origin"]
    I["✓ Continuous integration<br/>locked install, checks, CLI smoke test"]
    G{"✓ M0 gate<br/>tests, lint, and types pass"}

    R --> P --> C --> Q --> I --> G
    D --> I
```

## Completion evidence

- `uv.lock` resolves under Python 3.12.
- `uv run pytest` passes.
- `uv run ruff check .` passes.
- `uv run pyright` passes.
- GitHub Actions runs the locked installation, checks, and CLI smoke test.
- `main` is published to the private GitHub repository.

The [implementation roadmap](../implementation-roadmap.md) owns the current
cross-milestone status.

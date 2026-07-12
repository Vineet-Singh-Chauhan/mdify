# Contribution Guidelines

## Core Principles

### I. Architectural Tenets: Domain-Driven Design (DDD)
mdify is structured around the business domain, not the database or framework. We
isolate core business logic from external frameworks, UIs, and databases using a strict
layered architecture. We segment the application into distinct bounded contexts
(`IngestionContext`, `ParsingContext`, `AssetContext`) where state changes do not cross
context boundaries. Dependencies MUST point inward toward the Domain Layer, and the
Ubiquitous Language of the domain MUST be used throughout the codebase.

### II. Test-Driven Development (TDD)
We do not write production code unless a failing test dictates it. Testing is our primary
design tool. We strictly follow the Red-Green-Refactor cycle. Testing follows the Testing
Pyramid: 70% Unit Tests (fast, isolated, mocking I/O and queues), 20% Integration Tests
(verifying FastAPI, Celery, and filesystem sandbox behavior), and 10% E2E Tests
(black-box verification from React UI upload to ZIP download).

### III. Backend Standards (FastAPI & Python 3.11+)
We leverage modern Python 3.11+ features for speed, safety, and conciseness, including
union syntax (`|`), `asyncio.TaskGroup`, `StrEnum`, and Pydantic v2. Endpoints MUST use
Dependency Injection via `Depends()` rather than direct service instantiation. All
CPU-bound parsing MUST be offloaded to Celery workers via Redis. Domain exceptions MUST
be mapped to HTTP status codes via global exception handlers.

### IV. Frontend Standards (React SPA)
The frontend is a single-page application built with React, TypeScript, and TailwindCSS,
emphasizing a high-fidelity, Raycast-style developer utility interface. Strict TypeScript
is enforced (no `any` type, narrow `unknown` via type guards, explicit interfaces for
payloads). We separate Smart (Container) and Dumb (Presentational) components, use custom
hooks for complex logic (e.g. SSE/WebSocket handling), and manage state immutably using
React Query for server cache.

### V. Security Non-Negotiables
Security is our paramount concern. File uploads MUST be validated using magic numbers at
the FastAPI gateway, rejecting declarations by extensions or MIME-types. Payload sizes
MUST be strictly limited to 50MB and streams terminated if exceeded. XML, HTML, and
Office parsers MUST disable external entity resolution (preventing XXE) and ignore
macros. PDF JavaScript MUST be treated as inert text.

### VI. Custom Exception Hierarchy & Error Opacity
Generic exception classes (e.g., `Exception`, `ValueError`, `RuntimeError`,
`HTTPException` raised directly) are PROHIBITED in all application code. Every error
condition MUST be represented by a purpose-built, domain-specific exception class that
belongs to the bounded context in which it originates.

Rules:
- Every bounded context (`IngestionContext`, `ParsingContext`, `AssetContext`) MUST
  define its own exception base class (e.g., `IngestionError`, `ParsingError`,
  `AssetError`) from which all context-specific exceptions inherit.
- Exception class names MUST use Ubiquitous Language (e.g., `MagicNumberMismatchError`,
  `SandboxCreationError`, `VirusDetectedError`, `MarkdownCompilationError`).
- A global exception handler layer MUST intercept all domain exceptions and translate
  them to opaque, user-facing HTTP responses — internal class names, stack traces,
  file paths, and implementation details MUST NEVER be exposed in API responses.
- User-facing error messages MUST be human-readable, generic, and non-technical.
  They MUST NOT leak server internals (e.g., "An unexpected error occurred during
  processing" is acceptable; "pdfplumber raised IndexError at line 42" is not).
- Every custom exception class MUST be covered by at least one unit test verifying
  both its raise path and its translation to the correct sanitized HTTP response.


## Git & Commit Workflow

### 6.1 Branching Strategy
We follow Trunk-Based Development. The `main` branch is always deployable. Feature
branches are short-lived and branch off `main` as
`feature/[ticket-id]-short-description`.

### 6.2 Commit Messages
We follow Conventional Commits format to automate changelogs:
- `feat: add zip packaging to asset extractor`
- `fix: resolve memory leak in pdfplumber wrapper`
- `test: mock redis broker for ingestion pipeline`
- `refactor: apply DDD bounded contexts to parsing layer`

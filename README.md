# Property Investment RAG Consultant

A property research application that answers questions using local documents and external market context. It supports individual investors, wealth advisors, and relocation consultancies.

There are two interfaces: a React application backed by FastAPI, and a standalone Streamlit application that imports the same backend retrieval code directly.

## Features

- Chat with document sources and structured clarification questions.
- Regional comparisons tailored to an investor profile.
- Hybrid document retrieval: keyword search, embeddings, and optional reranking.
- Market and currency context from World Bank, BIS, and currency APIs; availability and dates vary by source.
- Login, admin and user roles, password management, and model selection in the React application.
- Admin controls for documents, users, LLM providers, saved answers, and market-data refreshes.
- Token usage tracking and cached answers in the FastAPI application.
- Streamlit chat, persona and market selection, a yield calculator, and a separate SQLite answer cache.

Answers are informational. Prompts require grounded figures, disclosure of missing data, and licensed advisor review for personalized investment decisions. Generated answers still require verification against their sources.

## Project structure

```text
Chatbot/
|-- backend/
|   |-- app.py                 FastAPI entry point and API routes
|   |-- config.py              Environment settings and paths
|   |-- rag_system.py          RAG orchestration, prompts, chat, comparisons
|   |-- document_loader.py     PDF, CSV, JSON, and TXT ingestion
|   |-- retriever.py           Keyword/semantic search, fusion, reranking
|   |-- llm_client.py          Model-provider HTTP calls
|   |-- market_data.py         External macroeconomic and currency context
|   |-- store.py               Users, sessions, LLM settings, usage, answer cache
|   |-- requirements.txt
|   |-- .env.example
|   `-- Dockerfile
|-- frontend/
|   |-- src/
|   |   |-- main.jsx           Browser entry point
|   |   |-- App.jsx            Application shell
|   |   |-- api.jsx            Fetch wrapper and shared UI helpers
|   |   |-- index.css          Tailwind layers and shared styles
|   |   |-- App.css            Layout and navigation styles
|   |   `-- components/        Login, chat, comparison, status, admin, password UI
|   |-- package.json
|   |-- vite.config.js
|   |-- README.md
|   `-- Dockerfile
|-- streamlit_app/
|   |-- app.py                 Streamlit entry point
|   |-- app_pages/             Chat and yield calculator pages
|   |-- advisor.py             Question-to-answer workflow
|   |-- query.py               Direct reuse of backend RAG and market data
|   |-- prompts.py             Persona-specific prompts
|   |-- llm.py                 Claude/OpenAI model integration
|   |-- tools.py               Yield and mortgage calculations
|   |-- cache.py               SQLite answer cache
|   |-- tests/                 Advisor and calculator tests
|   |-- requirements.txt
|   `-- README.md
|-- data/                      One subfolder per property market
|-- start.bat                  Windows launcher
|-- stop.bat                   Windows server stop script
|-- docker-compose.yml         Backend/frontend container configuration
|-- QUICKSTART.md
|-- LOCAL_MODE_GUIDE.md
|-- PROJECT_SUMMARY.md
|-- START_HERE_VSCODE.md
|-- VSCODE_SETUP.md
`-- README.md
```

Runtime files such as model downloads, embeddings, credentials, and user state are separate from application source.

## Architecture and request flow

```text
React browser UI -> FastAPI -> authentication and saved-answer lookup
                                  |
                                  v
                            PropertyInvestmentRAG
                                  |
                   document retrieval + market context
                                  |
                                  v
                              LLM provider
                                  |
                     answer + sources + usage -> React

Streamlit UI -> advisor/query -> shared backend retrieval + market context
                      |
               Streamlit LLM integration and SQLite cache
```

On startup, the backend loads documents, splits them into passages, and builds a TF-IDF index. Semantic embeddings and the reranker load in the background. Keyword retrieval is available while those components initialize.

For hybrid search, keyword and semantic rankings are merged with Reciprocal Rank Fusion. The optional cross-encoder reranker scores the candidates before the final passages are selected. Market-specific searches restrict candidates to that market.

Chat and comparison routes check the saved-answer cache before generating a new response. Cache keys incorporate request context, model configuration, a document version marker, market-data stamp, and retrieval mode. Successful model responses are saved and their usage is recorded. Document reloads clear saved answers.

The active retrieval pipeline uses NumPy, scikit-learn, and fastembed with on-disk embedding caches. Chroma settings and older container mounts remain in the repository, but Chroma is not the active retrieval engine. LangChain is used for document objects and text splitting.

## Local setup: FastAPI and React

Run these PowerShell commands from the project root. Use a Python version compatible with the pinned backend dependencies; Python 3.11 is a practical starting point. Node.js and npm are also required.

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` for your installation. Example settings:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
DATA_BASE_PATH=../data
EMBEDDING_PROVIDER=auto
RERANK_ENABLED=true
```

An OpenAI key is optional for local retrieval. Model-generated answers require an enabled LLM configuration; administrators can manage providers through the application. Local embeddings do not imply a locally hosted answer-generation model.

Start the backend from `backend/` so relative paths and `.env` resolve correctly:

```powershell
.\venv\Scripts\python.exe app.py
```

The first run creates an admin account. Its username defaults to `admin`. Set `ADMIN_PASSWORD` before the first run to choose its initial password; otherwise the backend prints a generated password once. Changing that environment variable later does not reset an existing account.

### Frontend

In a second terminal, from the project root:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for API requests. To override it, create `frontend/.env.local`:

```dotenv
VITE_API_URL=http://localhost:8000
```

| Service | Local URL |
|---|---|
| React application | http://localhost:5173 |
| FastAPI health check | http://localhost:8000/health |
| Interactive API documentation | http://localhost:8000/docs |

### Windows launch scripts

After dependencies and environments are installed, run from the project root:

```powershell
.\start.bat
```

Supported options:

- `all`: also starts Streamlit if its environment exists.
- `dev`: enables backend auto-reload.
- `nobrowser`: skips opening the browser.
- `dryrun`: displays launch actions without starting servers.

For example: `.\start.bat all nobrowser`.

`.\stop.bat` stops processes listening on ports 8000, 5173, and 8501 by default, and closes matching launcher processes. Check those ports before using it if other applications share them.

## Property data

Place documents in market folders:

```text
data/
|-- Dubai/
|   |-- research/
|   |-- regulation/
|   `-- datasets/
|-- Mumbai/
`-- London/
```

PDF, CSV, JSON, and TXT files are supported. Each immediate subfolder of `data/` defines a market; nested folders organize its documents. Market names are discovered from the data rather than hardcoded into the UI.

After adding or changing data, use the admin document reload action or restart the backend. Reloading also clears saved answers. Semantic indexing may continue in the background; check retrieval status for progress.

The Streamlit application needs access to the same documents. Its retrieval module reuses `backend/embeddings/` and `backend/models/` when present; otherwise it uses its own `.state` paths.

## Configuration and persistence

Backend defaults live in `backend/config.py` and can be overridden through `backend/.env`.

| Setting | Default / purpose |
|---|---|
| `DATA_BASE_PATH` | `../data`; market documents |
| `OPENAI_MODEL` | `gpt-4o-mini`; default environment-seeded provider model |
| `EMBEDDING_PROVIDER` | `auto`: OpenAI when a key is available, otherwise local |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `512` |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `RERANK_ENABLED` | `true` |
| `RERANK_MODEL` | `Xenova/ms-marco-MiniLM-L-6-v2` |
| `EMBEDDINGS_DIR` | `./embeddings`; cached vectors |
| `MODELS_DIR` | `./models`; downloaded local models |
| `DATA_STORE_PATH` | `./data_store.json`; users, sessions, provider settings, usage, answers |
| `MARKET_CACHE_PATH` | `./market_cache.json`; external market context |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` |
| `RETRIEVAL_K` | `5` |

`EMBEDDING_PROVIDER` also accepts `openai`, `local`, or `off`. Setting it to `off` disables semantic embeddings; reranking is controlled separately. Local models download on first use. Different providers/models use separate embedding caches.

Passwords are stored as salted hashes. Treat the application state file as sensitive: it also contains sessions and provider credentials. Do not commit `.env`, state files, or Streamlit secrets.

## API routes

The React application sends bearer tokens in the `Authorization` header. Most application routes require authentication; administrative routes require the admin role.

| Access | Method | Route | Purpose |
|---|---|---|---|
| Public | GET | `/`, `/health` | Service metadata and health |
| Public | POST | `/api/auth/login` | Create a login session |
| Token-based | POST | `/api/auth/logout` | Remove the supplied session |
| Signed in | GET | `/api/auth/me` | Current user and usage |
| Signed in | POST | `/api/auth/change-password` | Change password |
| Signed in | GET | `/api/llms` | Available models |
| Signed in | GET | `/api/system-stats` | Document statistics |
| Signed in | POST | `/api/chat` | Conversational research |
| Signed in | POST | `/api/compare-regions` | Compare a metric across markets |
| Admin | POST | `/api/reload-documents` | Reload documents and clear answers |
| Admin | GET, DELETE | `/api/admin/cache` | Inspect or clear saved answers |
| Admin | GET | `/api/admin/retrieval` | Retrieval/indexing status |
| Admin | GET | `/api/admin/market-data` | Market-data snapshot |
| Admin | POST | `/api/admin/market-data/refresh` | Refresh external data |
| Admin | GET, POST | `/api/admin/users` | List or create users |
| Admin | DELETE | `/api/admin/users/{username}` | Delete a user |
| Admin | POST | `/api/admin/users/{username}/password` | Reset a password |
| Admin | GET, POST | `/api/admin/llms` | List or create model configurations |
| Admin | PATCH, DELETE | `/api/admin/llms/{llm_id}` | Update or delete a configuration |
| Admin | POST | `/api/admin/llms/{llm_id}/test` | Test a model connection |

Example chat body:

```json
{
  "messages": [{"role": "user", "content": "Compare rental yields in Dubai and Mumbai"}],
  "user_profile": {"budget": 500000, "type": "individual", "risk_profile": "moderate"}
}
```

Example comparison body:

```json
{
  "metric": "rental yields",
  "regions": ["Dubai", "Mumbai"]
}
```

Both accept an optional `llm_id`. The older `/api/query` and `/api/investment-recommendation` endpoints are not present in the current API.

## Streamlit application

The standalone demo imports backend retrieval code rather than calling the FastAPI server. It has its own advisor workflow, Claude/OpenAI integration, SQLite answer cache, and calculator tools. It does not provide the React application's authentication/admin interface.

See [streamlit_app/README.md](streamlit_app/README.md) for environment setup, secrets, startup, tests, and deployment. Its default local URL is `http://localhost:8501`.

## Development checks

Frontend checks, from `frontend/`:

```powershell
npm run lint
npm run build
```

Streamlit advisor and calculator tests, from its configured environment in `streamlit_app/`:

```powershell
python -m pytest tests
```

These commands cover their respective areas; they are not a complete integration test of the running application.

## Prompt maintenance

The FastAPI application's prompt rules live in `backend/rag_system.py`: `BASE_RULES`, `CHAT_FORMAT`, and `COMPARE_FORMAT`. They describe context, constraints, structure, checkpoints, and review expectations. Profile, available-market, retrieved-document, and external-data blocks are assembled per request.

When changing prompt behavior, bump `CACHE_VERSION` in `backend/store.py` or clear saved answers so earlier responses are not reused. Streamlit has separate prompts in `streamlit_app/prompts.py` and its own saved-answer cache.

There is no automatic guarantee that every generated figure appears in the supplied evidence. Tax-rule verification and external market-data coverage depend on available sources.

## Containers

The repository includes backend/frontend Dockerfiles and `docker-compose.yml`. The Compose configuration still contains older model settings and Chroma mounts; review it before deployment. For a browser-based frontend, `VITE_API_URL` must be reachable from the browser, rather than using a container-only hostname such as `backend`.

Persist the current JSON state, market cache, embeddings, and model directories when configuring containers. The existing Chroma volume does not cover those paths. The Compose setup does not launch Streamlit.

## Further documentation

- [Frontend setup and styling](frontend/README.md)
- [Streamlit setup and architecture](streamlit_app/README.md)
- [Quick start](QUICKSTART.md)
- [VS Code setup](VSCODE_SETUP.md)
- [VS Code getting started](START_HERE_VSCODE.md)
- [Local mode guide](LOCAL_MODE_GUIDE.md)
- [Project summary](PROJECT_SUMMARY.md)

The supporting guides may retain older setup examples. Use the current source and this README when they differ.

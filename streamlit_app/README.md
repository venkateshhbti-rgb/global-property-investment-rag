# Property Investment Advisor (Streamlit app)

A chat app on top of the project's existing retrieval pipeline. It is the fastest route for an MVP or a demo. Move to the FastAPI + React app in the parent folder when you need real users, logins or billing.

| Layer | What it uses |
|---|---|
| Model | Claude (default when `ANTHROPIC_API_KEY` is set) or OpenAI |
| Workflow | question -> filter by country -> hybrid retrieval (keyword + semantic + reranker) -> live open data -> LLM writes the answer |
| Platform | the backend's retriever and embeddings, SQLite answer cache, keys in `.streamlit/secrets.toml` |
| Application | persona and country dropdowns, chat with source citations, yield calculator, disclaimer footer |

There is no Chroma here: the backend's own retriever already stores its embeddings on disk, and avoids Chroma's C++ build requirement on Windows.

## Files

| File | Job |
|---|---|
| `app.py` | entrypoint: sidebar (persona, country, model), navigation, disclaimer footer |
| `app_pages/chat.py` | the chat page with source citations |
| `app_pages/yield_calculator.py` | the yield calculator page |
| `advisor.py` | the question -> answer workflow (no Streamlit imports, so it is unit-tested) |
| `query.py` | `search(query, country, k)` returns `(text, metadata)` pairs |
| `prompts.py` | one Context / Constraints / Structure / Checkpoints / Review system prompt per persona |
| `tools.py` | `calc_yield()` and `mortgage_payment()`: all maths happens here, never in the LLM |
| `llm.py` | model choice (Claude or OpenAI) |
| `cache.py` | SQLite cache: a repeated question costs no tokens |
| `tests/` | unit tests: `test_tools.py` (calculator) and `test_advisor.py` (answer workflow and cache) |

## Run it

From the project root, in PowerShell:

```powershell
cd streamlit_app
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Put at least one key in `.streamlit/secrets.toml`, then:

```powershell
streamlit run app.py
```

The first start loads the documents and the search index and takes about a minute. If `backend/embeddings/` exists (built by the backend), the app reuses it.

Run the tests with `pytest tests` (27 tests: the calculator, the answer workflow and its cache).

Behaviour worth knowing:
- Changing the persona or country starts a fresh context for the model. Earlier replies written for another persona are not sent, because they would otherwise act as format examples and the new persona's layout would be ignored.
- Saved answers are keyed by persona, country, model, the question, and a fingerprint of the documents, live data and search mode. A repeated question costs no tokens. Use **Clear saved answers** after editing prompts.
- Only the Claude path is untested here (no Anthropic key was available); the OpenAI path is tested end to end.

## Making it trustworthy

- Each persona prompt says to answer only from the supplied context, otherwise "I don't have that in the documents".
- Every answer shows its sources with the file, page and the file's last-updated date. The documents carry no effective date, so the file date is the closest signal.
- Live figures (World Bank, BIS, exchange rates) are shown with their year.
- All yield and mortgage numbers come from `tools.py`.
- The footer carries the "informational only" disclaimer.

## Deploying (Streamlit Community Cloud)

1. The `data/` folder is gitignored because it holds third-party reports. On Cloud the app needs the documents, so either use a **private** repo that includes them, or add a download step in `query.py` that fetches them at startup.
2. Add the keys in the app's Secrets box (same format as `secrets.toml`).
3. The first start on Cloud has to embed the documents. Commit `backend/embeddings/*.npz` to the private repo to skip that.

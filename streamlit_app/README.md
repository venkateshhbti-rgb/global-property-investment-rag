# Property Investment Consultant (Streamlit app)

The same consultant as the FastAPI + React app, as a single Streamlit app that is easy to host. It runs the backend's engine in the same process, so answers, accounts, saved keys and token counts behave identically.

| You get | Where |
|---|---|
| Sign in and sign out, change password | login screen, sidebar |
| Token counter, model picker, investor profile (budget, type, risk) | sidebar |
| **Chat** with sources, clarifying-question forms and saved answers | Chat page |
| **Compare** markets on a metric | Compare page |
| **Yield calculator** (all maths done by code, never the AI) | Yield calculator page |
| **Status** (admins only): documents, search quality, live market data, AI models, users | Status page |

## Files

| File | Job |
|---|---|
| `app.py` | entrypoint: sign-in, sidebar, navigation, disclaimer footer |
| `app_pages/chat.py`, `compare.py`, `status.py`, `yield_calculator.py` | the pages |
| `services.py` | the chat and compare workflow (no Streamlit imports, so it is unit-tested) |
| `query.py` | points the backend's engine at this app's folders and loads it |
| `tools.py` | `calc_yield()` and `mortgage_payment()` |
| `ui.py` | small display helpers |
| `tests/` | unit tests for the calculator and the workflow |

## Run it locally

From the project root, in PowerShell:

```powershell
cd streamlit_app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Edit `.streamlit/secrets.toml` (an `OPENAI_API_KEY` and an `ADMIN_PASSWORD`), then:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Or double-click `start.bat all` in the project root. Sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

The first start loads the documents and the search index and takes about a minute. If `backend/embeddings/` exists, the app reuses it.

Run the tests with `.\.venv\Scripts\python.exe -m pytest tests`.

## Deploy on Streamlit Community Cloud

1. Push the repo, then create the app with `streamlit_app/app.py` as the main file.
2. Paste your secrets (same format as `secrets.toml.example`) into the app's **Secrets** box. At minimum: `OPENAI_API_KEY` and `ADMIN_PASSWORD`.
3. **Documents:** the `data/` folder is gitignored because it holds third-party reports, so a public deployment has nothing to search. The Chat page warns about this. Either deploy from a **private** repo that includes `data/` (and, to skip the long first indexing, `backend/embeddings/`), or add a small set of documents you are free to share.
4. **Privacy:** a Community Cloud app is public by default and uses your API key. Use the app's **Share** setting to restrict it to people you invite. The sign-in screen controls who can use the app, but only the Share setting stops strangers reaching the sign-in page.

### Limits on Streamlit Cloud

- **Storage is temporary.** Users, models and keys added in the Status page are lost when the app restarts or sleeps. Put what must last into the secrets: the admin account (`ADMIN_USERNAME`, `ADMIN_PASSWORD`), `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are recreated automatically on every start. Lasting user accounts would need an external database.
- **Reloading the page signs you out.** Sessions live in the browser tab.
- **Memory is limited**, so keep the document set modest.
- **Retired models:** an OpenAI provider on `gpt-3.5-turbo` is moved to `gpt-4o-mini` automatically on start.

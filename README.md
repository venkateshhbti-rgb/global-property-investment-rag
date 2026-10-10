# Property Investment RAG Consultant

A sophisticated AI-powered property investment consulting system using Retrieval-Augmented Generation (RAG) technology. This system serves three primary user groups:

- **Individual Property Investors** ($200K-$2M budget)
- **Independent Wealth Advisors** serving HNIs
- **Cross-border Relocation & Migration Consultancies**

## 🎯 Features

### Core Capabilities
- **Smart Chat Interface**: Ask property investment questions and get expert analysis
- **Regional Comparison Tool**: Compare metrics across Dubai, Mumbai, and other markets
- **Investment Advisor**: Personalized recommendations based on budget and risk profile
- **Real-time Analysis**: Access to property data, regulations, research reports, and market data
- **Multi-source Intelligence**: Aggregates PDFs, CSVs, APIs, and research documents

### Data Sources
- Property price datasets and transaction histories
- Rental yield information and market trends
- Regulatory documents (UAE Golden Visa, tax information)
- Research reports from leading real estate firms
- API specifications for property lookups

## Adding a New City or Country

Every folder directly inside `data/` is treated as one market, named after the folder.

```
data/
├── Dubai/
├── Mumbai/
├── London/        <- create a folder, drop in PDFs, CSVs, JSON or TXT files
└── Singapore/
```

Then open **Status** (admin) and click **Reload Documents**. The new market appears in the Compare tab, in the footer, and in the bot's list of available markets. Questions about a market with no folder get a "no data" reply instead of guessed figures.

## 🧭 Prompt Framework (CCSCR)

The consultant's prompts follow the **CCSCR** framework: **C**ontext, **C**onstraints, **S**tructure, **C**heckpoints, **R**eview. The prompt text lives in `backend/rag_system.py` (`BASE_RULES`, `CHAT_FORMAT`, `COMPARE_FORMAT` and the helper methods that build each request).

| Part | What it means here | Where it is | Status |
|---|---|---|---|
| **Context** | Role: global property investment analyst for three personas (individual investors $200K-$2M, wealth advisors serving HNIs, relocation firms). Each request carries the user's profile, the list of available markets, live macro/FX data and the retrieved document excerpts. | `BASE_RULES`, `_profile_block`, `_markets_block`, `_live_block`, `_context` | Implemented |
| **Constraints** | Use only the supplied context and live data. No personalized financial advice ("requires a licensed advisor review"). Ranges instead of false precision. Tax and regulatory points are "indicative only". Flag missing or thin data. Never move a live figure from one market to another. | `BASE_RULES` | Implemented |
| **Structure** | Full analysis in five parts (Market Context, Price Comparison, Rental Yield, Cost of Capital, Risk Flags) plus a Bottom line, about 200 words. Compare uses a shorter per-market format. Clarifying questions use a fixed `CLARIFY:` format that the UI turns into an answer form. | `CHAT_FORMAT`, `COMPARE_FORMAT`, `_parse_clarify` | Implemented |
| **Checkpoints** | Flag data older than 18 months (each live figure carries its year). Add a currency volatility warning when currencies differ, backed by the 12-month FX move. Don't ask for details already given (`_known_facts`, `_drop_known`). Market not in the data gets a "no data" reply. | `BASE_RULES`, `market_data.py`, `_known_facts`, `_drop_known` | Partly implemented |
| **Review** | Analytical, not salesy tone, with a "why it matters" for key metrics. Each answer lists its sources (documents and live APIs). | `BASE_RULES`, sources list in the chat UI | Partly implemented |

**Not implemented yet**
- Suggesting alternative cities when rental comparables are missing.
- Cross-checking recent tax-rule changes against an official source.
- Comparing answers against past advisor briefs in a knowledge base (add example briefs to `data/` to make them retrievable).
- An automatic check that every figure in an answer appears in the documents or live data.

If you change any prompt text, bump `CACHE_VERSION` in `backend/store.py` so saved answers written under the old rules are not reused.

## 🔎 Retrieval (Hybrid RAG)

Passages are found with **hybrid retrieval**, implemented in `backend/retriever.py`:

1. **Keyword search** (TF-IDF) and **semantic search** (embeddings) each return their best candidates.
2. The two rankings are merged with Reciprocal Rank Fusion.
3. A **cross-encoder reranker** re-scores the top candidates and keeps the best few.
4. If the question names a market, all of this runs inside that market's documents only.

Embeddings are built in the background and cached in `backend/embeddings/` by passage hash. The app works immediately with keyword search plus the reranker, improves when embedding finishes, resumes after an interruption, and only embeds new or changed documents on later runs. The **Status** tab (admin) shows progress.

| Setting in `backend/.env` | Meaning |
|---|---|
| `EMBEDDING_PROVIDER=auto` | Use OpenAI embeddings if an OpenAI key is configured, otherwise a local model (default) |
| `EMBEDDING_PROVIDER=openai` | Always OpenAI (`text-embedding-3-small`, 512 dimensions). Fast; roughly $0.10-0.15 for about 28,000 passages |
| `EMBEDDING_PROVIDER=local` | Local `bge-small` model via fastembed. Free and private, but slow on a laptop CPU (an hour or more for a large corpus) |
| `EMBEDDING_PROVIDER=off` | Keyword search only |
| `RERANK_ENABLED=false` | Skip the reranker (saves about a second per question) |

Local models download on first use into `backend/models/` (about 200 MB). Changing the embedding provider or model builds a separate cache; the old one is kept.

**Windows note:** `onnxruntime` must be imported before `scikit-learn`, otherwise Python crashes with a segmentation fault. `retriever.py` does this for you; keep that import at the top of the file.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard (Frontend)                │
│  - Chat Interface  - Comparison Tool  - Investment Advisor   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────▼────────────────────────────────┐
│              FastAPI Backend (Python)                        │
│  - Query Processing  - RAG Logic  - Document Management     │
└────────────────────────────┬────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
        ┌────────┐      ┌──────────┐    ┌──────────┐
        │ Chroma │      │ OpenAI   │    │ Property │
        │ DB     │      │ API      │    │ Data     │
        │ (Vecs) │      │ (LLM)    │    │ (PDFs)   │
        └────────┘      └──────────┘    └──────────┘
```

## 📋 Prerequisites

### System Requirements
- Python 3.9+
- Node.js 16+ and npm
- 4GB RAM minimum
- 2GB disk space for vector database

### API Keys & Credentials
1. **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com/api-keys)
   - Required for LLM and embeddings
   - Models used: `gpt-3.5-turbo` and `text-embedding-3-small`

## 🚀 Local Setup Instructions

### Step 1: Clone/Prepare Project

```bash
cd E:\Personal\AI\property-rag-chatbot
```

### Step 2: Backend Setup

#### Create Python Virtual Environment
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Configure Environment Variables
```bash
# Copy example to create .env file
copy .env.example .env

# Edit .env with your configuration
# Most importantly, add your OpenAI API key:
# OPENAI_API_KEY=sk-...
```

**Key Configuration Fields:**
```env
# Required
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small

# Data paths (relative to backend folder)

# RAG Settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_K=5
```

#### Start Backend Server
```bash
python app.py
# OR
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
Initializing RAG system...
Loading Dubai data from: ../data/Dubai
Loading Mumbai data from: ../data/Mumbai
Total documents loaded: 45
Documents split into 250 chunks
RAG System initialized successfully!

Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Frontend Setup

#### Install Dependencies
```bash
cd ../frontend
npm install
```

#### Create Environment File
```bash
# Copy example to create .env.local
copy .env.example .env.local
```

**Frontend Environment:**
```env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=Property Investment RAG Consultant
```

#### Start Development Server
```bash
npm run dev
```

**Expected Output:**
```
  VITE v5.0.0 ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### Step 4: Access the Application

Open your browser and navigate to:
```
http://localhost:5173
```

## 📊 Data Structure

Ensure your property data is organized as follows:

```
data/
├── Dubai/
│   ├── Dataset/
│   │   └── Dubai real estate transactions-2026.csv
│   ├── API/
│   │   └── SDGDLDEjariLookups_swagger.json
│   ├── regulation/
│   │   ├── UAE-Golden-Visa-By-Investment.pdf
│   │   └── *.pdf
│   ├── research/
│   │   ├── Colliers-Report.pdf
│   │   └── *.pdf
│   ├── tax/
│   │   └── *.pdf
│   └── faq/
│       └── *.txt
└── Mumbai/
    ├── archive/
    │   ├── locality_prices_monthly.csv
    │   ├── metro_stations.csv
    │   ├── rentals.csv
    │   ├── secondary_sales.csv
    │   └── under_construction.csv
    └── [other folders]
```

## 🎮 Using the Application

### 1. Chat with Consultant
- Ask any property investment question
- Set your investor profile (budget, type, risk preference)
- Get instant expert analysis with source citations

**Example Questions:**
- "What's the current price trend for 2-bedroom apartments in Dubai?"
- "Compare rental yields between Dubai and Mumbai"
- "What are the investment options for a $500K budget?"

### 2. Regional Comparison
- Select metrics: rental yields, prices, market growth, etc.
- Choose regions to compare
- Get detailed comparative analysis

**Supported Metrics:**
- Rental yields
- Property prices
- Market growth
- Affordability index
- Investment returns
- Transaction volume

### 3. Investment Recommendations
- Enter your budget ($200K - $2M+)
- Choose risk profile (conservative/moderate/aggressive)
- Select target regions
- Get personalized investment strategy

### 4. System Status
- View document statistics
- Monitor system health
- Reload documents after updates

## 🔧 Backend API Endpoints

### Chat & Queries
```bash
# Simple query
POST /api/query
{
  "question": "What are the best investment opportunities in Dubai for $500K?"
}

# Conversation with context
POST /api/chat
{
  "messages": [{"role": "user", "content": "..."}],
  "user_profile": {
    "budget": 500000,
    "type": "individual",
    "risk_profile": "moderate"
  }
}

# Regional comparison
POST /api/compare-regions
{
  "metric": "rental yields",
  "regions": ["Dubai", "Mumbai"]
}

# Investment recommendation
POST /api/investment-recommendation
{
  "budget": 500000,
  "risk_profile": "moderate",
  "target_regions": ["Dubai", "Mumbai"]
}
```

### System Management
```bash
# Get system stats
GET /api/system-stats

# Reload documents
POST /api/reload-documents

# Health check
GET /health
```

## 📈 Supported Use Cases

### For Individual Investors
- Market analysis and trend identification
- Property price comparisons
- ROI calculations
- Risk assessment

### For Wealth Advisors
- Client portfolio recommendations
- Multi-market analysis
- Risk-adjusted strategies
- Regulatory compliance guidance

### For Relocation Consultancies
- City-to-city property comparisons
- Cost of living vs. investment returns
- Immigration-friendly markets
- Currency and tax considerations

## 🛠️ Development Notes

### Adding New Property Data
1. Place data files in `data/<City or Country>/` folders
2. Supported formats: PDF, CSV, JSON, TXT
3. Restart backend or call `/api/reload-documents` endpoint

### Customizing RAG Behavior
Edit `backend/rag_system.py`:
```python
# Adjust chunk size for better context
CHUNK_SIZE=1000

# Change number of retrieved documents
RETRIEVAL_K=5

# Modify system prompt in _setup_qa_chain()
```

### Extending for New Regions
1. Create new folder: `data/NewCity/`
2. Add data files
3. Update config in `backend/config.py`:
```python
NEW_CITY_DATA_PATH = "../data/NewCity"
```
4. Modify document loader to include new region
5. Restart backend

## 🔐 Security Considerations

- Keep OpenAI API key in `.env` file (never commit)
- Use environment variables for all secrets
- Implement rate limiting in production
- Add authentication layer for enterprise use
- Sanitize user inputs before processing

## 📦 Production Deployment

### Backend Deployment (e.g., Heroku, AWS)
```bash
# Build for production
gunicorn app:app --workers 4

# Environment variables must be set on host
OPENAI_API_KEY=...
```

### Frontend Deployment (e.g., Vercel, Netlify)
```bash
npm run build
# Deploy the 'dist' folder
```

### Docker Deployment
```dockerfile
# Backend Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend .
CMD ["gunicorn", "app:app"]
```

## 🐛 Troubleshooting

### Backend Won't Start
```
Error: OPENAI_API_KEY not found
Solution: Check .env file and ensure OPENAI_API_KEY is set

Error: Documents not loading
Solution: Verify data/ folder structure and file permissions

Error: ModuleNotFoundError
Solution: Activate venv and reinstall: pip install -r requirements.txt
```

### Frontend Won't Load
```
Error: Cannot POST /api/query
Solution: Ensure backend is running on http://localhost:8000

Error: Blank page
Solution: Check browser console (F12) for errors, ensure npm run dev is running
```

### RAG System Not Working
```
Error: Vector store initialization failed
Solution: Delete chroma_db/ folder and restart (will rebuild)

Error: Low quality responses
Solution: Increase RETRIEVAL_K in config.py for more context documents
```

## 📚 Technology Stack

### Backend
- **FastAPI**: Modern async REST framework
- **LangChain**: RAG and LLM orchestration
- **Chroma**: Vector database
- **OpenAI**: LLM and embeddings
- **PyPDF2**: PDF processing
- **Pandas**: Data handling

### Frontend
- **React 18**: UI framework
- **Vite**: Fast build tool
- **Recharts**: Data visualization
- **Lucide Icons**: Icon library
- **Tailwind CSS**: Styling

## 📞 Support & Feedback

For issues or feature requests:
1. Check logs: Backend logs in terminal, frontend logs in browser console (F12)
2. Verify all prerequisites are installed
3. Ensure API keys are valid
4. Check internet connection for OpenAI API calls

## 📄 License

This project is part of a property investment analysis suite.

## 🎓 Learning Resources

- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Guide](https://platform.openai.com/docs)
- [React Documentation](https://react.dev)
- [Vite Guide](https://vitejs.dev)

---

**Last Updated**: October 2024
**Version**: 1.0.0

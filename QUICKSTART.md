# Quick Start Guide

Get the Property Investment RAG Consultant running in under 10 minutes.

## Prerequisites Checklist

- [ ] Python 3.9+ installed (`python --version`)
- [ ] Node.js 16+ installed (`node --version`)
- [ ] OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)
- [ ] Property data in `data/<City or Country>/` folders (one per market)

## 🚀 Start in 3 Steps

### Step 1: Backend (3 minutes)

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

Start server:
```bash
python app.py
```

✅ Should see: `RAG System initialized successfully!`

### Step 2: Frontend (2 minutes)

Open new terminal:
```bash
cd frontend
npm install
npm run dev
```

✅ Should see: `Local: http://localhost:5173/`

### Step 3: Use It!

Open browser → http://localhost:5173

Start asking questions:
- "What's the average property price in Dubai?"
- "Compare rental yields between Dubai and Mumbai"
- "What's the best investment for $500K budget?"

## Common Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\activate` |
| `Cannot POST /api/query` | Ensure backend is running on port 8000 |
| `OPENAI_API_KEY not found` | Add to `backend/.env` |
| `chroma_db` permission error | Delete folder, restart backend |

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Explore API endpoints at http://localhost:8000/docs
- Add custom property data to `data/` folder
- Deploy to production (see README)

## 📊 Test Query

Once running, try this in the Chat tab:

> "I have a $500K budget and moderate risk tolerance. What property investments would you recommend across Dubai and Mumbai?"

Expected: Detailed analysis with source citations in under 30 seconds.

---

**Stuck?** Check [README.md](README.md) Troubleshooting section or ensure all prerequisites are installed.

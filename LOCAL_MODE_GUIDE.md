# 🚀 LOCAL MODE GUIDE - No API Key Required!

This guide shows you how to run the entire Property Investment RAG system **locally** without any API keys.

## ✨ What is Local Mode?

**Local Mode** = The system works completely offline:
- ✅ No OpenAI API key needed
- ✅ No API calls, no costs
- ✅ Fast responses from local documents
- ✅ Perfect for development and testing
- ✅ Later add API key for AI-powered responses

## 📋 Prerequisites (Minimal)

Just these three things:
- Python 3.9+ ([python.org](https://www.python.org))
- Node.js 16+ ([nodejs.org](https://nodejs.org))
- VS Code ([code.visualstudio.com](https://code.visualstudio.com))

**That's it!** No OpenAI account needed initially.

## 🎯 VS Code Setup - 5 Minutes

### Step 1: Open Project in VS Code

```bash
# From PowerShell or Command Prompt
cd E:\Personal\AI\property-rag-chatbot
code .
```

Or use **File → Open Folder** in VS Code and select the project folder.

### Step 2: Create Python Environment (Backend)

**In VS Code:**

Press **Ctrl + `** to open terminal

Navigate to backend:
```bash
cd backend
```

Create virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

Should see `(venv)` prefix in terminal:
```
(venv) E:\...\backend>
```

### Step 3: Install Backend Packages

```bash
pip install -r requirements.txt
```

⏳ Wait 2-3 minutes for installation to complete

### Step 4: Create Configuration File

1. In VS Code Explorer, right-click **backend/.env.example**
2. Select **Copy**
3. Right-click in backend folder → **Paste**
4. Rename to **.env**
5. Open the `.env` file

It should look like:
```env
LOCAL_MODE=True
OPENAI_API_KEY=

# Rest of config...
```

**✨ Leave OPENAI_API_KEY empty!** That's the whole point.

Press **Ctrl+S** to save.

### Step 5: Start Backend

In terminal (still in backend folder with venv activated):
```bash
python app.py
```

You should see:
```
============================================================
Initializing Property Investment RAG System (LOCAL MODE)
============================================================
✓ Documents split into 250 chunks
✓ Organized documents by 2 regions
============================================================
✅ RAG System initialized successfully!
📝 Currently in LOCAL MODE (no API key required)
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **Backend is running!**

### Step 6: Start Frontend

**Press Ctrl+Shift+`** to open a **new** terminal

Navigate to frontend:
```bash
cd ..\frontend
npm install
npm run dev
```

You should see:
```
  VITE v5.0.0 ready in 123 ms

  ➜  Local:   http://localhost:5173/
```

✅ **Frontend is running!**

### Step 7: Open Dashboard

**Ctrl+Click** on `http://localhost:5173/` in terminal

Or open browser and go to: `http://localhost:5173`

You should see the **Property Investment Dashboard**! 🎉

## 🧪 Testing Local Mode

Try these in the **Chat Tab**:

### Test 1: Simple Query
```
"What property information do you have about Dubai?"
```

**Expected:** Response from your documents without API call

### Test 2: Comparison
Go to **Compare Tab**:
- Metric: "property prices"
- Regions: Dubai, Mumbai
- Click Compare

**Expected:** Local analysis

### Test 3: Investment Advisor
Go to **Advisor Tab**:
- Budget: 500000
- Risk: moderate
- Regions: Dubai, Mumbai

**Expected:** Personalized recommendation from documents

## 🔍 How Local Mode Works

### Local Search Process:
1. **User asks question** → Chat interface
2. **Find relevant documents** → Simple keyword search
3. **Generate response** → Based on document content
4. **Show sources** → Which documents were used

### Example:
```
Question: "Average property price in Dubai?"
  ↓
Search documents for "Dubai" and "price"
  ↓
Find matching chunks
  ↓
Summarize and present findings
  ↓
Show which PDFs/CSVs were used as sources
```

**All happens locally in ~2-3 seconds** ⚡

## 💻 How to Make Changes

### Change RAG Behavior:

Edit `backend/config.py`:
```python
CHUNK_SIZE=1500      # Larger pieces of text
RETRIEVAL_K=10       # More retrieved documents
```

Restart backend: **Ctrl+C** → `python app.py`

### Change Frontend:

Edit `frontend/src/components/ChatConsultant.jsx`

**Vite auto-reloads** - changes appear in browser instantly ✨

### Add New Data:

1. Place files in `data/<City or Country>/`
2. Go to System Status tab
3. Click "Reload Documents"
4. New data is indexed

## 🎓 Understanding Local Mode

### What Works in Local Mode:
- ✅ Chat with investment consultant
- ✅ Compare regions/metrics
- ✅ Investment recommendations
- ✅ Document search & retrieval
- ✅ Source citations
- ✅ Profile management

### What Needs API Key:
- ❌ Natural language understanding (AI)
- ❌ Vector embeddings for similarity search
- ❌ Advanced language generation

**But local mode still provides value!** It's perfect for:
- Development & testing
- Learning how RAG works
- Understanding your data
- Later upgrading to AI

## 🔑 Adding API Key Later

When you want AI-powered responses:

### Step 1: Get OpenAI API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign up (if needed)
3. Create new secret key
4. Copy the key

### Step 2: Update Configuration

In VS Code, edit `backend/.env`:

```env
LOCAL_MODE=False
OPENAI_API_KEY=sk-your-key-here-abc123xyz
OPENAI_MODEL=gpt-3.5-turbo
```

### Step 3: Restart Backend

In terminal:
```
Ctrl+C  (stop current backend)
python app.py  (restart)
```

You'll see:
```
Initializing OpenAI embeddings...
Initializing ChatOpenAI...
RAG System initialized successfully! (OPENAI MODE)
```

### Step 4: Test with AI

Same queries now use OpenAI for smarter responses! 🚀

## 🛠️ Troubleshooting Local Mode

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'langchain'`

**Fix:**
```bash
# Make sure venv is activated
.\venv\Scripts\activate

# Reinstall
pip install -r requirements.txt
```

### Port 8000 already in use

**Error:** `Port 8000 is already in use`

**Fix:**
```bash
# Kill the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Then restart
python app.py
```

### Frontend won't load

**Error:** `Cannot POST /api/query` in browser console

**Fix:** Make sure backend is running in the other terminal

### No documents found

**Error:** `Warning: No documents loaded`

**Fix:** Verify data in `data/<City or Country>/` folders (one per market)

## 📊 VS Code Workspace Layout

Perfect setup:

```
┌─────────────────────────────────────────────┐
│ VS CODE WINDOW                              │
├─────────────────────────────────────────────┤
│                                             │
│  EXPLORER (Left)        EDITOR (Center)    │
│  ├── backend/           app.py              │
│  ├── frontend/          (showing file)      │
│  ├── data/                                  │
│  └── README.md                              │
│                                             │
├─────────────────────────────────────────────┤
│ TERMINAL (Bottom)                           │
│                                             │
│ Tab 1: Backend         │  Tab 2: Frontend   │
│ (venv) ...backend>     │  ...frontend>      │
│ python app.py ✓        │  npm run dev ✓     │
│                                             │
└─────────────────────────────────────────────┘
```

## 🚀 Tips & Tricks

### Quick Commands
- **Ctrl+`** - Toggle terminal
- **Ctrl+J** - Toggle panel
- **Ctrl+K Ctrl+O** - Open folder
- **Ctrl+Shift+P** - Command palette
- **Ctrl+P** - Quick file open

### Fast Development
1. Make backend change → Auto-reloads (thanks to `--reload`)
2. Make frontend change → Auto-reloads (thanks to Vite)
3. No need to restart either!

### Test with Browser DevTools
- **F12** - Open browser DevTools
- **Console** - See any JS errors
- **Network** - See API calls
- **Application** - Check local storage

## 📚 File Structure Reference

```
property-rag-chatbot/
├── backend/
│   ├── .env ← Configuration (OPENAI_API_KEY empty)
│   ├── app.py ← API server
│   ├── rag_system.py ← Local search logic
│   ├── document_loader.py ← File reader
│   └── venv/ ← Virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   └── node_modules/
│
└── data/
    ├── Dubai/
    └── Mumbai/
```

## ✅ Validation Checklist

After setup, verify:

- [ ] Terminal 1 shows "RAG System initialized successfully!"
- [ ] Terminal 2 shows "Local: http://localhost:5173/"
- [ ] Dashboard loads without errors
- [ ] Chat tab works (try a query)
- [ ] System Status shows documents loaded
- [ ] No API key is configured yet

## 🎉 You're Done!

You now have a fully functional property investment RAG system running locally **without any API keys or costs**!

### Next Steps:
1. **Explore the system** - Try queries, compare regions, get recommendations
2. **Understand the flow** - Check how documents are loaded and searched
3. **Add more data** - Put new property files in `data/` and reload
4. **Learn RAG** - Open `backend/rag_system.py` to see how it works
5. **Add API key later** - When ready for AI-powered responses

---

**Questions?** Check [README.md](README.md) or [VSCODE_SETUP.md](VSCODE_SETUP.md)

**Happy coding!** 🚀


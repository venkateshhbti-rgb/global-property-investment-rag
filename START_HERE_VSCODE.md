# 🎯 START HERE - VS Code Local Setup (5 Minutes)

## What You Get

A fully functional **Property Investment RAG System** running locally with:
- ✅ No API keys needed
- ✅ No costs
- ✅ Real property data (Dubai, Mumbai)
- ✅ Interactive dashboard
- ✅ Instant local search

## ⚡ Quick Start (Copy & Paste)

### Terminal 1: Backend

```powershell
cd E:\Personal\AI\property-rag-chatbot\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Wait for:** `Uvicorn running on http://0.0.0.0:8000`

### Terminal 2: Frontend

Open **new PowerShell** (not tab in VS Code, a separate window):

```powershell
cd E:\Personal\AI\property-rag-chatbot\frontend
npm install
npm run dev
```

**Wait for:** `Local: http://localhost:5173/`

### Open in Browser

Ctrl+Click the link or go to: **http://localhost:5173**

---

## 🎓 Understanding What's Running

### Backend (Port 8000)
- **What:** Python server with RAG system
- **Status:** Running in first terminal
- **Mode:** LOCAL (no API key)
- **Job:** Search documents, return responses

### Frontend (Port 5173)
- **What:** React dashboard
- **Status:** Running in second terminal
- **Mode:** Development (auto-reload)
- **Job:** Display UI, send queries to backend

### Data
- **What:** Property documents (PDFs, CSVs)
- **Location:** `data/<City or Country>/` folders
- **Auto-loaded:** When backend starts

---

## 🧪 Try These Queries

### Chat Tab
```
"Tell me about property investment opportunities in Dubai"
```

### Compare Tab
1. Metric: `property prices`
2. Regions: Dubai, Mumbai
3. Click Compare

### Advisor Tab
1. Budget: `500000`
2. Risk: `moderate`
3. Regions: Dubai, Mumbai
4. Click "Get Recommendations"

### System Status Tab
- See how many documents loaded
- View document breakdown by region/type
- Click "Reload Documents" after adding new data

---

## 📂 Project Structure

```
E:\Personal\AI\property-rag-chatbot\
├── backend/               ← Python server
│   ├── app.py            ← REST API
│   ├── rag_system.py     ← Local search logic
│   ├── .env              ← Config (API key empty)
│   └── venv/             ← Virtual environment
│
├── frontend/             ← React dashboard
│   ├── src/
│   │   ├── App.jsx       ← Main app
│   │   └── components/   ← UI components
│   └── node_modules/
│
├── data/                 ← Property data
│   ├── Dubai/
│   └── Mumbai/
│
├── LOCAL_MODE_GUIDE.md   ← Detailed guide
├── VSCODE_SETUP.md       ← VS Code specific
└── README.md             ← Full documentation
```

---

## 🔧 How It Works (Simple Version)

```
You: "Tell me about Dubai"
    ↓
Frontend sends question to backend
    ↓
Backend searches documents for "Dubai"
    ↓
Backend finds matching chunks
    ↓
Backend sends response + sources
    ↓
Frontend displays answer
    ↓
Done! (All local, <3 seconds)
```

---

## 🎯 Common Next Steps

### Want to Modify UI?
1. Edit files in `frontend/src/`
2. Save (Ctrl+S)
3. Browser auto-refreshes ✨

### Want to Change RAG Behavior?
1. Edit `backend/config.py`
2. Ctrl+C to stop backend
3. Run `python app.py` again

### Want to Add New Data?
1. Add files to `data/<City or Country>/`
2. In System Status tab → Click "Reload Documents"

### Want AI-Powered Responses?
Later, when you have OpenAI API key:
1. Edit `backend/.env`
2. Add: `OPENAI_API_KEY=sk-your-key`
3. Restart backend
4. Same interface, AI-powered responses! 🚀

---

## ❓ Help & Troubleshooting

### Backend won't start
```bash
# Check Python installed
python --version

# Check venv activated (look for "(venv)" prefix)
# If not:
.\venv\Scripts\activate

# Check packages installed
pip list

# Reinstall if needed
pip install -r requirements.txt
```

### Frontend won't load
```bash
# Check Node installed
node --version

# Check npm packages installed
npm list

# Reinstall if needed
npm install
```

### "Cannot POST /api/query"
- **Cause:** Backend not running
- **Fix:** Start backend in first terminal

### Port already in use
```bash
# Port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Port 5173
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

---

## 📚 Full Documentation

- **[LOCAL_MODE_GUIDE.md](LOCAL_MODE_GUIDE.md)** - Detailed local setup
- **[VSCODE_SETUP.md](VSCODE_SETUP.md)** - VS Code-specific guide
- **[README.md](README.md)** - Complete technical docs

---

## ✅ Success Indicators

After setup, you should see:

**In Terminal 1 (Backend):**
```
============================================================
✓ Documents split into 250 chunks
✓ Organized documents by 2 regions
✅ RAG System initialized successfully!
📝 Currently in LOCAL MODE (no API key required)
INFO: Uvicorn running on http://0.0.0.0:8000
```

**In Terminal 2 (Frontend):**
```
  VITE v5.0.0 ready in 123 ms
  ➜  Local:   http://localhost:5173/
```

**In Browser:**
- Dashboard loads
- 4 tabs visible (Chat, Compare, Advisor, Status)
- Can type and send queries
- Get responses with sources

---

## 🚀 You're Ready!

Everything is set up and running locally. No API keys, no costs, full functionality.

**Try it now:**
1. Terminal 1: `python app.py` ✓
2. Terminal 2: `npm run dev` ✓
3. Browser: `http://localhost:5173` ✓
4. Ask a question! ✓

---

## 💡 Pro Tips

### For Quick Restarts
Keep both terminals side-by-side so you can see output from both

### For Development
- Backend: `Ctrl+C` restarts instantly
- Frontend: Auto-reloads on save

### For Testing
- Use System Status tab to verify documents loaded
- Check browser DevTools (F12) for API response details

### For Production Later
- Add API key when ready
- Use docker-compose for deployment
- See README.md for cloud options

---

**Next:** Open Terminal → Follow the **Quick Start** section above!


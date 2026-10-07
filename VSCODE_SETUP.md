# VS Code Setup Guide - Local Development (No API Key Required)

Get the RAG system running locally in VS Code in **5 minutes** without any API keys.

## 📋 Prerequisites

- VS Code installed
- Python 3.9+ 
- Node.js 16+
- Git (optional, but recommended)

## 🎯 Opening Project in VS Code

### Method 1: Open Folder
1. **File** → **Open Folder**
2. Navigate to: `E:\Personal\AI\property-rag-chatbot`
3. Click **Select Folder**

### Method 2: Command Line
```bash
cd E:\Personal\AI\property-rag-chatbot
code .
```

## 🔧 Setup in VS Code

### Step 1: Open Terminal in VS Code

**Ctrl + `** (backtick) to open integrated terminal

You should see:
```
E:\Personal\AI\property-rag-chatbot>
```

### Step 2: Create Python Virtual Environment

**In VS Code Terminal:**
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
```

You should see `(venv)` prefix in terminal:
```
(venv) E:\Personal\AI\property-rag-chatbot\backend>
```

### Step 3: Install Backend Dependencies

**Still in backend folder with venv activated:**
```bash
pip install -r requirements.txt
```

Wait for completion (~2-3 minutes)

### Step 4: Configure Backend for Local Mode

**In VS Code, open** `backend/.env.example`

Right-click → **Copy** → Paste in same folder → Rename to `.env`

**Edit** `backend/.env`:
```env
# OpenAI Configuration - LEAVE EMPTY FOR LOCAL MODE
OPENAI_API_KEY=

# Local Mode
LOCAL_MODE=True

# Data Paths

# Other settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_K=5
```

**Press Ctrl+S** to save

### Step 5: Start Backend

**In VS Code Terminal (backend folder):**
```bash
python app.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

✅ **Backend is running!**

### Step 6: Open New Terminal for Frontend

**Ctrl + Shift + `** (opens new terminal tab)

**Navigate to frontend:**
```bash
cd ..\frontend
npm install
```

Wait for completion (~1-2 minutes)

### Step 7: Start Frontend

**Still in frontend folder:**
```bash
npm run dev
```

You should see:
```
Local:   http://localhost:5173/
```

✅ **Frontend is running!**

## 🌐 Open Dashboard

**Ctrl + Click on** `http://localhost:5173/` in terminal, OR:

1. Open browser
2. Go to: `http://localhost:5173`

You should see the Property Investment Dashboard! 🎉

## 💻 VS Code Layout

Organize your workspace:

```
VS CODE
├── EXPLORER (Left Sidebar)
│   ├── backend/
│   │   ├── app.py ← Main server
│   │   ├── rag_system.py ← RAG logic (modify this)
│   │   ├── .env ← Local configuration
│   │   └── ...
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   └── components/
│   │   └── ...
│   └── data/
│       ├── Dubai/
│       └── Mumbai/
│
├── TERMINAL (Bottom)
│   ├── Backend: (venv) ... python app.py
│   └── Frontend: ... npm run dev
│
└── EDITOR (Center)
    └── Currently viewing file
```

## 🧪 Test Local Mode

### In Chat Tab:
Try asking:
```
"Tell me about Dubai property market"
```

**Expected Response (Local Mode):**
- Simple, mock responses without API calls
- Sources from loaded documents
- No waiting for OpenAI API

### Compare Tab:
```
Metric: "property prices"
Regions: Dubai, Mumbai
```

### Advisor Tab:
```
Budget: 500000
Risk: moderate
Regions: Dubai, Mumbai
```

## 📝 Debugging Tips in VS Code

### Useful VS Code Extensions
1. **Python** - IntelliSense, debugging, linting
2. **Pylance** - Better Python support
3. **REST Client** - Test API endpoints
4. **Thunder Client** - Alternative to Postman

### Python Debugging

**Set Breakpoint:**
1. Click line number in `backend/rag_system.py`
2. Red dot appears
3. Run: `python -m debugpy --listen 5678 app.py`

**Or use VS Code Python debugger:**
1. Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: App",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/app.py",
      "console": "integratedTerminal"
    }
  ]
}
```
2. Press **F5** to debug

### View Backend Logs
Terminal automatically shows all backend logs with timestamps

### Frontend Console
**Ctrl + Shift + J** in browser to see React errors/logs

## 🔗 Test API Endpoints

### Using Thunder Client (VS Code Extension)

1. **Install** "Thunder Client" extension
2. **Click Thunder Client icon** (left sidebar)
3. **New Request**

**Test Health Check:**
- Method: GET
- URL: `http://localhost:8000/health`
- Click **Send**

**Test Query (Local Mode):**
- Method: POST
- URL: `http://localhost:8000/api/query`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "question": "Tell me about Dubai property market"
}
```

## 🔄 Workflow - Making Changes

### Modify RAG Logic
1. Edit `backend/rag_system.py`
2. Backend auto-reloads (if using `--reload`)
3. Try query in UI - should see changes

### Modify UI
1. Edit `frontend/src/components/ChatConsultant.jsx`
2. Browser auto-reloads (Vite hot reload)
3. Changes appear instantly

### Test Data Changes
1. Add new file to `data/<City or Country>/`
2. In System Status tab → Click "Reload Documents"
3. New data indexed

## 🚨 Common VS Code Issues

| Issue | Solution |
|-------|----------|
| `Python not found` | Install Python from python.org, restart VS Code |
| `Module not found` | Activate venv: `.\venv\Scripts\activate` |
| `Port 8000 already in use` | Kill: `netstat -ano \| findstr :8000` then `taskkill /PID <PID> /F` |
| `npm ERR` | Delete `frontend/node_modules`, run `npm install` again |
| `ES6 import errors` | Right-click React file → "Select Python Interpreter" → choose `./venv` |

## 📊 Project Structure in VS Code

**Click** on files to navigate:
- `backend/app.py` - REST endpoints
- `backend/rag_system.py` - RAG & LLM logic
- `backend/document_loader.py` - File reading
- `frontend/src/App.jsx` - Main UI

**Modify** and save **(Ctrl+S)** - changes auto-reload!

## 🎯 Next: Add API Key Later

When ready to use OpenAI AI (instead of local mode):

1. **Get API Key:**
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy key

2. **Add to** `backend/.env`:
```env
OPENAI_API_KEY=sk-your-key-here
LOCAL_MODE=False
```

3. **Restart backend:**
   - Ctrl+C in terminal
   - Run `python app.py` again

4. **Test in UI** - now uses real OpenAI! 🚀

## 💡 Tips

- **Ctrl+`** - Toggle terminal
- **Ctrl+Shift+P** - Command palette (find anything)
- **Ctrl+P** - Quick file open
- **Ctrl+H** - Find & replace
- **Ctrl+Alt+L** - Format code
- **F5** - Debug (with launch.json)
- **Shift+Alt+F** - Format document

## 🧹 Cleaning Up

If you want to start fresh:

**In VS Code Terminal:**
```bash
# Clean backend
cd backend
rm -r venv
rm -r __pycache__
rm -r chroma_db

# Clean frontend
cd ..\frontend
rm -r node_modules
```

Then repeat **Steps 2-7** above.

---

## ✅ You're All Set!

You now have:
- ✅ Local RAG system running
- ✅ Full VS Code integration
- ✅ Auto-reloading backend & frontend
- ✅ Dashboard working on `http://localhost:5173`
- ✅ Ready to add API key when needed

**Troubleshooting?** Check the main [README.md](README.md) or [QUICKSTART.md](QUICKSTART.md)


# 🚀 AI-Powered Code Review Tool

An intelligent **AI-powered code review system** that combines **static analysis (AST)** with **Large Language Models (LLMs)** to detect bugs, bad practices, security risks, and missing edge cases in Python code.

This project provides **fast, structured, and contextual feedback** through a modern React frontend and a Flask backend.

---

## 📌 Features

### 🔍 Static Code Analysis (AST-Based)

* Python syntax error detection
* Unreachable code detection
* Undefined variable usage
* Unused imports and variables
* Inconsistent return statements
* Infinite loop detection
* Constant condition checks
* Bare `except` clause detection

### 🤖 AI-Powered Review (LLM Integration)

* Logic error analysis
* Security vulnerability scanning
* Performance optimization suggestions
* Edge-case detection
* Best-practice recommendations

Supports:

* **Anthropic Claude (recommended)**
* **OpenAI GPT**
* **Local models (Ollama)**

### 🎨 Interactive Frontend

* Code editor with syntax highlighting
* Issue categorization by severity
* Inline issue indicators
* Toggle AI analysis on/off
* Click-to-expand issue explanations

---

## 🏗 System Architecture

```
Frontend (React.js)  →  REST API  →  Backend (Flask)
                                 ├── AST Analyzer
                                 └── LLM Analysis Service
```

* **Frontend:** React (Port 3000)
* **Backend:** Flask (Port 5000)
* Communication via HTTP/JSON

---

## 🧰 Technology Stack

### Backend

* Python 3.8+
* Flask 3.0
* Python AST module
* Anthropic / OpenAI SDK
* Flask-CORS
* Flask-Limiter (rate limiting)

### Frontend

* React 18
* Tailwind CSS
* Lucide React Icons
* Fetch API

---

## 📂 Project Structure

```
code-review-tool/
├── backend/
│   ├── analyzers/
│   │   ├── ast_analyzer.py
│   │   └── llm_integration.py
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   └── App.css
│   ├── public/
│   │   └── index.html
│   └── package.json
├── README.md
├── SETUP.md
└── FOLDER_STRUCTURE.md
```

---

## ⚙️ API Endpoints

### 🔹 Analyze Code

**POST** `/api/analyze`

```json
{
  "code": "def foo():\n pass",
  "use_llm": true,
  "focus_areas": ["security", "performance"]
}
```

**Response**

```json
{
  "success": true,
  "analysis_time": 1.2,
  "summary": {
    "total_issues": 4,
    "errors": 2,
    "warnings": 1,
    "info": 1
  },
  "issues": [...]
}
```

---

### 🔹 Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "llm_available": true,
  "ast_available": true
}
```

---

## 🚀 Getting Started

### 1️⃣ Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Backend runs on: `http://localhost:5000`

---

### 2️⃣ Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs on: `http://localhost:3000`

---

## 🔐 Environment Variables

### Backend (`.env`)

```env
LLM_API_KEY=your_api_key_here
LLM_PROVIDER=anthropic
PORT=5000
CACHE_TTL=3600
```

### Frontend (`.env`)

```env
REACT_APP_API_URL=http://localhost:5000
```

---

## ⚡ Performance Optimizations

* AST + LLM parallel execution
* Result caching (1-hour TTL)
* Rate limiting (20 requests/min)
* Deduplication of AST & AI findings

---

## 🔒 Security Considerations

* No code execution (AST parsing only)
* Input size limit: 50KB
* API keys stored securely
* CORS controlled
* No stack traces exposed to users

---

## 🧪 Testing (Recommended)

* Unit tests for AST analyzer
* LLM response parsing tests
* Integration tests for full pipeline
* Manual UI testing checklist

---

## 📈 Future Enhancements

* Multi-language support (JS, Java, Go, Rust)
* IDE plugins (VS Code, PyCharm)
* CI/CD integration
* Auto-fix suggestions
* Code quality analytics dashboard

---

## ⚠️ Known Limitations

* Python only (currently)
* No runtime execution analysis
* LLM suggestions may have false positives
* 50KB code size limit per analysis

---

## 📜 License

This project is for **educational and academic use**.

---

## 👤 Author

**Aryan Pachouri**
IIT Delhi
Project Status: **Fully Functional & Deployment-Ready**

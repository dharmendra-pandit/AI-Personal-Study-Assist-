# Personal AI Study Assistant — End-to-End Process

Input → Processing → Intelligence → Output → Feedback Loop

User Input
↓
Data Processing (clean + chunk)
↓
Embeddings + Vector DB
↓
RAG Retrieval
↓
LLM (DeepSeek)
↓
Response (Notes / Quiz / Answer)
↓
Performance Tracking
↓
Personalized Plan
↓
Repeat 🔁

## Run

First time only (Python 3.10+):

```powershell
python -m venv myenv
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env    # then put your DeepSeek API key in .env
```

Every time:

```powershell
.\run.bat
```

`run.bat` uses `myenv` directly, so no activation is needed (double-clicking it works too).
To run Streamlit yourself instead, activate the environment first; a plain `streamlit run`
in a fresh terminal uses the global Python, which lacks the project's packages:

```powershell
.\myenv\Scripts\Activate.ps1
streamlit run app.py
```

The app opens at http://localhost:8501. The first start takes about a minute while torch and
the embedding model load (the model is downloaded once, then used from the local cache).
File watching is off (see `.streamlit/config.toml`), so restart the app after editing code.

`.env` settings: `API_KEY`, `BASE_URL` (e.g. `https://api.deepseek.com`), and optionally
`LLM_MODEL` (default `deepseek-chat`), `EMBEDDING_MODEL`, `DATA_DIR`.

## Layout

```
app.py          entry point (page + tabs)
ui/             one module per tab: chat, notes, quiz, progress, plan, sidebar
src/core/       config, text cleaning, chunking
src/db/         vector store (FAISS) and tracking (SQLite)
src/services/   embeddings, ingestion, retrieval, LLM calls, study workflows
data/           generated index + database (git-ignored)
```

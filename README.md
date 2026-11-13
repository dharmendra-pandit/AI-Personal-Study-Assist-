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

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Create a `.env` file with `API_KEY` and `BASE_URL` (e.g. `https://api.deepseek.com`).

## Layout

```
app.py          entry point (page + tabs)
ui/             one module per tab: chat, notes, quiz, progress, plan, sidebar
src/core/       config, text cleaning, chunking
src/db/         vector store (FAISS) and tracking (SQLite)
src/services/   embeddings, ingestion, retrieval, LLM calls, study workflows
data/           generated index + database (git-ignored)
```

# YT-Agent (public upload)

Safe copy of the project for GitHub: **no real API keys or `.env` files** are included. Use the example files and set secrets locally or in your host’s dashboard.

## Environment linking

### Backend (`backend/.env`)

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill `SUPABASE_URL`, `SUPABASE_ANON_KEY` (anon/public), and `SUPABASE_SERVICE_KEY` (service role — server only, never expose to the browser).
3. Add other keys (YouTube, OpenAI, Redis, etc.) as needed.

The backend reads **only** `backend/.env` from disk (same keys can be set via OS env on Render/Docker).

### Frontend (`frontend/.env`)

1. Copy `frontend/.env.example` to `frontend/.env`.
2. Set `VITE_API_URL` to your backend URL (e.g. `http://localhost:8000`).
3. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (**anon** key only — never commit the service role key here).

## Local run

**Backend**

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (Vite default).

## Docker

See `docker-compose.yml`. Provide `backend/.env` and build args / env for `VITE_*` as in that file.

## Security

- Rotate any keys that were ever pasted in chat or committed by mistake.
- Never push `backend/.env`, `frontend/.env`, or root `env` to Git.

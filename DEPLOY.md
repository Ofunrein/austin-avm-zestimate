# Deployment Guide

## HuggingFace Spaces (API)

1. Go to https://huggingface.co/new-space
2. Name: `austin-avm-api`, SDK: Docker, Visibility: Public
3. Connect GitHub repo `Ofunrein/avm-zestimate`, branch `main`
4. Add Space secret: `HF_REPO_ID=<your-hf-username>/austin-avm-model`
5. Space auto-deploys from `Dockerfile` at repo root

## HuggingFace Model Repo

After running training locally (`cd ml && .venv/bin/python run_training.py 50`):

```python
from huggingface_hub import HfApi
api = HfApi()
api.create_repo("austin-avm-model", repo_type="model", exist_ok=True)
api.upload_folder(folder_path="ml/models", repo_id="<your-hf-username>/austin-avm-model", repo_type="model")
```

## Vercel (Frontend)

```bash
cd web && npx vercel --prod
```

Set env vars in Vercel dashboard:
- `NEXT_PUBLIC_API_URL` = `https://<user>-austin-avm-api.hf.space`
- `NEXT_PUBLIC_SUPABASE_URL` = from Supabase dashboard
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` = from Supabase dashboard

## Supabase

Run `supabase/schema.sql` in the Supabase SQL Editor.

## GitHub Actions Secrets (for retrain workflow)

Add to repo Settings > Secrets:
- `KAGGLE_USERNAME` + `KAGGLE_KEY` (from kaggle.com/account)
- `HF_TOKEN` (from huggingface.co/settings/tokens)
- `HF_REPO_ID` (e.g. `youruser/austin-avm-model`)

## Training

```bash
# Install Kaggle creds: ~/.kaggle/kaggle.json
# {"username":"<your-kaggle-username>","key":"<your-api-key>"}

cd ml && .venv/bin/python run_training.py 50
# smoke test first: .venv/bin/python run_training.py 10
```

## Live URLs

- Frontend: https://austin-avm.vercel.app
- API: https://ofunrein-austin-avm-api.hf.space
- API docs: https://ofunrein-austin-avm-api.hf.space/docs
- HF model: https://huggingface.co/ofunrein/austin-avm-model
- HF Space: https://huggingface.co/spaces/ofunrein/austin-avm-api
- GitHub PR: https://github.com/Ofunrein/avm-zestimate/pull/1

## HF Space Architecture

Models embedded directly in Docker image (via `COPY ml/models/ ./ml/models/`).
No runtime download needed. Cold start ~30s.

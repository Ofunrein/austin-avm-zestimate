from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import predict, comps, benchmark, scan

app = FastAPI(
    title="Austin AVM API",
    description="Hyperlocal Automated Valuation Model for Austin TX",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router, tags=["prediction"])
app.include_router(comps.router, tags=["comps"])
app.include_router(benchmark.router, tags=["benchmark"])
app.include_router(scan.router, tags=["scan"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()[-2000:]},
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/debug")
def debug():
    import os, sys
    from pathlib import Path
    models_dir = Path(__file__).parent.parent / "ml/models"
    return {
        "cwd": os.getcwd(),
        "file": str(Path(__file__)),
        "models_dir": str(models_dir),
        "models_exist": models_dir.exists(),
        "model_files": sorted(str(f) for f in models_dir.glob("*")) if models_dir.exists() else [],
        "sys_path": sys.path[:5],
    }

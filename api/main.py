from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

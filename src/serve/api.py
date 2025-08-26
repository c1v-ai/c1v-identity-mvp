from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.models import MatchRequest, MatchResponse

app = FastAPI(
    title="C1V Identity API",
    version="0.0.1",
    description="Identity resolution API for matching customer records.",
    default_response_class=ORJSONResponse,
)

# Permissive CORS for local dev; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz", summary="Liveness probe")
def healthz():
    return {"status": "ok"}

def _naive_score(r1: dict, r2: dict) -> float:
    """Baseline: fraction of overlapping fields that match case-insensitively."""
    keys = set(r1) & set(r2)
    if not keys:
        return 0.0
    matches = sum(
        1
        for k in keys
        if str(r1.get(k, "")).strip().lower() == str(r2.get(k, "")).strip().lower()
    )
    return matches / len(keys)

@app.post(
    "/match",
    response_model=MatchResponse,
    summary="Match two records",
    description="Returns a boolean match decision with a confidence score in [0,1].",
    responses={
        200: {
            "description": "Match decision",
            "content": {
                "application/json": {
                    "example": {"match": True, "confidence": 0.97, "reason": "naive-baseline"}
                }
            },
        },
        400: {"description": "Bad request"},
    },
)
def match(req: MatchRequest) -> MatchResponse:
    try:
        score = _naive_score(req.record1, req.record2)
        is_match = score >= 0.7
        return MatchResponse(match=is_match, confidence=float(score), reason="naive-baseline")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

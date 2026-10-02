"""FastAPI application for the Review UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ont_core.config import APIConfig, DatabaseConfig
from ont_core.factory import RepositoryFactory, create_db_pool


class ExtractionResponse(BaseModel):
    """Extraction data for the review UI."""

    id: UUID
    observation_id: UUID
    status: str
    extraction_confidence: float
    behaviors: list | None = None
    breeding_evidence: dict | None = None
    habitat_features: list[str] | None = None
    life_stages: list[str] | None = None
    note_text: str
    common_name: str
    scientific_name: str
    validation_issues: list[dict] | None = None


class ExtractionListResponse(BaseModel):
    """Paginated list of extractions."""

    data: list[ExtractionResponse]
    meta: dict


class ReviewAction(BaseModel):
    """Request body for review actions."""

    action: Literal["approve", "reject"]
    notes: str | None = None


class AppState:
    """Application state holding repositories."""

    def __init__(self):
        self.db_pool = None
        self.repo_factory: RepositoryFactory | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_config = DatabaseConfig()
    state.db_pool = await create_db_pool(db_config)
    state.repo_factory = RepositoryFactory(state.db_pool)
    yield
    if state.db_pool:
        await state.db_pool.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    api_config = APIConfig()

    app = FastAPI(
        title="Observation Note Tagger API",
        version="0.1.0",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in api_config.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/extractions", response_model=ExtractionListResponse)
    async def list_extractions(
        status: str | None = Query(None, description="Filter by status"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        if not state.repo_factory:
            raise HTTPException(status_code=503, detail="Service not ready")

        extractions_repo = state.repo_factory.extractions()
        lineage_repo = state.repo_factory.lineage()

        rows, total = await extractions_repo.list_for_review(
            status=status, limit=limit, offset=offset
        )

        data = []
        for row in rows:
            validation_issues = await lineage_repo.get_validation_issues(row["id"])
            data.append(
                ExtractionResponse(
                    id=row["id"],
                    observation_id=row["observation_id"],
                    status=row["status"],
                    extraction_confidence=row["extraction_confidence"],
                    behaviors=row["behaviors"],
                    breeding_evidence=row["breeding_evidence"],
                    habitat_features=row["habitat_features"],
                    life_stages=row["life_stages"],
                    note_text=row["note_text"],
                    common_name=row["common_name"],
                    scientific_name=row["scientific_name"],
                    validation_issues=validation_issues,
                )
            )

        return ExtractionListResponse(
            data=data,
            meta={"total": total, "limit": limit, "offset": offset},
        )

    @app.post("/api/extractions/{extraction_id}/review")
    async def review_extraction(extraction_id: UUID, body: ReviewAction):
        if not state.repo_factory:
            raise HTTPException(status_code=503, detail="Service not ready")

        extractions_repo = state.repo_factory.extractions()
        new_status = "approved" if body.action == "approve" else "rejected"

        updated = await extractions_repo.update_status(
            extraction_id=extraction_id,
            status=new_status,
            reviewed_by="api",
            review_notes=body.notes,
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Extraction not found")

        return {
            "status": "ok",
            "extraction_id": str(extraction_id),
            "new_status": new_status,
        }

    @app.get("/api/stats")
    async def get_stats():
        if not state.repo_factory:
            raise HTTPException(status_code=503, detail="Service not ready")

        extractions_repo = state.repo_factory.extractions()
        observations_repo = state.repo_factory.observations()

        extraction_stats = await extractions_repo.count_by_status()
        observation_stats = await observations_repo.count_by_status()

        return {
            "extractions": extraction_stats,
            "observations": observation_stats,
        }

    return app


app = create_app()

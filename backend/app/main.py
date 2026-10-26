from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.router import router as admin_router
from app.analysis.coordinator import analysis_coordinator
from app.analysis.harness.executor import LangChainAnalysisRunner
from app.analysis.router import router as analysis_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import dispose_engine, init_database
from app.workspace.router import attachment_router, result_router
from app.workspace.router import router as workspace_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    analysis_coordinator.runner = LangChainAnalysisRunner()
    await analysis_coordinator.recover_stale_tasks()
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth_router)
    application.include_router(workspace_router)
    application.include_router(attachment_router)
    application.include_router(analysis_router)
    application.include_router(result_router)
    application.include_router(admin_router)

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "database": "sqlite",
            "llm_configured": settings.llm_configured,
        }

    return application


app = create_app()

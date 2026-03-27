from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.services.snowflake import db
from app.logging_conf import setup_logging, get_logger
from app.routers import companies, assessments, health, industries, config, signals, sec, evidence, metrics, testing, integration, rag, justify

# Setup logging
setup_logging()
logger = get_logger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def execute_sql_file(file_path: str, task_name: str):
        if not os.path.exists(file_path):
            logger.warning(f"{file_path} not found, skipping {task_name}.")
            return

        logger.info(f"Executing {task_name} from {file_path}...")
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            # Split by semicolon and filter out empty/whitespace statements
            raw_statements = [s.strip() for s in content.split(';') if s.strip()]
            statements = []
            
            for raw_stmt in raw_statements:
                # Remove comments from the statement to check if it's actually empty
                lines = raw_stmt.split('\n')
                clean_lines = [l for l in lines if not l.strip().startswith('--')]
                clean_stmt = '\n'.join(clean_lines).strip()
                
                if clean_stmt:
                    statements.append(clean_stmt)
            
            for i, stmt in enumerate(statements):
                try:
                    await db.execute(stmt)
                    logger.debug(f"Successfully executed statement {i+1} of {len(statements)}")
                except Exception as e:
                    logger.error(
                        f"Failed to execute statement {i+1} in {file_path}: {str(e)}\n"
                        f"SQL: {stmt[:200]}..."
                    )
                    # Raise error to stop startup if schema fails
                    if task_name == "schema initialization":
                        raise e

            logger.info(f"{task_name.capitalize()} completed successfully.")
        except Exception as e:
            logger.error(f"Critical error during {task_name}: {e}")
            if task_name == "schema initialization":
                 raise e

    # Startup logic
    logger.info("Starting up application...")
    import os
    
    try:
        # 1. Establish persistent Snowflake Connection
        await db.connect()
        logger.info("Connected to Snowflake successfully.")

        # 2. Run Schema Migrations
        await execute_sql_file("app/database/schema.sql", "schema initialization")
        await execute_sql_file("app/database/schema_sec.sql", "SEC schema initialization")
        await execute_sql_file("app/database/schema_signal.sql", "signals schema initialization")
        await execute_sql_file("app/database/schema_culture.sql", "culture schema initialization")

        # 3. Check for Seed Data
        try:
            count = await db.count_industries()
            
            if count == 0:
                logger.info("Industries table is empty. Auto-seeding...")
                await execute_sql_file("app/database/seed.sql", "data seeding")
            else:
                logger.info("Industries table already has data. Skipping seed.")
        except Exception as e:
            logger.error(f"Error checking industry count (might be schema issue): {e}")
            
    except Exception as e:
        logger.critical(f"APPLICATION STARTUP FAILED: {e}")
        pass
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await db.close()
    logger.info("Snowflake connection closed.")

app = FastAPI(
    title=settings.APP_NAME,
    description="""
# PE OrgAIR Platform
Intelligence-driven platform for assessing AI Maturity in Private Equity target companies.
    
## Features
* **External Intelligence**: Dynamically collect signals (jobs, patents, tech stack) from top web sources.
* **SEC Pipeline**: Automated download, parsing, and semantic chunking of SEC filings.
* **AI Maturity Assessment**: Structured framework for evaluating companies across 7 key dimensions.
* **Snowflake Integration**: High-performance data storage and enrichment.
    """,
    version=settings.APP_VERSION,
    contact={
        "name": "Advanced Agentic Coding Team",
        "url": "https://github.com/pe-org-air",
    },
    license_info={
        "name": "Proprietary",
    },
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(industries.router, prefix="/api/v1/industries", tags=["Industries"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(sec.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["External Signals"])
app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["Evidence"])
app.include_router(assessments.router, prefix="/api/v1", tags=["Assessments"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(testing.router, prefix="/api/v1/system", tags=["System Testing"])
app.include_router(integration.router, prefix="/api/v1", tags=["Integration"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(justify.router, prefix="/api/v1/rag", tags=["RAG"])
from app.routers import agent_ui, investments, observability
app.include_router(agent_ui.router, prefix="/api/v1")
app.include_router(investments.router, prefix="/api/v1/investments", tags=["Investment ROI"])
app.include_router(observability.router, prefix="/api/v1/observability", tags=["Observability"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}
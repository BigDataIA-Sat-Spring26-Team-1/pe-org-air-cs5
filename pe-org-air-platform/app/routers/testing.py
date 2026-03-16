from fastapi import APIRouter, HTTPException
import subprocess
import os
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

# Thread pool for running blocking subprocess calls
executor = ThreadPoolExecutor(max_workers=1)

def run_pytest():
    """Run pytest in a blocking subprocess (runs in thread pool)."""
    try:
        process = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        # Analyze the output to provide a summary
        output = process.stdout + process.stderr
        success = process.returncode == 0
        
        # Simple parsing for a summary
        lines = output.split('\n')
        summary = "No summary found"
        for line in reversed(lines):
            if "passed" in line or "failed" in line:
                summary = line.strip()
                break
        
        return {
            "status": "success" if success else "failed",
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "raw_output": output,
            "exit_code": process.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Tests timed out after 120 seconds",
            "raw_output": "Timeout exceeded while running tests."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "raw_output": f"Error running tests: {str(e)}"
        }

@router.post("/run-tests")
async def run_system_tests():
    """
    Triggers the internal test suite and returns the captured output.
    Runs pytest in a thread pool to avoid blocking the event loop.
    """
    try:
        # Run pytest in thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run_pytest)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

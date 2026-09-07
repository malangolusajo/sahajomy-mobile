"""
Scheduler for Intelligent Notifications in Logistics Intelligence Platform
"""

import asyncio
from datetime import datetime

from app.core.dependencies import get_customer
from app.database import get_db
from app.services.intelligent_notifications import run_intelligent_notifications
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/customer/notification-scheduler", tags=["Notification Scheduler"]
)

# Global flag to control the scheduler
scheduler_running = False


@router.post("/start")
def start_notification_scheduler(
    current_user: dict = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    Start the intelligent notification scheduler
    """
    if scheduler_running:
        return {"message": "Scheduler is already running"}

    # Run the scheduler in the background
    asyncio.create_task(run_scheduler(db))

    return {"message": "Started intelligent notification scheduler"}


@router.post("/stop")
def stop_notification_scheduler(current_user: dict = Depends(get_customer)):
    """
    Stop the intelligent notification scheduler
    """
    global scheduler_running
    scheduler_running = False

    return {"message": "Stopped intelligent notification scheduler"}


@router.get("/status")
def get_scheduler_status(current_user: dict = Depends(get_customer)):
    """
    Get the status of the notification scheduler
    """
    return {"running": scheduler_running}


@router.post("/run-now")
def run_scheduler_now(
    current_user: dict = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    Run the intelligent notification scheduler immediately
    """
    try:
        results = run_intelligent_notifications(db)
        return {"message": "Ran intelligent notifications now", "results": results}
    except Exception as e:
        return {"error": str(e)}


async def run_scheduler(db: Session):
    """
    Background task to run the scheduler periodically
    """
    global scheduler_running
    scheduler_running = True

    while scheduler_running:
        try:
            # Run the intelligent notifications
            results = run_intelligent_notifications(db)
            print(f"[{datetime.now()}] Ran intelligent notifications: {results}")

            # Wait for 1 hour before running again
            await asyncio.sleep(3600)  # 1 hour

        except Exception as e:
            print(f"Error in notification scheduler: {str(e)}")
            await asyncio.sleep(
                300
            )  # Wait 5 minutes before retrying if there's an error

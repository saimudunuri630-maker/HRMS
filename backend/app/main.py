from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.authentication_service.router import router as auth_router
from app.employee_service.router import router as employee_router
from app.attendance_service.router import router as attendance_router
from app.project_service.router import (
    router as project_router,
    roles_router as project_roles_router,
)
from app.dashboard_service.router import router as dashboard_router
from app.profile_service.router import router as profile_router
from app.leave_service.router import router as leave_router
from app.announcement_service.router import router as announcement_router
from app.work_report_service.router import router as work_report_router
from app.complaint_service.router import router as complaint_router
from app.notification_service.router import router as notification_router
from app.audit_service.router import router as audit_router

app = FastAPI(
    title="Mediatize HRMS API",
    description="Enterprise Human Resources Management System Backend",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication routes available at both /auth and /api/auth
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Services that already define their own internal prefixes (e.g., prefix="/api/employees")
app.include_router(employee_router)
app.include_router(attendance_router)
app.include_router(project_router)
app.include_router(project_roles_router)
app.include_router(project_router, prefix="/api", include_in_schema=False)
app.include_router(project_roles_router, prefix="/api", include_in_schema=False)
app.include_router(announcement_router)
app.include_router(work_report_router)
app.include_router(complaint_router)

# Dashboard summary and analytics routes
app.include_router(dashboard_router)

# Profile management routes (works for HR and Employees)
app.include_router(profile_router)

# Leave management domain routes (requests, types, balances)
app.include_router(leave_router)

# Notifications and Audit Logs routes
app.include_router(notification_router)
app.include_router(audit_router)


@app.get("/")
def root():
    return {
        "status": "online",
        "title": "Mediatize HRMS API",
        "system": "Mediatize HRMS Backend",
        "version": "2.0.0",
    }
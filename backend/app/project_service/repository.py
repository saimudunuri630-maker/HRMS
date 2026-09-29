from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.project_service.models import (
    Project,
    ProjectRole,
    ProjectEmployeeAssignment,
    ProjectStatus,
    AssignmentStatus,
)
from app.employee_service.models import Employee
from app.authentication_service.models import User


class ProjectRepository:
    @staticmethod
    def create(db: Session, project_data: dict) -> Project:
        project = Project(**project_data)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: int) -> Project | None:
        return db.query(Project).filter(Project.id == project_id).first()

    get_project_by_id = get_by_id

    @staticmethod
    def get_by_code(db: Session, project_code: str) -> Project | None:
        return (
            db.query(Project)
            .filter(func.lower(Project.project_code) == project_code.strip().lower())
            .first()
        )

    @staticmethod
    def list_projects(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        status: ProjectStatus | None = None,
        priority: ProjectPriority | None = None,
        employee_id: int | None = None,
    ):
        query = db.query(Project).filter(Project.deleted_at.is_(None))

        if employee_id is not None:
            # Filter projects where employee has an active assignment
            query = query.join(
                ProjectEmployeeAssignment,
                Project.id == ProjectEmployeeAssignment.project_id,
            ).filter(
                ProjectEmployeeAssignment.employee_id == employee_id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            ).distinct()

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Project.project_name.ilike(search_term),
                    Project.project_code.ilike(search_term),
                    Project.description.ilike(search_term),
                )
            )

        if status:
            query = query.filter(Project.status == status)

        if priority:
            query = query.filter(Project.priority == priority)

        total = query.count()
        items = (
            query.order_by(Project.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    @staticmethod
    def update(db: Session, project: Project, update_data: dict) -> Project:
        for key, value in update_data.items():
            if value is not None:
                setattr(project, key, value)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_active_team_member_count(db: Session, project_id: int) -> int:
        return (
            db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == project_id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .count()
        )

    # ========================================================
    # PROJECT ROLES REPOSITORY
    # ========================================================

    @staticmethod
    def add_role(db: Session, role_data: dict) -> ProjectRole:
        role = ProjectRole(**role_data)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> ProjectRole | None:
        return db.query(ProjectRole).filter(ProjectRole.id == role_id).first()

    @staticmethod
    def get_role_by_name(db: Session, project_id: int, role_name: str) -> ProjectRole | None:
        return (
            db.query(ProjectRole)
            .filter(
                ProjectRole.project_id == project_id,
                func.lower(ProjectRole.role_name) == role_name.strip().lower(),
            )
            .first()
        )

    @staticmethod
    def list_roles_by_project(db: Session, project_id: int) -> list[ProjectRole]:
        return (
            db.query(ProjectRole)
            .filter(ProjectRole.project_id == project_id)
            .order_by(ProjectRole.id.asc())
            .all()
        )

    @staticmethod
    def update_role(db: Session, role: ProjectRole, update_data: dict) -> ProjectRole:
        for key, value in update_data.items():
            if value is not None:
                setattr(role, key, value)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role: ProjectRole) -> None:
        # Set project_role_id = None on assignments using this role
        db.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_role_id == role.id
        ).update({"project_role_id": None})
        db.delete(role)
        db.commit()

    @staticmethod
    def get_assigned_count_for_role(db: Session, role_id: int) -> int:
        return (
            db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_role_id == role_id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .count()
        )

    # ========================================================
    # PROJECT ASSIGNMENTS / TEAM MEMBERS REPOSITORY
    # ========================================================

    @staticmethod
    def get_assignment_by_id(db: Session, assignment_id: int) -> ProjectEmployeeAssignment | None:
        return (
            db.query(ProjectEmployeeAssignment)
            .filter(ProjectEmployeeAssignment.id == assignment_id)
            .first()
        )

    @staticmethod
    def get_active_assignment(
        db: Session, project_id: int, employee_id: int
    ) -> ProjectEmployeeAssignment | None:
        return (
            db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == project_id,
                ProjectEmployeeAssignment.employee_id == employee_id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .first()
        )

    @staticmethod
    def get_any_assignment(
        db: Session, project_id: int, employee_id: int
    ) -> ProjectEmployeeAssignment | None:
        return (
            db.query(ProjectEmployeeAssignment)
            .filter(
                ProjectEmployeeAssignment.project_id == project_id,
                ProjectEmployeeAssignment.employee_id == employee_id,
            )
            .first()
        )

    @staticmethod
    def assign_employee(
        db: Session,
        project_id: int,
        employee_id: int,
        project_role_id: int | None,
        assigned_by: int,
        start_date: date | None = None,
    ) -> ProjectEmployeeAssignment:
        assignment = ProjectRepository.get_any_assignment(db, project_id, employee_id)
        if assignment:
            # Reactivate or update
            assignment.status = AssignmentStatus.ACTIVE
            assignment.project_role_id = project_role_id
            assignment.assigned_by = assigned_by
            assignment.start_date = start_date or date.today()
            assignment.end_date = None
            db.commit()
            db.refresh(assignment)
            return assignment

        assignment = ProjectEmployeeAssignment(
            project_id=project_id,
            project_role_id=project_role_id,
            employee_id=employee_id,
            assigned_by=assigned_by,
            start_date=start_date or date.today(),
            status=AssignmentStatus.ACTIVE,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def remove_employee(
        db: Session, assignment: ProjectEmployeeAssignment
    ) -> ProjectEmployeeAssignment:
        assignment.status = AssignmentStatus.TERMINATED
        assignment.end_date = date.today()
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def update_member_role(
        db: Session, assignment: ProjectEmployeeAssignment, project_role_id: int | None
    ) -> ProjectEmployeeAssignment:
        assignment.project_role_id = project_role_id
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def list_project_members(
        db: Session, project_id: int, active_only: bool = True
    ) -> list[ProjectEmployeeAssignment]:
        query = db.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_id == project_id
        )
        if active_only:
            query = query.filter(
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE
            )
        return query.order_by(ProjectEmployeeAssignment.id.asc()).all()

    @staticmethod
    def get_employee_assigned_projects(db: Session, employee_id: int):
        return (
            db.query(Project)
            .join(
                ProjectEmployeeAssignment,
                Project.id == ProjectEmployeeAssignment.project_id,
            )
            .filter(
                ProjectEmployeeAssignment.employee_id == employee_id,
                ProjectEmployeeAssignment.status == AssignmentStatus.ACTIVE,
            )
            .order_by(Project.id.desc())
            .all()
        )


get_project_by_id = ProjectRepository.get_by_id
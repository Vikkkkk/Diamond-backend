from typing import List, Union
from sqlalchemy.orm import Session
from models import get_db_instance, get_db
from fastapi import Depends, FastAPI, Request, HTTPException, status, Path
from fastapi.responses import JSONResponse
from utils.auth import verify_token, get_current_member
from models.member_role import MemberRole
from models.project_members import ProjectMembers
from models.roles import Roles
from models.members import Members
from models.projects import Projects
from loguru import logger
from typing import Callable


# Dependency Injection Implementation

def role_required(allowed_roles: List[str]):
    def role_required_dependency(
        current_member: Members = Depends(get_current_member), 
        db: Session = Depends(get_db_instance)
    ):
        try:
            print(allowed_roles)
            # Fetch roles for the current user
            member_roles = db.query(MemberRole).filter(MemberRole.member_id == current_member.id, MemberRole.active_role == True).all()
            role_ids = [role.role_id for role in member_roles]
            
            roles = db.query(Roles).filter(Roles.id.in_(role_ids)).all()
            user_roles = {role.name for role in roles}
            if not set(allowed_roles).intersection(user_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource"
                )
        except HTTPException as error:
            raise error
        except Exception as error:
            logger.exception(f"role_required:: error - {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            db.close()
    return role_required_dependency
            
        
    


def project_access_required() -> Callable:
    def project_access_dependency(
        project_id: str = Path(...),  # or Query(...)
        current_member: Members = Depends(get_current_member),
        db: Session = Depends(get_db_instance)
    ):
        try:
            # Check if the user has access to the project
            # is_valid = db.query(Projects).join(MemberRole).filter(
            #     Projects.id == project_id,
            #     Projects.is_deleted == False
            # ).first()

            # if not is_valid:
            #     raise HTTPException(
            #         status_code=status.HTTP_403_FORBIDDEN,
            #         detail="Invalid project ID"
            #     )
            # Check if the user is an admin
            admin_role = db.query(MemberRole).join(Roles).filter(
                MemberRole.member_id == current_member.id,
                Roles.name == 'Admin',
                MemberRole.active_role == True
            ).first()

            if admin_role:
                # If the current member is an admin, allow access
                return
            
            # Check if the user has access to the project
            has_access = db.query(ProjectMembers).join(MemberRole).filter(
                ProjectMembers.project_id == project_id,
                MemberRole.member_id == current_member.id,
                MemberRole.active_role == True
            ).first()

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this project resource"
                )
        except HTTPException as error:
            raise error
        except Exception as error:
            logger.exception(f"project_access_required:: error - {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            db.close()
    return project_access_dependency
    
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.sections import Sections
from schemas.project_schemas import Project
from schemas.project_details_schema import ProjectResponse, ProjectsResponse, ProjectModuleMemberResponse
from controller import section_controller
from loguru import logger
from utils.auth import verify_token
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/section", tags=["section APIs"])


@router.get("/get_sections", status_code=status.HTTP_200_OK)
@logger.catch
async def get_sections(
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Retrieve a list of sections.

    **Args:**
    - `verified_token` (bool): Boolean flag indicating whether the user's token is verified.
    - `db` (Database): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the list of sections or an error message.

    **Raises:**
    - `HTTPException`: Returns a 500 status code with an error message if an unexpected error occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await section_controller.get_sections(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


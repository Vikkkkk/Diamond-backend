from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from middleware.user_authorization_middleware import admin_required
from models import get_db
from models.members import Members
from controller import quotation_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from schemas.project_raw_material_schema import ProjectRawMaterial
from middleware.permission_middleware import role_required, project_access_required
from typing import List, Optional

router = APIRouter(prefix="/quotation", tags=["Quotation APIs"])


@router.put("/update_project_raw_material/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch 
async def update_project_raw_material(
    request_data: ProjectRawMaterial,
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    project_raw_material_id: str = Query(description="Project Raw material id"),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    try:
        return await quotation_controller.update_project_raw_material(db, project_id, project_raw_material_id, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/generate_quotation/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch 
async def generate_quotation(
    client_id: str = Query(description="client id"),
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    try:
        return await quotation_controller.generate_quotation(db, project_id, client_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.get("/{project_id}/get_project_quotations", status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project_quotations(
    project_id: str,
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    # verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Retrieves the current status of a project based on the specified project_id.

    Args:
    - project_id (str, optional): The ID of the project to retrieve the status for. 
                                  If not provided, the function will return an error response.
    - verified_token (bool, dependency): A dependency to verify the authentication token. 
                                         Required for access to this endpoint.
    - db (Session, dependency): A dependency to access the database session.

    Returns:
    - JSONResponse: A JSON response containing the current project status if the project is found, 
                    or an appropriate error message if the project is not in the database or other issues occur.

    Raises:
    - HTTPException: Raised if token verification fails or if an error occurs during the retrieval process.
    """
    try:
        # if not verified_token:
        #     return invalid_credential_resp
        return await quotation_controller.get_project_quotations(db, project_id, page, page_size)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
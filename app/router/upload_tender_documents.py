from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import project_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required

router = APIRouter(prefix="/upload", tags=["Project APIs"])

@router.post("/documents", status_code=status.HTTP_201_CREATED)
@logger.catch
async def upload_file(
    project_id: str = Form(...),
    file: List[UploadFile] = File(...),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for uploading documents for a project.

    **Args:**
    - `db` (Session): db session referance
    - `project_id` (str): Project Id, which will add along with the file data into the database
    - `file` (file): File, selected and uploaded in to the system for a specific project
    - `current_member` (Members): This will contain member details of current loggedin member.
    """
    try:
        return await project_controller.upload_tender_documents(db, project_id, file, current_member)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.delete("/delete_document/{document_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_document(
    document_id: str,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator"])),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for deleting a document from a project.

    **Args:**
    - `document_id` (str): Document ID of the file to be deleted.
    - `current_member` (Members): This will contain member details of current logged-in member.
    """
    try:
        return await project_controller.delete_tender_document(db, document_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
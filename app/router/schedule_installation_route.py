"""
This module containes all routes those are related to schedule installation  add/update/read/delete.
"""
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import transfer_opening_controller
from controller import schedule_installation_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from middleware.permission_middleware import role_required, project_access_required
from fastapi import APIRouter, Depends, UploadFile, Form, File
from schemas.schedule_installation_opening_schema import ScheduleInstallationMappingSchema, ScheduleInstallationCommentBase
from typing import Optional, List



router = APIRouter(prefix="/schedule_installation", tags=["Schedule Installation APIs"])


@router.get("/{project_id}/get_installation_openings", status_code=status.HTTP_200_OK)
@logger.catch
async def get_installation_openings(
    project_id = str,
    work_order_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Retrieve installation opening data for a specific project.

    This endpoint fetches all schedule installation mapping data (e.g., coordinate data, 
    status, related schedule data, and comments) for a given project ID.

    Args:
    - project_id (str): The unique identifier of the project whose installation openings are to be retrieved.
    - db (Session): SQLAlchemy session dependency for interacting with the database.

    Returns:
    - JSONResponse: A JSON object containing the installation mapping data and a success message,
      or an error message in case of failure.
    
    Raises:
    - HTTPException: If any error occurs during data retrieval.
    """
    try:
        return await schedule_installation_controller.get_installation_openings_data(db, project_id, work_order_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)
    


@router.get("/{project_id}/get_installation_unassigned_openings_info", status_code=status.HTTP_200_OK)
@logger.catch
async def get_installation_unassigned_openings_info(
    project_id = str,
    db: Session = Depends(get_db),
):
    """
    Retrieve installation Unassigned opening data for a specific project.

    This endpoint fetches all schedule installation mapping data (e.g., coordinate data, 
    status, related schedule data, and comments) for a given project ID.

    Args:
    - project_id (str): The unique identifier of the project whose installation openings are to be retrieved.
    - db (Session): SQLAlchemy session dependency for interacting with the database.

    Returns:
    - JSONResponse: A JSON object containing the installation mapping data and a success message,
      or an error message in case of failure.
    
    Raises:
    - HTTPException: If any error occurs during data retrieval.
    """
    try:
        return await schedule_installation_controller.get_installation_unassigned_openings_info(db, project_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)
    


@router.post("/{project_id}/upload_floor_plan")
async def upload_floor_plan(
    project_id: str,
    area: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_member: str = Depends(get_current_member)
):
    """
    Upload a floor plan document for a specific project and area.

    This endpoint allows a user to upload a floor plan file (e.g., PDF, image) associated 
    with a specific project and area. The uploaded file is saved and linked to the project's 
    installation plan.

    Args:
    - project_id (str): Unique identifier of the project.
    - area (str): Area/zone name the floor plan belongs to.
    - file (UploadFile): The floor plan file to be uploaded (PDF, JPG, etc.).
    - db (Session): SQLAlchemy session used for database interactions.
    - current_member (str): The ID of the authenticated user performing the upload.

    Returns:
    - JSONResponse: A success message with file metadata or an error message in case of failure.

    Raises:
    - HTTPException: If any error occurs during the upload or save operation.
    """
    try:
        return await schedule_installation_controller.upload_floor_plan_controller(
            db,
            project_id=project_id,
            area=area,
            current_member=current_member,
            file=file,
    )
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)
    


@router.get("/{project_id}/get_floor_plans", status_code=status.HTTP_200_OK)
@logger.catch
async def get_floor_plans(
    project_id = str,
    area: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Retrieve floor plans for a specific project and area.

    This endpoint returns the uploaded floor plan documents associated with a given project 
    and area. Useful for viewing previously uploaded architectural or installation plans.

    Args:
    - project_id (str): Unique identifier of the project.
    - area (str): The specific area (zone/section) for which the floor plan is required.
    - db (Session): SQLAlchemy database session dependency.

    Returns:
    - JSONResponse: A JSON object containing a list of floor plans or an error message.

    Raises:
    - HTTPException: If an internal error occurs during data retrieval.
    """
    try:
        return await schedule_installation_controller.get_floor_plans_data(db, project_id, area)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.post("/{project_id}/assign_opening_to_floor_plan", status_code=status.HTTP_201_CREATED)
async def assign_opening_to_floor_plan(
    project_id: str,
    request_data:ScheduleInstallationMappingSchema,
    db: Session = Depends(get_db),
    current_member: str = Depends(get_current_member)
):
    """
    Assign a schedule opening to a floor plan.

    This endpoint maps a schedule opening (like DOOR, FRAME, etc.) to a specific floor plan 
    document along with coordinate data. It saves the mapping to the database.

    Args:
    - project_id (str): Unique identifier of the project.
    - request_data (ScheduleInstallationMappingSchema): Input payload containing the mapping data.
    - db (Session): SQLAlchemy database session dependency.
    - current_member (str): The ID of the currently authenticated project member.

    Returns:
    - JSONResponse: A success message with the newly created mapping ID or an error message.

    Raises:
    - HTTPException: If an error occurs while saving the mapping.
    """
    try:
        return await schedule_installation_controller.assign_opening_to_floor_plan(
            db,
            project_id=project_id,
            request_data = request_data,
            current_member=current_member,
    )
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.delete("/{project_id}/remove_opening_from_floor_plan", status_code=status.HTTP_200_OK)
async def remove_opening_from_floor_plan(
    project_id: str,
    schedule_installation_mapping_id: str,
    db: Session = Depends(get_db),
    # current_member: str = Depends(get_current_member)
):
    """
    Remove an assigned opening from a floor plan.

    This endpoint deletes a specific schedule installation mapping using its ID. 
    It is used when a mapped opening (such as a door or frame) needs to be removed from the floor plan.

    Args:
    - project_id (str): Unique identifier of the project.
    - schedule_installation_mapping_id (str): The ID of the schedule installation mapping to be removed.
    - db (Session): SQLAlchemy database session dependency.
    - # current_member (str): (Optional) ID of the authenticated user. Uncomment if user auth is required.

    Returns:
    - JSONResponse: A success message or an error message.

    Raises:
    - HTTPException: If an error occurs during deletion.
    """
    try:
        return await schedule_installation_controller.delete_opening_from_floor_plan(
            db,
            schedule_installation_mapping_id = schedule_installation_mapping_id
    )
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.delete("/{project_id}/remove_all_opening_from_floor_plan", status_code=status.HTTP_200_OK)
async def remove_opening_from_floor_plan(
    project_id: str,
    schedule_installation_plan_doc_id: str = Query(...),
    deleted_schedule_ids: str = Query(..., description="Comma-separated list of opening IDs to delete openings"),
    db: Session = Depends(get_db),
    # current_member: str = Depends(get_current_member)
):
    try:
        return await schedule_installation_controller.delete_all_opening_from_floor_plan(
            db,
            schedule_installation_plan_doc_id=schedule_installation_plan_doc_id,
            deleted_schedule_ids=deleted_schedule_ids,
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)





@router.post("/{project_id}/add_comment", status_code=200)
async def add_comment(
    project_id: str,
    schedule_installation_mapping_id: str = Form(...),
    comment: str = Form(...),
    attachments: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Add a comment to a schedule installation mapping.

    This endpoint allows a project member to add a comment related to a specific schedule installation mapping.
    Useful for annotating mapping decisions, coordination notes, or progress updates.

    Args:
    - project_id (str): The ID of the project to which this mapping belongs.
    - db (Session): Database session dependency.
    - current_member: The currently authenticated member adding the comment.

    Returns:
    - JSONResponse: Contains the new comment ID and a success message.

    Raises:
    - HTTPException: Returns a 500 error if any exception occurs.
    """
    try:
        return await schedule_installation_controller.add_mapping_comment(db, project_id, schedule_installation_mapping_id, comment, attachments, current_member)
    except Exception as error:
        raise error
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.put("/{project_id}/update_comment/{comment_id}", status_code=200)
async def update_comment(
    project_id: str,
    comment_id: str,
    schedule_installation_mapping_id: str = Form(...),
    comment: str = Form(None),
    attachments: List[UploadFile] = File(None),
    deleted_attachment_ids: str = Form(None),
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Update an existing comment for a schedule installation mapping.

    This endpoint allows a project member to update a previously submitted comment associated
    with a specific schedule installation mapping.

    Args:
    - project_id (str): The ID of the project to which this comment belongs.
    - comment_id (str): The ID of the comment to update.
    - request_data (ScheduleInstallationCommentBase): The updated comment data.
    - db (Session): Database session dependency.

    Returns:
    - JSONResponse: A success message with the updated comment ID.

    Raises:
    - HTTPException: Returns a 500 error if the update fails due to internal server error.
    """
    try:
        return await schedule_installation_controller.update_mapping_comment(db, comment_id, schedule_installation_mapping_id, comment, attachments, project_id, deleted_attachment_ids, current_member)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.delete("/{project_id}/delete_mapping_comment/{comment_id}", status_code=200)
async def delete_mapping_comments(
    project_id: str,
    comment_id: str,
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Delete a specific comment from a schedule installation mapping.

    This endpoint allows deletion of a comment associated with a schedule installation mapping
    within a given project.

    Args:
    - project_id (str): The ID of the project from which the comment is to be deleted.
    - comment_id (str): The ID of the comment to delete.
    - db (Session): Database session dependency.

    Returns:
    - JSONResponse: A success message if the comment is deleted successfully.

    Raises:
    - HTTPException: Returns a 500 error if the deletion process fails.
    """
    try:
        return await schedule_installation_controller.delete_mapping_comments(db, comment_id, current_member)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.get("/{project_id}/get_schedule_installation_mapping_details/{mapping_id}", status_code=200)
async def get_schedule_installation_mapping_details(
    project_id: str,
    mapping_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed schedule installation mapping data including prep data and comments.

    This endpoint fetches a specific schedule installation mapping record along with its related
    preparation data and comments, ordered by comment creation date (descending).

    Args:
    - project_id (str): The ID of the project (used for route context, not directly in the query).
    - mapping_id (str): The ID of the schedule installation mapping to retrieve.
    - db (Session): SQLAlchemy database session.

    Returns:
    - JSONResponse: Contains the mapping data and a success message.

    Raises:
    - HTTPException: Returns a 500 error if data retrieval fails.
    """
    try:
        return await schedule_installation_controller.get_schedule_installation_mappings_info(db, mapping_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.put("/{project_id}/update_installation_prep_status", status_code=200)
async def update_installation_prep_status(
    project_id: str,
    status: str = Query(...),
    prep_id:str = Query(...),
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Update the status of a specific installation prep record.

    This endpoint updates the status field of a schedule installation prep record identified by the `prep_id`.

    Args:
        project_id (str): The ID of the project (used for context, not in query).
        status (str): The new status value to assign to the prep record.
        prep_id (str): The ID of the installation prep record to be updated.
        db (Session): SQLAlchemy database session dependency.

    Returns:
        JSONResponse: A 200 status code with a success message upon successful update.

    Raises:
        HTTPException: Returns a 500 status code with error details if the operation fails.
    """

    try:
        return await schedule_installation_controller.update_installation_prep_status(db, status, prep_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/{project_id}/get_schedule_installation_mappings", status_code=200)
async def get_schedule_installation_mappings(
    project_id: str,
    doc_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Retrieve schedule installation mappings for a specific floor plan document.

    This endpoint fetches all schedule installation mapping records associated with a given
    floor plan document (`doc_id`). These mappings typically include coordinate data, status,
    prep data, and related comments.

    Args:
        project_id (str): The ID of the project (used for context in routing, not for querying).
        doc_id (str): The ID of the installation plan document to retrieve mappings for.
        db (Session): SQLAlchemy database session dependency.

    Returns:
        JSONResponse: A 200 response containing mapping data and a success message.

    Raises:
        HTTPException: Returns a 500 status code with error details if data retrieval fails.
    """

    try:
        return await schedule_installation_controller.get_schedule_installation_mappings(db, doc_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.delete("/{project_id}/remove_floor_plan",status_code=status.HTTP_200_OK)
async def remove_floor_plan(
    project_id: str,
    doc_id: str = Query(...),
    db: Session = Depends(get_db)
):

    try:
        return await schedule_installation_controller.remove_floor_plan(db, doc_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)




@router.get("/{project_id}/schedule_installation_mapping_activities/{schedule_installation_mapping_id}")
async def schedule_installation_mapping_activities(
    project_id: str, 
    schedule_installation_mapping_id: str,
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
    ):
    try:

        return await schedule_installation_controller.get_schedule_installation_mapping_activities(db, schedule_installation_mapping_id, page, page_size)

    except Exception as error:
        logger.exception(f"Error fetching schedule installation mapping activities: {error}")
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.delete("/{project_id}/delete_mapping_comment_attachment/{attachment_id}", status_code=200)
async def delete_mapping_comment_attachment(
    project_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    API endpoint to delete a schedule installation mapping comment attachment.

    This route delegates the deletion logic to the controller method. It performs:
    - Removal of the file from the S3 bucket.
    - Deletion of the attachment record from the database.

    Args:
        project_id (str): The ID of the project to which the attachment belongs.
        attachment_id (str): The unique ID of the attachment to be deleted.
        db (Session): Database session dependency injected by FastAPI.
        current_member: The authenticated member performing the operation.

    Returns:
        JSONResponse: Success message upon successful deletion or error message if an exception occurs.
    """
    
    try:
        return await schedule_installation_controller.delete_mapping_comment_attachment(db, attachment_id, current_member)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)
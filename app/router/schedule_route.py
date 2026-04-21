from typing import List, Optional, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.schedules import Schedules
from models.members import Members
from models.opening_change_stats import OpeningChangeStats
from schemas.schedule_schemas import ScheduleResponse, ScheduleRequest,AdonOpeningFieldCreateSchema
from schemas.schedule_data_schema import ScheduleDataRequest, ScheduleDataBulkRequest, ScheduleDataBulkSaveSchema, ScheduleDataResponse
from schemas.adon_opening_fields_schema import AdonOpeningFieldResponseSchema, AdonOpeningFieldOpeningResponseSchema, OpeningFieldOpeningResponseSchema
# from schemas.project_details_schema import ProjectResponse, ProjectsResponse, ProjectModuleMemberResponse
from controller import schedule_controller
from loguru import logger
from utils.auth import verify_token
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required

router = APIRouter(prefix="/schedule", tags=["Schedule APIs"])


@router.get("/get_schedules/{project_id}", response_model=ScheduleResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_schedules(
    project_id: str, 
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])), 
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve schedules for a specific project.

    This endpoint fetches the schedules associated with a given project ID. The request requires a 
    verified token and, optionally, role-based access control can be implemented for certain roles.

    **Args**:
    - `project_id (str)`: The ID of the project for which schedules are to be fetched.
    - `verified_token (bool)`: Indicates whether the request token is verified (default: Depends on `verify_token`).
    - `db (Session)`: SQLAlchemy database session used to interact with the database.
    
    **Returns:**
    - `ScheduleResponse`: A response model containing the schedule data and status if successful.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_schedules(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.patch("/save_schedule/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def save_schedule(
    project_id: str,
    schedule: ScheduleRequest, 
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    
):
    """
    **Summary:**
    Create a new schedule for a specific project.

    This endpoint allows the creation of a new schedule entry for a given project. The request requires 
    the project ID and schedule data, along with the current member information. Role-based access control 
    can be implemented optionally based on the roles required.

    **Args:**
    - `project_id (str)`: The ID of the project for which the schedule is to be created.
    - `schedule (ScheduleRequest)`: The schedule data from the request body.
    - `current_member (Members)`: Information about the current member creating the schedule.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.

    **Returns:**
    - `dict`: A success message and relevant schedule information if the schedule is successfully created.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For any general exceptions during schedule creation.
    """

    try:
        return await schedule_controller.save_schedule(db, project_id, schedule, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/get_opening_fields", response_model=AdonOpeningFieldResponseSchema, status_code=status.HTTP_200_OK)
@logger.catch
async def get_opening_fields(
    opening_type: str = Query(title="Opening Type", description="Opening Type: DOOR/FRAME/HARDWARE/OPENING"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve opening fields for a specific opening type.

    This endpoint fetches the opening fields based on the specified opening type (e.g., DOOR, FRAME, or HARDWARE).
    The request requires a verified token for authentication. Optionally, role-based access control can be implemented
    to limit access to specific roles.

    **Args:**
    - `opening_type (str)`: The type of opening (DOOR, FRAME, HARDWARE) to filter the fields.
    - `verified_token (bool)`: Indicates whether the request token is verified (default: Depends on `verify_token`).
    - `db (Session)`: SQLAlchemy database session used to interact with the database.

    **Returns:**
    - `AdonOpeningFieldResponseSchema`: A response model containing the opening field data and status if successful.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_opening_fields(db, opening_type)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_field_options", status_code=status.HTTP_200_OK)
@logger.catch
async def get_field_options(
    manufacturer_code: Optional[str] = Query(title="Manufacturer Code", default=None),
    brand_code: Optional[str] = Query(title="Brand Code", default=None),
    field_name: str = Query(title="Field Name"),
    series_code: Optional[str] = Query(title="Series Code", default=None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve field options based on various filter criteria.

    This endpoint fetches the field options for a given field name, with optional filters for manufacturer code, 
    brand code, and series code. The request requires a verified token for authentication. Role-based access 
    control can be implemented optionally to limit access to specific roles.

    **Args:**
    - `manufacturer_code (Optional[str])`: The code for the manufacturer (default: None).
    - `brand_code (Optional[str])`: The code for the brand (default: None).
    - `field_name (str)`: The name of the field for which to retrieve options.
    - `series_code (Optional[str])`: The code for the series (default: None).
    - `verified_token (bool)`: Indicates whether the request token is verified (default: Depends on `verify_token`).
    - `db (Session)`: SQLAlchemy database session used to interact with the database.

    **Returns:**
    - `list`: A list of field options matching the provided criteria.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_feature_options(db, manufacturer_code, brand_code, field_name, series_code)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/add_opening_data", status_code=status.HTTP_200_OK)
@logger.catch
async def add_opening_data(
    # schedule_data: ScheduleDataBulkRequest, 
    schedule_data: ScheduleDataBulkSaveSchema,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    
):
    """
    **Summary:**
    Add or update opening data in the database.

    This endpoint adds new opening data or updates existing opening data if an ID is provided in the request. 
    The request requires the `schedule_data` to be provided as input, and the current member is inferred from 
    the authentication token. Optionally, role-based access control can be implemented to limit access to specific roles.

    **Args:**
    - `schedule_data (ScheduleDataBulkRequest)`: The schedule data to be added or updated.
    - `current_member (Members)`: The current member performing the action, inferred from the authentication token.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.

   **Returns:**
    - `dict`: A response containing the result of the add or update operation.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """

    try:
        return await schedule_controller.add_opening_data(db, schedule_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/upload_opening_file/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def upload_opening_file(
    schedule_id: str,
    file: UploadFile = File(...),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
    
):
    """
    **Summary:**
    Upload a file for a specific opening and update the corresponding schedule record.

    This endpoint allows the user to upload a file for a specific opening. The file is then uploaded to
    an S3 bucket, and the corresponding schedule record is updated with the file path and file type. 
    The `schedule_id` is used to identify the schedule in the database.

    **Args:**
    - `schedule_id (str)`: The ID of the opening to which the file will be uploaded.
    - `file (UploadFile)`: The file to be uploaded.
    - `current_member (Members)`: The current member performing the upload action, inferred from the authentication token.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.

    **Returns:**
    - `dict`: A response containing a success message and the file's path in S3.
    - `JSONResponse`: A JSON response with an error message if something goes wrong.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures, file-related errors, or database issues.
    """

    try:
        return await schedule_controller.upload_opening_file(db, schedule_id, file)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.delete("/delete_schedule/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_schedule(
    schedule_id: str,
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        if not verified_token:
            return invalid_credential_resp
        
        return await schedule_controller.delete_schedule(db, schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/schedule-data/{schedule_id}", response_model=ScheduleDataResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_schedule_data(
    schedule_id: str,
    part_number: Optional[str] = Query(title="Part Number", default=None),
    opening_type: str = Query(title="Opening Type", description="Opening Type: DOOR/FRAME/HARDWARE/OPENING"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """
    Fetch schedule data for a specific schedule based on the provided `schedule_id` and `opening_type`.

    **Path Parameters:**
    - `schedule_id` (str): The unique identifier for the schedule whose data is being retrieved.

    **Query Parameters:**
    - `opening_type` (str): Specifies the type of opening. Valid options include "DOOR", "FRAME", "HARDWARE", or "OPENING".

    **Dependencies:**
    - `verified_token` (bool): Ensures that the user has a valid token for accessing this resource.
    - `db` (Session): Provides the database session for querying the database.

    **Response:**
    - **200 OK**: Returns the schedule data in a structured format if the request is successful.
    - **401 Unauthorized**: Returns an invalid credential response if the token verification fails.
    - **500 Internal Server Error**: Returns an error message in case of any unexpected exceptions.

    **Usage Example:**
    `GET /schedule-data/{schedule_id}?opening_type=DOOR`
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_schedule_data(db, schedule_id, opening_type, part_number)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/get_opening_feature_fields", status_code=status.HTTP_200_OK)
@logger.catch
async def get_opening_feature_fields(
    opening_type: str = Query(title="Opening Type", description="Opening Type: DOOR/FRAME/HARDWARE/OPENING"),
    manufacturer_code: str = Query(title="Manufacturer code"),
    brand_code: Optional[str] = Query(title="Brand code", default=None),
    series_code: str = Query(title="Series code"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    # """
    # **Summary:**
    # Retrieve opening fields for a specific opening type.

    # This endpoint fetches the opening fields based on the specified opening type (e.g., DOOR, FRAME, or HARDWARE).
    # The request requires a verified token for authentication. Optionally, role-based access control can be implemented
    # to limit access to specific roles.

    # **Args:**
    # - `opening_type (str)`: The type of opening (DOOR, FRAME, HARDWARE) to filter the fields.
    # - `verified_token (bool)`: Indicates whether the request token is verified (default: Depends on `verify_token`).
    # - `db (Session)`: SQLAlchemy database session used to interact with the database.

    # **Returns:**
    # - `AdonOpeningFieldResponseSchema`: A response model containing the opening field data and status if successful.
    # - `JSONResponse`: A JSON response with an error message in case of an exception.

    # **Raises:**
    # - `HTTPException`: For authentication/authorization failures or database errors.
    # """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_opening_feature_fields(
            db,
            opening_type,
            manufacturer_code,
            brand_code,
            series_code
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/comparison_opening_stats/{schedule_id}",status_code=status.HTTP_200_OK)
@logger.catch
async def comparison_opening_stats(
    schedule_id: str,
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """
    Retrieve opening change statistics for a given schedule.

    **Path Parameters:**
    - `schedule_id` (str): The unique identifier of the schedule for which opening stats are requested.

    **Query Parameters:**
    *(Currently none, but `opening_type` can be added if needed in the future.)*

    **Dependencies:**
    - `verified_token` (bool): Validates the user's authentication token.
    - `db` (Session): Database session used for querying the relevant data.
    - *(Optional)* `role_required`: Uncomment to restrict access based on user roles.

    **Responses:**
    - **200 OK**: Successfully returns the comparison data related to the schedule.
    - **401 Unauthorized**: If token verification fails.
    - **500 Internal Server Error**: If an unexpected error occurs during processing.

    **Example:**
    `GET /comparison_opening_stats/123e4567-e89b-12d3-a456-426614174000`
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.get_comparison_opening_stats(db, schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/create_adon_opening_field", status_code=status.HTTP_201_CREATED)
@logger.catch
async def create_adon_opening_field(
    payload: AdonOpeningFieldCreateSchema,
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Create a new Adon Opening Field.

    **Body Parameters:**
    - `field_name` (str): Display name of the field
    - `field_desc` (str, optional): Description
    - `search_keywords` (str, optional): Search keywords
    - `field_type` (enum): Allowed values → NUMBER | TEXT | FILE_UPLOAD

    **Dependencies:**
    - `verified_token` (bool): User authentication check
    - `db` (Session): Database session

    **Responses:**
    - **201 Created**: Successfully created AdonOpeningField
    - **401 Unauthorized**: Invalid token
    - **500 Internal Server Error**: On failure
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await schedule_controller.create_adon_opening_field(db, payload)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



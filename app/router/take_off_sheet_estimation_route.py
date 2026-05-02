"""
This module containes all routes those are related to takeoff-sheet estimation add/update/read/delete.
"""

from datetime import date
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import raw_material_controller
from controller import take_off_sheet_estimation_controller
from controller import material_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.take_off_sheet_schemas import (
    TakeOffSheets,
    TakeOffSheetRequest,
    TakeOffSheetSectionAreaRequest,
)
from schemas.auth_schemas import invalid_credential_resp
from schemas.take_off_sheet_item_schema import TakeOffSheetItem
from schemas.take_off_sheet_estimation_schemas import EstimationBreakdown
from schemas.take_off_sheet_estimation_schemas import EstimationSurcharge
from schemas.take_off_sheet_estimation_schemas import EstimationDiscount
from schemas.materials_schema import (
    BatchProjectMaterialAssignRequest,
    CreateOpeningProjectMaterialRequest,
    ProjectMaterialRequest,
    ProjectMaterialAssignRequest,
    UpdateMaterialDescriptionRequest,
    UpdateDoorFrameMaterialSectionRequest,
)
from middleware.permission_middleware import role_required, project_access_required


router = APIRouter(
    prefix="/take_off_sheet/estimation", tags=["Take Off Sheet estimation APIs"]
)


@router.get("/raw_materials/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_project_raw_materials(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await raw_material_controller.get_project_raw_materials(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_all_raw_materials/{section_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_all_raw_materials(
    section_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await raw_material_controller.get_all_raw_materials(db, section_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_raw_materials", status_code=status.HTTP_200_OK)
@logger.catch
async def get_all_raw_materials(
    keyword: str = Query(description="keyword for raw material filter [door|frame]"),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await raw_material_controller.get_raw_materials(db, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_all_project_raw_materials/{project_id}", status_code=status.HTTP_200_OK
)
@logger.catch
async def get_all_project_raw_materials(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await raw_material_controller.get_all_project_raw_materials(
            db, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_raw_material_details", status_code=status.HTTP_200_OK)
@logger.catch
async def get_raw_material_details(
    keywords: str = None,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await raw_material_controller.get_raw_material_details(db, keywords)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_all_sections/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_all_sections(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Retrieve information about all sections in a project's take-off sheet.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `verified_token` (bool, optional): Token verification status.
            Defaults to Depends(verify_token).
    - `db` (Session, optional): The SQLAlchemy database session.
            Defaults to Depends(get_db).

    **Returns:**
    - `JSONResponse`: FastAPI JSONResponse object.
            - 'message' (str): Error message in case of an exception.
            - Status code 200: Successful response with data.
            - Status code 401: Unauthorized if token verification fails.
            - Status code 500: Internal Server Error for other exceptions.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_all_sections(
            db, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_opening_items_summary", status_code=status.HTTP_200_OK)
@logger.catch
async def get_opening_items_summary(
    project_id: str,
    project_take_off_sheet_section_area_item_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_opening_items_summary(
            db, project_id, project_take_off_sheet_section_area_item_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_openings_summary", status_code=status.HTTP_200_OK)
@logger.catch
async def get_openings_summary(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_openings_summary(
            db, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/set_estimation_breakdown", status_code=status.HTTP_200_OK)
@logger.catch
async def set_estimation_breakdown(
    project_id: str,
    request_data: EstimationBreakdown,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Set the estimation breakdown for a project.

    Args:
        project_id (str): The ID of the project.
        request_data (EstimationBreakdown): The estimation breakdown data.
        verified_token (bool, optional): Indicates if the token is verified. Defaults to Depends(verify_token).
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Returns:
        JSONResponse: The response containing the result of setting the estimation breakdown.

    Raises:
        Exception: If an error occurs while setting the estimation breakdown.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.set_estimation_breakdown(
            db, project_id, request_data
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/set_estimation_surcharge", status_code=status.HTTP_200_OK)
@logger.catch
async def set_estimation_surcharge(
    project_id: str,
    request_data: EstimationSurcharge,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Set estimation surcharge for a project.

    This function is used to set the estimation surcharge for a specific project. It takes the following parameters:

    - `project_id` (str): The ID of the project for which the estimation surcharge is being set.
    - `request_data` (EstimationSurcharge): The data containing the estimation surcharge information.
    - `verified_token` (bool, optional): A flag indicating whether the token is verified. Defaults to False.
    - `db` (Session, optional): The database session. Defaults to the session obtained from `get_db` dependency.

    The function returns the result of setting the estimation surcharge. If the token is not verified, it returns a response with an invalid credential message. If an exception occurs during the process, it returns a JSON response with an error message and a status code of 500.

    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.set_estimation_surcharge(
            db, project_id, request_data
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_estimation_breakdown", status_code=status.HTTP_200_OK)
@logger.catch
async def get_estimation_breakdown(
    project_id: str,
    tab_type: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    A function to get all sections with optional tab type, using project id and verified token, and returning estimation breakdown.
    Parameters:
        - project_id: str
        - tab_type: str
        - verified_token: bool
        - db: Session
    Returns:
        - JSONResponse
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_estimation_breakdown(
            db, project_id, tab_type
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_estimation_surcharge", status_code=status.HTTP_200_OK)
@logger.catch
async def get_estimation_surcharge(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Retrieves the estimation surcharge for a specific project.

    Parameters:
        - project_id (str): The ID of the project.
        - verified_token (bool, optional): Indicates whether the token is verified. Defaults to False.
        - db (Session, optional): The database session. Defaults to None.

    Returns:
        - JSONResponse: The response containing the estimation surcharge for the project. If the token is not verified, the response will contain an "invalid_credential" message. If an exception occurs, the response will contain an error message with a status code of 500.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_estimation_surcharge(
            db, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/{project_id}/discount/project_quote", status_code=status.HTTP_201_CREATED
)
@logger.catch
async def discount_project_quote(
    project_id: str,
    discount_quote_number: str = Form(None),
    file: List[UploadFile] = File(None),
    discount: str = Form(...),
    manufacturer_id: str = Form(...),
    brand_id: str = Form(None),
    raw_material_id: str = Form(...),
    discount_type: str = Form(...),
    expiry_date: Optional[Union[str, date]] = Form(None),
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Endpoint to discount a project quote.

    Args:
        project_id (str): Identifier of the project.
        discount_quote_number (str, optional): Quote number for the discount (if applicable).
        file (List[UploadFile], optional): List of uploaded files (if applicable).
        discount (str): Discount value.
        manufacturer_id (str): Identifier of the manufacturer.
        raw_material_id (str): Identifier of the raw material.
        discount_type (str): Type of discount.
        db (Session, optional): Database session object. Defaults to None.
        current_member (Members, optional): Current member performing the operation. Defaults to None.
    """
    discount_project_quote = {
        "discount": discount,
        "manufacturer_id": manufacturer_id,
        "brand_id": brand_id,
        "raw_material_id": raw_material_id,
        "discount_type": discount_type,
        "expiry_date": expiry_date,
    }
    if discount_quote_number is not None:
        discount_project_quote["discount_quote_number"] = discount_quote_number

    try:
        return await take_off_sheet_estimation_controller.discount_project_quote(
            db, discount_project_quote, file, project_id, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/discount/project_quote", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_discount_project_quote(
    request_data: EstimationDiscount,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Endpoint to discount a project quote.

    Args:
        reqest_data (EstimationDiscount): Discount project quote data removar info.
        db (Session, optional): Database session object. Defaults to None.
        current_member (Members, optional): Current member performing the operation. Defaults to None.
    """
    try:
        return await take_off_sheet_estimation_controller.delete_discount_project_quote(
            db, request_data, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/discount", status_code=status.HTTP_200_OK)
@logger.catch
async def get_project_discount(
    project_id: str,
    raw_material_id: str = Query(description="raw material id"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Endpoint to get project discount.

    Args:
        manufacturer_id (str): Identifier of the manufacturer.
        raw_material_id (str): Identifier of the raw material.
        db (Session, optional): Database session object. Defaults to None.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_project_discount(
            db, raw_material_id, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/{project_id}/material_type_wise_estimated_price", status_code=status.HTTP_200_OK
)
@logger.catch
async def material_type_wise_estimated_price(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.material_type_wise_estimated_price(
            db, project_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/{project_id}/get_take_off_sheet_section_area_info/{take_off_sheet_section_area_item_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def get_take_off_sheet_section_area_info(
    take_off_sheet_section_area_item_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Retrieve sections of a take-off sheet for a given section id.

    **Args:**
    - `section_id` (str): The unique identifier of the section.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the take-off sheet section area.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_estimation_controller.get_take_off_sheet_section_area_info(
            db, take_off_sheet_section_area_item_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/project_materials/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_project_materials(
    project_id: str,
    material_type: str = Query(
        ..., description="Material type: HARDWARE, FRAME, DOOR, or OTHER"
    ),
    keyword: str = Query(None, description="Optional keyword to search by short code"),
    raw_material_id: str = Query(None, description="Optional raw material id"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Get all project materials filtered by project ID and material type.

    **Args:**
    - `project_id` (str): The project ID.
    - `material_type` (str): Material type filter - HARDWARE, FRAME, DOOR, or OTHER.
    - `keyword` (str, optional): Keyword to filter by short code.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required`: Dependency to check user roles.
    - `project_access`: Dependency to verify project access.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the project materials list.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_materials(
            db, project_id, material_type, keyword, raw_material_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/add_hardware_material", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_hardware_material(
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Add a new hardware material to the project materials table.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing hardware material information including:
        - name, short_code, desc, series
        - material_type (should be HARDWARE)
        - base_feature, base_price, adon_feature, adon_price
        - total_amount
        - manufacturer_id, brand_id, project_id
        - hardware_product_category_id (optional)
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the created project_material_id.
      Status code 201 if successful, 500 if an exception occurs.
    """
    try:
        return await material_controller.create_project_material(
            request_data, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/add_door_frame_material", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_door_frame_material(
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Add a new door or frame material to the project materials table.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing door/frame material information including:
        - name, short_code, desc, series
        - material_type (DOOR or FRAME)
        - base_feature, base_price, adon_feature, adon_price
        - total_amount
        - manufacturer_id, brand_id, project_id
        - raw_material_id (optional)
        - adon_feature example:
            {
                "Closers": {
                    "Concealed Closer": {
                    "option": {
                        "desc": "Reinforcing for concealed or semi-concealed closer prep",
                        "optionCode": "Concealed Closer",
                        "availabilityCriteria": [
                        {
                            "seriesCode": "TRR-Series Doors"
                        },
                        {
                            "seriesCode": "D-Series"
                        },
                        {
                            "seriesCode": "Diamond Plus-Series"
                        }
                        ]
                    },
                    "quantity": 1
                    }
                }
            }
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the created project_material_id.
      Status code 201 if successful, 500 if an exception occurs.
    """
    try:
        return await material_controller.create_project_material(
            request_data, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/update_project_material/{material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_project_material(
    material_id: str,
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Update an existing project material (hardware, door, or frame).

    **Args:**
    - `material_id` (str): The ID of the project material to update.
    - `request_data` (ProjectMaterialRequest): The updated material information. Fields provided will be updated, unset fields remain unchanged.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and project_material_id.
      Status code 200 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await material_controller.update_project_material(
            material_id, request_data, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/delete_project_material/{material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_project_material(
    material_id: str,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Soft delete a project material (hardware, door, or frame).

    **Args:**
    - `material_id` (str): The ID of the project material to delete.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message.
      Status code 200 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await material_controller.delete_project_material(
            material_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/clone_project_material/{material_id}", status_code=status.HTTP_201_CREATED
)
@logger.catch
async def clone_project_material(
    material_id: str,
    short_code: str = Query(..., description="Short code for the cloned material"),
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Clone an existing project material to create a copy with a modified short_code.

    **Args:**
    - `material_id` (str): The ID of the project material to clone.
    - `short_code` (str): The short code for the cloned material. 
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the new project_material_id and original_material_id.
      Status code 201 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await material_controller.clone_project_material(
            material_id, short_code, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/assign_material_to_opening/{opening_id}", status_code=status.HTTP_201_CREATED
)
@logger.catch
async def assign_material_to_opening(
    opening_id: str,
    request_data: ProjectMaterialAssignRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Assign an existing project material to an opening (door/frame).

    **Args:**
    - `opening_id` (str): The project_take_off_sheet_section_area_item_id (opening) to assign the material to.
    - `request_data` (ProjectMaterialAssignRequest): Contains project_material_id and quantity.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and project_material_id.
      Status code 201 if successful, 404 if not found, 400 if already assigned, 500 if an exception occurs.
    """
    try:
        return await material_controller.assign_material_to_opening(
            request_data, opening_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/assign_hardware_to_group/{hardware_group_id}", status_code=status.HTTP_201_CREATED
)
@logger.catch
async def assign_hardware_to_group(
    hardware_group_id: str,
    request_data: ProjectMaterialAssignRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Assign an existing hardware material to a hardware group.

    **Args:**
    - `hardware_group_id` (str): The hardware_group_id to assign the material to.
    - `request_data` (ProjectMaterialAssignRequest): Contains project_material_id and quantity.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and project_material_id.
      Status code 201 if successful, 404 if not found, 400 if already assigned, 500 if an exception occurs.
    """
    try:
        return await material_controller.assign_hardware_material(
            request_data, hardware_group_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete(
    "/remove_material_from_opening/{opening_schedule_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def remove_material_from_opening(
    opening_schedule_id: str,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Remove a material assignment from an opening.

    **Args:**
    - `opening_schedule_id` (str): The ID of the opening schedule entry to remove.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message.
      Status code 200 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await material_controller.remove_material_from_opening(
            opening_schedule_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_unassigned_door_and_other_materials/{project_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def get_unassigned_door_and_other_materials(
    project_id: str,
    project_take_off_sheet_section_area_item_id: str = Query(
        ..., description="The project take off sheet section area item ID."
    ),
    material_type: str = Query(..., description="Material type: FRAME, DOOR, or OTHER"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Get all project materials filtered by project ID and material type.

    **Args:**
    - `project_id` (str): The project ID.
    - `project_take_off_sheet_section_area_item_id` (str): The project take off sheet section area item ID.
    - `material_type` (str): Material type filter - FRAME, DOOR, or OTHER.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required`: Dependency to check user roles.
    - `project_access`: Dependency to verify project access.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the project materials list.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_unassigned_door_and_other_materials(
            db, project_id, material_type, project_take_off_sheet_section_area_item_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_unassigned_door_and_other_materials_v2/{project_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def get_unassigned_door_and_other_materials_v2(
    project_id: str,
    project_take_off_sheet_section_area_item_id: str = Query(
        ..., description="The project take off sheet section area item ID."
    ),
    material_type: str = Query(..., description="Material type: FRAME, DOOR, or OTHER"),
    section_id: str = Query(..., description="The section ID."),
    project_take_off_sheet_section_id: str = Query(..., description="The project take off sheet section ID."),
    project_take_off_sheet_id: str = Query(..., description="The project take off sheet ID."),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Get all project materials filtered by project ID and material type.

    **Args:**
    - `project_id` (str): The project ID.
    - `project_take_off_sheet_section_area_item_id` (str): The project take off sheet section area item ID.
    - `material_type` (str): Material type filter - FRAME, DOOR, or OTHER.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required`: Dependency to check user roles.
    - `project_access`: Dependency to verify project access.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the project materials list.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_unassigned_door_and_other_materials_v2(
            db, project_id, material_type, project_take_off_sheet_section_area_item_id, section_id, project_take_off_sheet_section_id, project_take_off_sheet_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_unassigned_hardware_materials/{project_id}", status_code=status.HTTP_200_OK
)
@logger.catch
async def get_unassigned_hardware_materials(
    project_id: str,
    hardware_group_id: str = Query(..., description="The hardware group ID."),
    material_type: str = Query(..., description="Material type: HARDWARE"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Get all project materials filtered by project ID and material type.

    **Args:**
    - `project_id` (str): The project ID.
    - `hardware_group_id` (str): The hardware group ID.
    - `material_type` (str): Material type filter - HARDWARE.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required`: Dependency to check user roles.
    - `project_access`: Dependency to verify project access.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the project materials list.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_unassigned_hardware_materials(
            db, project_id, material_type, hardware_group_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_materials_details/{project_id}", status_code=status.HTTP_200_OK
)
@logger.catch
async def get_project_materials_details(
    project_id: str,
    opening_schedule_id: str = Query(..., description="Opening schedule id."),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Get materials details for a specific opening schedule.

    **Args:**
    - `project_id` (str): The project ID.
    - `opening_schedule_id` (str): The opening schedule ID.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required`: Dependency to check user roles.
    - `project_access`: Dependency to verify project access.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the materials details.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_materials_details(
            db, project_id, opening_schedule_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/create_opening_project_material/{project_id}", status_code=status.HTTP_200_OK
)
@logger.catch
async def create_opening_project_material(
    request_data: CreateOpeningProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    
    db: Session = Depends(get_db),
):
    """**Summary:**
    Add a new door or frame material to the project materials table.

    **Args:**
    - `request_data` (CreateOpeningProjectMaterialRequest): The request data containing door/frame material information including:
        - name, short_code, desc, series
        - material_type (DOOR or FRAME)
        - base_feature, base_price, adon_feature, adon_price
        - total_amount
        - manufacturer_id, brand_id, project_id
        - raw_material_id (optional)
        - opening_schedule_id (required)
        - adon_feature example:
            {
                "Closers": {
                    "Concealed Closer": {
                    "option": {
                        "desc": "Reinforcing for concealed or semi-concealed closer prep",
                        "optionCode": "Concealed Closer",
                        "availabilityCriteria": [
                        {
                            "seriesCode": "TRR-Series Doors"
                        },
                        {
                            "seriesCode": "D-Series"
                        },
                        {
                            "seriesCode": "Diamond Plus-Series"
                        }
                        ]
                    },
                    "quantity": 1
                    }
                }
            }
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the created project_material_id.
      Status code 201 if successful, 500 if an exception occurs.
    """

    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.create_opening_project_material(
            request_data, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

@router.put("/update_project_material_description/{material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_project_material_description(
    material_id: str,
    material_desc: UpdateMaterialDescriptionRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Update an existing project material description (hardware, door, or frame).

    **Args:**
    - `material_id` (str): The ID of the project material to update.
    - `description` (str): The updated material description.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and project_material_id.
      Status code 200 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await material_controller.update_material_desc(
            material_id, material_desc, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/get_door_frame_material_section/{project_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def get_door_frame_material_section(
    project_id: str,
    material_type: str = Query(..., description="Material type: DOOR, FRAME"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """List door frame raw material section rows for a project."""
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_door_frame_material_sections(
            db, project_id,material_type
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put(
    "/update_door_frame_material_section/{project_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def update_door_frame_material_section(
    project_id: str,
    door_frame_raw_material_section_request: UpdateDoorFrameMaterialSectionRequest,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """Update a door frame raw material section (raw material and/or material type)."""
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.update_door_frame_material_section(
            project_id, door_frame_raw_material_section_request, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_openings/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_openings(
    project_id: str,
    material_type: str = Query(..., description="Material type: DOOR, FRAME"),
    verified_token: bool = Depends(verify_token),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_openings(db, project_id, material_type)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/batch_assign_material_to_opening/{project_material_id}", status_code=status.HTTP_201_CREATED
)
@logger.catch
async def batch_assign_material_to_opening(
    project_material_id: str,
    request_data: BatchProjectMaterialAssignRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Assign an existing project material to an opening (door/frame).

    **Args:**
    - `project_material_id` (str): The project_material_id to assign the material to.
    - `request_data` (BatchProjectMaterialAssignRequest): Contains project_take_off_sheet_section_area_items_ids and quantity.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and project_material_id.
      Status code 201 if successful, 404 if not found, 400 if already assigned, 500 if an exception occurs.
    """
    try:
        return await material_controller.batch_assign_material_to_opening(
            request_data, project_material_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


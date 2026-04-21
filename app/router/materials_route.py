"""
This module containes all routes those are related to takeoff-sheet add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import material_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.materials_schema import ProjectMaterial, ProjectMaterialRequest, ProjectMaterialAssignRequest, RawMaterialMappingRequest
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/materials", tags=["Materials APIs"])

@router.get("/manufacturers", status_code=status.HTTP_200_OK)
@logger.catch
async def get_manufaturers(
    keyword: str = Query(None, alias="keyword"),
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    fetch all manufacturers based on additional filter.

    **Args:**
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the manufacturers.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        print(f"verified_token=={verified_token}")
        if not verified_token:
            return invalid_credential_resp
        # if keyword == "DOOR":
        #     keyword = "HMD"
        # if keyword == "FRAME":
        #     keyword = "HMF"
                
        return await material_controller.get_manufaturers(db, page, page_size, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

@router.get("/catalogs/{keyword}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_catalogs(
    keyword: str,
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    fetch all manufacturers based on additional filter.

    **Args:**
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the manufacturers.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        print(f"verified_token=={verified_token}")
        if not verified_token:
            return invalid_credential_resp
        # if keyword == "DOOR":
        #     keyword = "HMD"
        # if keyword == "FRAME":
        #     keyword = "HMF"
                
        return await material_controller.get_catalogs(db, page, page_size, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    
@router.get("/brands/{manufacturer_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_brands(
    manufacturer_id: str,
    keyword: str = Query(None, alias="keyword"),
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    fetch all brand based on manufacturers and additional filter.

    **Args:**
    - `manufacturer_id` (str): The ID of the manufacturer.
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - JSONResponse: A JSON response containing the brands.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        # if keyword == "DOOR":
        #     keyword = "HMD"
        # if keyword == "FRAME":
        #     keyword = "HMF"
        return await material_controller.get_brands(db, page, page_size, manufacturer_id, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/series", status_code=status.HTTP_200_OK)
@logger.catch
async def get_series(
    manufacturer_code: str = Query(None),
    brand_code: str = Query(None),
    category: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    fetch all series for the requested manufacturer and brand.

    **Args:**
    - `manufacturer_code` (str): The code of the manufacturer.
    - `brand_code` (str): The code of the brand.
    - `category` (str): The code of the category.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.

    **Returns:**
    - `JSONResponse`: A JSON response containing the series.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_series(db, manufacturer_code, brand_code, category)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/features", status_code=status.HTTP_200_OK)
@logger.catch
async def get_features(
    manufacturer_code: str = Query(None),
    brand_code: str = Query(None),
    series_code: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
):
    """**Summary:**
    fetch all features for the requested series.

    **Args:**
    - `manufacturer_code` (str): The code of the manufacturer.
    - `brand_code` (str): The code of the brand.
    - `series_code` (str): The code of the series.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.

    **Returns:**
    - `JSONResponse`: A JSON response containing all features.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_features(manufacturer_code, brand_code, series_code)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.get("/base_price", status_code=status.HTTP_200_OK)
@logger.catch
async def get_baseprice(
    req: Request,
    manufacturer_code: str = Query(None),
    brand_code: str = Query(None),
    series_code: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
):
    """**Summary:**
    fetch all features prices(base price) for the requested series.

    **Args:**
    - `req` (Request): request object to get the set if dynamic query params.
    - `manufacturer_code` (str): The code of the manufacturer.
    - `brand_code` (str): The code of the brand.
    - `series_code` (str): The code of the series.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.

    **Returns:**
    - `JSONResponse`: A JSON response containing all base prices.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        query_params = req.query_params._dict
        if "manufacturer_code" in query_params:
            del query_params["manufacturer_code"]
        if "brand_code" in query_params:
            del query_params["brand_code"]
        if "series_code" in query_params:
            del query_params["series_code"]
        return await material_controller.get_baseprice(query_params, manufacturer_code, brand_code, series_code)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/adon_features", status_code=status.HTTP_200_OK)
@logger.catch
async def get_adon_features(
    manufacturer_code: str = Query(None),
    brand_code: str = Query(None),
    series_code: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
):
    """**Summary:**
    fetch all adon-features for the requested series.

    **Args:**
    - `manufacturer_code` (str): The code of the manufacturer.
    - `brand_code` (str): The code of the brand.
    - `series_code` (str): The code of the series.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.

    **Returns:**
    - `JSONResponse`: A JSON response containing all adon-features.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_adon_features(manufacturer_code, brand_code, series_code)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/adon_price", status_code=status.HTTP_200_OK)
@logger.catch
async def get_adonprice(
    req: Request,
    manufacturer_code: str = Query(None),
    brand_code: str = Query(None),
    series_code: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
):
    """**Summary:**
    fetch all adon-features prices(adon price) for the requested series.

    **Args:**
    - `req` (Request): request object to get the set if dynamic query params.
    - `manufacturer_code` (str): The code of the manufacturer.
    - `brand_code` (str): The code of the brand.
    - `series_code` (str): The code of the series.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.

    **Returns:**
    - `JSONResponse`: A JSON response containing all adon-features prices.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        query_params = req.query_params._dict
        if "manufacturer_code" in query_params:
            del query_params["manufacturer_code"]
        if "brand_code" in query_params:
            del query_params["brand_code"]
        if "series_code" in query_params:
            del query_params["series_code"]
        return await material_controller.get_adonprice(query_params, manufacturer_code, brand_code, series_code)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/{project_id}/sync_project_material_price/{project_material_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def sync_project_material_price(
    project_material_id: str,
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Update an existing item in the take-off sheet section area.

    **Args:**
    - `project_material_id` (str): The ID of the project_material to be updated.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the result of the update operation.
            - 'message' (str): A message indicating the result of the operation.
            - 'status' (str): The status of the update operation ('success' or 'failure').

    **Raises:**
    - `HTTPException`: If an unexpected error occurs during the update process.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.sync_project_material_price(project_material_id, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/{project_id}/add_hardware/{hardware_group_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_hardware(
    hardware_group_id: str,
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add project material to the hardware group.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing information
      about the project material to be added to the hardware group.
    - `hardware_group_id` (str): The ID of the hardware group to which we need to add the hw material.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.add_hardware_material(request_data, hardware_group_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/{project_id}/update_hardware", status_code=status.HTTP_201_CREATED)
@logger.catch
async def update_hardware_material(
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    update hw material.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing information
      about the project material to be added to the hardware group.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.update_hardware_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.delete("/{project_id}/delete_hardware_material/{hardware_group_material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_hardware_material(
    hardware_group_material_id: str,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Endpoint to delete hardware material from the database.

    Args:
        hardware_group_material_id (str): The ID of the hardware group material to be deleted.
        `current_member` (Members): The current authenticated member making the request.
        db (Session, optional): SQLAlchemy database session. Defaults to Depends(get_db).

    Returns:
        JSONResponse: A JSON response indicating success or failure.
    """
    try:
        return await material_controller.delete_hardware_material(hardware_group_material_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/{project_id}/assign_hardware/{hardware_group_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def assign_hardware(
    hardware_group_id: str,
    request_data: ProjectMaterialAssignRequest,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add project material to the hardware group.

    **Args:**
    - `request_data` (ProjectMaterialAssignRequest): The request data containing information
      about the project material id and quantity to be added to the hardware group.
    - `hardware_group_id` (str): The ID of the hardware group to which we need to add the hw material.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.assign_hardware_material(request_data, hardware_group_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/add_project_material/{project_take_off_sheet_section_area_item_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_project_material(
    project_take_off_sheet_section_area_item_id: str,
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add project material to the opening.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing information
      about the project material to be added to the opening
    - `project_take_off_sheet_section_area_item_id` (str): The ID of the opening to which we need to add the material.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.add_material(request_data, project_take_off_sheet_section_area_item_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/{project_id}/update_project_material", status_code=status.HTTP_200_OK)
@logger.catch
async def update_project_material(
    request_data: ProjectMaterialRequest,
    current_member: Members = Depends(get_current_member),
    # role_required_ = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    update project material.

    **Args:**
    - `request_data` (ProjectMaterialRequest): The request data containing information
      about the project material to be updated.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.update_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.post("/{project_id}/clone_opening_material/{opening_schedule_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def clone_opening_material(
    opening_schedule_id: str,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This module is responsible for clonning  a opening schedule material for a project opening.

    **Args:**
    - `opening_schedule_id` (str): pening_schedule_id which we want to clone.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.clone_opening_material(opening_schedule_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/{project_id}/project_material/{project_material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_project_material(
    project_material_id: str,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    update project material.

    **Args:**
    - project_material_id (str): project material id which we need to delete.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await material_controller.delete_material(project_material_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/{project_id}/get_materials", status_code=status.HTTP_200_OK)
@logger.catch
async def get_materials(
    project_id: str,
    material_type: str = Query(None, alias="material_type"),
    keyword: str = Query(None, alias="keyword"),
    raw_material_id: str = Query(None, alias="raw_material_id"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving materials list depending on the input keyword and type

    This method fetches a subset of materials from the database based on the specified type and short code.

    **Args:**
    - `db`: The database session object.
    - `material_type` (str): material type we need.
    - `keyword` (str): this will be usefull for keyword search on short code.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await material_controller.get_materials(
            db, project_id, material_type, keyword, raw_material_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/add_manufacturer_material_mapping", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_manufacturer_material_mapping(
    request_data: RawMaterialMappingRequest,
    manufacturer_code:  str = Query(...),
    brand_code:str = Query(None),
    db: Session = Depends(get_db)
):
    try:
        return await material_controller.add_manufacturer_material_mapping(request_data, manufacturer_code, brand_code, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_manufacturer_material_mappings")
@logger.catch
async def get_manufacturer_material_mappings(
    manufacturer_code: str = Query(...),
    brand_code: str = Query(None),
    db: Session = Depends(get_db)
):
    try:
        return await material_controller.get_manufacturer_material_mappings(manufacturer_code, brand_code, db)
    except Exception as error:
        logger.exception("Error in route: get_manufacturer_material_mappings")
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/set_pricebook_available", status_code=status.HTTP_200_OK)
async def set_pricebook_available(
    manufacturer_code: str = Query(..., alias="manufactureCode"),
    brand_code: str = Query(None, alias="brandCode"),
    db: Session = Depends(get_db)
):
    try:
    
        return await material_controller.set_pricebook_available(manufacturer_code, brand_code, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_raw_materials", status_code=status.HTTP_200_OK)
async def get_raw_materials(
    db: Session = Depends(get_db)
):
    try:
        return await material_controller.list_raw_materials(db)
    except Exception as error:
        logger.exception("Error in route: get_raw_materials")
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_catalogs", status_code=status.HTTP_200_OK)
@logger.catch
async def get_catalogs(
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    # verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of active manufacturers along with their associated active brands.

    This endpoint supports optional pagination via `page` and `page_size` query parameters.
    
    - **page** (int, optional): Page number for paginated results.
    - **page_size** (int, optional): Number of records per page.
    - **verified_token** (bool): Authorization token dependency to secure the route.
    - **db** (Session): Database session dependency.

    Returns:
        JSON response containing:
        - A list of manufacturers with their active brands
        - Total item count
        - Page count
        - Success message
    """
    try:
        # if not verified_token:
        #     return invalid_credential_resp
                
        return await material_controller.get_catalogs_v2(db,page=page,page_size=page_size)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

    
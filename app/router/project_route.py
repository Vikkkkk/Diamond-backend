from typing import List, Union, Optional
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File, HTTPException
from starlette import status
from middleware.user_authorization_middleware import admin_required
from models import get_db
from models.members import Members
from schemas.project_schemas import Project
from schemas.project_details_schema import ProjectResponse, ProjectsResponse, ProjectModuleMemberResponse
from schemas.project_status_logs_schema import ProjectStatusLogs
from controller import project_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from schemas.project_member_schema import ProjectMembers
from middleware.permission_middleware import role_required, project_access_required
from schemas.project_schemas import ProjectListResponse, ProjectAssignResponse, MembersResponse, ProjectMemberRoleResponse
from datetime import datetime
from starlette import status as starlette_status

router = APIRouter(prefix="/project", tags=["Project APIs"])


@router.get("/get_projects", response_model=ProjectsResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_projects(
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    project_status: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'Pending', 'In Progress', 'Dropped'. 'Failed', 'Done'"),
    bid_status: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'Estimating', 'Await Bid', 'Sent'. 'Wait for approval', 'Bid Success', 'Bid Failed'"),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here,
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
    client_id: Optional[str] = None,
    module_type: str = Query(default=None, alias="module_type", description = "Options: 'Estimation' or 'Project Management'"),
    sort_by: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'name', 'quotation_due_date', 'priority', 'start_date', 'due_date'")

):
    """**Summary:**
    This method is responsible for retreaving paginated list of projects depending on the input range

    This method fetches a subset of projects from the database based on the specified
    page number and page size.

    **Args:**
    - `db`: The database session object.
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `keyword` (str): this will be usefull for keyword search on name and project_id.
    - `project_status` (str): this will be usefull for filter search.
    - `bid_status` (str): this will be usefull for filter search.
    - `current_member` (Members): This will contain member details of current loggedin member.
        Its being used by the admin required decorator.
    - `client_id` (str): this will filter the project list based on client
    - `module_type` (str) this will filter the project list based on module_type (Options: "Estimation", "Project Management")
    - `sort_by` (str) this will sort the list based on the requested order
    """
    try:
                                
        return await project_controller.get_projects(db, page, page_size, keyword, current_member, module_type, project_status, bid_status, client_id, sort_by)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_project", status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """**Summary:**
    This method is responsible for retreaving the details of the input project id

    **Args:**
    - `db` (Session): db session referance
    - `id` (String): project Id for which it will run the fetch query
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await project_controller.get_project(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/role/{role_id}/members", response_model=ProjectModuleMemberResponse, status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project_role_members(
    role_id: str,
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving the member list for a role id within a project

    **Args:**
    - `db` (Session): db session referance.
    - `id` (String): project Id for which it will return the members.
    - `role_id` (String): role Id for which it will return the members of a project.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not

    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await project_controller.get_project_role_members(db, project_id, role_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/insert_project", status_code=status.HTTP_201_CREATED)
@logger.catch
async def insert_project(
    name: str = Form(...),
    quotation_due_date: str = Form(...),
    street_address: str = Form(...),
    province: str = Form(...),
    country: str = Form(...),
    postal_code: str = Form(...),
    priority: str = Form(...),
    note: str = Form(None),
    client_ids: List[str] = Form(None),
    member_ids: List[str] = Form(None),
    file: List[UploadFile] = File(...),
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """**Summary:**
    Endpoint to insert a new project.

    **Args:**
    - `name` (str): Name of the project.
    - `quotation_due_date` (str): Due date for the project.
    - `street_address` (str): Street address of the project location.
    - `province` (str): Province of the project location.
    - `country` (str): Country of the project location.
    - `postal_code` (str): Postal code of the project location.
    - `note` (str, optional): Additional notes for the project.
    - `current_project_status` (str, optional): Current status of the project.
    - `current_bid_status` (str, optional): Current bid status of the project.
    - `is_active` (bool, optional): Flag indicating whether the project is active.
    - `client_ids` (str): Unique identifier for the client associated with the project.
    - `member_ids` (List[str]): List of unique identifiers for project members.
    - `file` (List[UploadFile]): List of file to be uploaded and associated with the project.
    - `db` (Session): Database session reference.
    - `current_member` (Members): This will contain member details of current loggedin member.

    **Returns:**
    - `JSONResponse`: A JSON response containing the success message or an error message if the operation fails.

    **Note:**
    - This endpoint uses the create_project function from the project_controller to handle the project creation process.
    - In case of an error during project creation, a 500 Internal Server Error response is returned with an error message.
    """
    
    project_data = {
        "name": name,
        "quotation_due_date": quotation_due_date,
        "street_address": street_address,
        "province": province,
        "country": country,
        "postal_code": postal_code,
        "note": note,
        "priority": priority,
        "client_ids": client_ids,
        "member_ids": member_ids,
    }
    try:
        return await project_controller.create_project(db, project_data, file, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
 
    
@router.delete("/{project_id}/delete_project", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_project(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """**Summary:**
    This method deletes a project from the DB based on the provided id.

    **Args:**
    - `id` (int): The unique identifier of the project to be deleted.
    - `current_member` (Members): This will contain member details of current loggedin member.
    - `db` (Session): DB session reference. Defaults to Depends(get_db).
    """
    try:
        # Delete the client
        return await project_controller.delete_project_soft(db, project_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/{project_id}/update_project", status_code=status.HTTP_200_OK)
@logger.catch
async def update_project(
    name: str = Form(None),
    project_code: str = Form(None),
    quotation_due_date: str = Form(None),
    street_address: str = Form(None),
    province: str = Form(None),
    country: str = Form(None),
    postal_code: str = Form(None),
    note: str = Form(None),
    priority: str = Form(None),
    client_ids: List[str] = Form(None),
    member_ids: List[str] = None,
    file: List[UploadFile] = File(default=None),
    removed_tender_docs: list[str] = None,
    project_id: str = Path(..., title="Project ID", description="The ID of the Project"),
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """**Summary:**
    Endpoint to insert a new project.

    **Args:**
    - `name` (str): Name of the project.
    - `quotation_due_date` (str): Due date for the project.
    - `street_address` (str): Street address of the project location.
    - `province` (str): Province of the project location.
    - `country` (str): Country of the project location.
    - `postal_code` (str): Postal code of the project location.
    - `note` (str, optional): Additional notes for the project.
    - `current_project_status` (str, optional): Current status of the project.
    - `current_bid_status` (str, optional): Current bid status of the project.
    - `is_active` (bool, optional): Flag indicating whether the project is active.
    - `client_ids` (str): Unique identifier for the client associated with the project.
    - `member_ids` (List[str]): List of unique identifiers for project members.
    - `file` (List[UploadFile]): List of file to be uploaded and associated with the project.
    - `removed_tender_docs` (List[str], optional): A list of tender document IDs to be removed from the project.
    - `db` (Session): Database session reference.
    - `current_member` (Members): This will contain member details of current loggedin member.

    **Returns:**
    - `JSONResponse`: A JSON response containing the success message or an error message if the operation fails.

    **Note:**
    - This endpoint uses the create_project function from the project_controller to handle the project creation process.
    - In case of an error during project creation, a 500 Internal Server Error response is returned with an error message.
    """
    
    project_data = {
        "project_code": project_code, 
        "name": name,
        "quotation_due_date": quotation_due_date,
        "street_address": street_address,
        "province": province,
        "country": country,
        "postal_code": postal_code,
        "note": note,
        "priority": priority,
        "client_ids": client_ids,
        "member_ids": member_ids,
    }
    # project_data = ProjectRequest(**project_data)

    try:
        return await project_controller.update_project(db, project_id, project_data, current_member, file, removed_tender_docs)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/download/{file_id}", status_code=status.HTTP_200_OK)
async def download_file(
        file_id: str = Path(..., description="The id of the file to download"),
        # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
        project_access = Depends(project_access_required()),
        db: Session = Depends(get_db)
    ):
    """**Summary:**
    Download File Endpoint

    Retrieves and downloads a file based on the provided file_id.

    **Args:**
    - `file_id` (str): The id of the file to download.
    - `verified_token` (bool, query parameter, dependency): Boolean flag indicating whether the user's token is verified.
    - `db` (Session, query parameter, dependency): Database session dependency.

   ** Returns:**
    - `200 OK`: Returns the file for download if successful.
    
    **Raises:**
    - `401` Unauthorized: If the token is not verified.
    - `404` Not Found: If the specified file_id does not exist.
    - `500` Internal Server Error: If an unexpected error occurs during the file download process.
    """

    try:
        # if not verified_token:
        #     return invalid_credential_resp
        return await project_controller.download_file(db, file_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_project_logs", status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project_logs(
    project_id: str = Path(..., title="Project ID", description="The ID of the Project"),
    category: str = Query(None, description="status category"),
    db: Session = Depends(get_db),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    verified_token: bool = Depends(verify_token)
):
    """
    Retrieves project/bid logs for a specified project.

    Parameters:
    - project_id (str): The ID of the project for which bid logs are to be retrieved.
    - category (str, optional): A category to filter bid logs. Defaults to None.
    - verified_token (bool, dependency): Dependency to verify the token.
    - db (Session, dependency): Dependency to get the database session.

    Returns:
    - JSONResponse: A JSON response containing the bid logs for the specified project.

    Raises:
    - HTTPException: If the token verification fails or any other exception occurs during the process.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await project_controller.get_project_logs(db, project_id, category)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.post("/{project_id}/insert_project_logs", status_code=status.HTTP_201_CREATED)
@logger.catch
async def insert_project_logs(
    request_data: ProjectStatusLogs,
    project_id: str = Path(..., title="Project ID", description="The ID of the Project"),
    # role_required = Depends(role_required(["Admin", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    try:
        return await project_controller.insert_project_logs(db, current_member, project_id, request_data.status_id, request_data.status_type, data_return=True)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_project_status", status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project_status(
    category: str = Query(None, description="status category"),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db),
    # role_required = Depends(role_required(["Admin", "Estimator"]))  # Specify allowed roles here
):
    """
    Retrieves the bid status of projects based on the specified category.

    Parameters:
    - category (str, optional): A category to filter project bid statuses. Defaults to None.
    - verified_token (bool, dependency): Dependency to verify the token.
    - db (Session, dependency): Dependency to get the database session.

    Returns:
    - JSONResponse: A JSON response containing the bid status of projects based on the specified category.

    Raises:
    - HTTPException: If the token verification fails or any other exception occurs during the process.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await project_controller.get_project_status(db, category)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/list_open_projects")
async def list_open_projects(
    db: Session = Depends(get_db),
    keyword: str = Query(default=None),
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None), 
    verified_token: bool = Depends(verify_token)
):
    """
    **Summary:**
    Fetch all projects associated with a specific project ID.

    **Args:**
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency to ensure the request is authenticated.

    **Returns:**
    - `ProjectListResponse`: A list of projects related to the specified project.
      Status code 200 if successful, or 500 if an internal server error occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await project_controller.get_all_projects(db,keyword,page,page_size)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/self_assign_project",response_model=None,status_code=status.HTTP_201_CREATED)
async def self_assign_project(
    project_id: str,
    start_date: datetime = Form(...),
    due_date: datetime = Form(...),
    # request_type: str = Form(...),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    Self-assign the current member as the project manager for a specific project.

    **Summary:**
    This endpoint allows the current authenticated member to assign themselves as the project manager for a specific project.
    The member can optionally provide a start date and due date for the project.

    **Parameters:**
    - `project_id` (str): The unique identifier of the project.
    - `start_date` (datetime, optional): The start date of the project. If not provided, the project will have no specific start date.
    - `due_date` (datetime, optional): The due date of the project. If not provided, the project will have no specific due date.
    - `db` (Session, dependency): The database session used for the transaction.
    - `current_member` (Members, dependency): The current authenticated member who is self-assigning to the project.

    **Returns:**
    - `None`: The function does not return a response model. It handles the self-assignment operation.

    **Raises:**
    - `HTTPException`: Returns a JSON response with a message and status code 500 in case of any error during the self-assignment process.
    """
    try:
        # # Validate request type
        # if not request_type or request_type not in ['ASSIGN_START', 'START']:
        #     return JSONResponse(status_code=400, content={"message": "Invalied request"})
        
        # Validate start_date and due_date
        if start_date and due_date:
            if start_date > due_date:
                return JSONResponse(status_code=400, content={"message": "Start date cannot be greater than due date."})
            if due_date < start_date:
                return JSONResponse(status_code=400, content={"message": "Due date cannot be less than start date."})

        return await project_controller.to_assign_project(project_id, start_date, due_date, db, current_member)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_self_assigned_projects",status_code=status.HTTP_200_OK)
async def get_self_assigned_project(
    db: Session = Depends(get_db),
    module_type: str = Query(alias="module_type", description = "Options: 'Estimation' or 'Project Management'"),
    project_status: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'Pending', 'In Progress', 'Dropped'. 'Failed', 'Done'"),
    bid_status: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'Estimating', 'Await Bid', 'Sent'. 'Wait for approval', 'Bid Success', 'Bid Failed'"),
    keyword: str = Query(default=None),
    client_id: str = Query(default=None),
    verified_token: bool = Depends(verify_token),
    current_member: Members = Depends(get_current_member),
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    sort_by: Optional[list] = Query(default=None, description = "Options should be commma seperated: 'name', 'quotation_due_date', 'priority', 'start_date', 'due_date'")
):
    """
    Retrieve a list of projects assigned to the current member.

    **Endpoint:** `/get-assign-project`

    **Method:** GET

    **Summary:**
    This endpoint fetches projects assigned to the current member who has a "Project Manager" role. 
    It ensures that the user is authenticated and has a valid token before proceeding. If the token is invalid, 
    it returns an invalid credential response.

    **Parameters:**
    - `db: Session`: Database session dependency.
    - `module_type` (str) this will filter the project list based on module_type (Options: "Estimation", "Project Management")
    - `project_status`: Option parameter which will filter data based on project status
    - `bid_status` (str): this will be usefull for filter search.
    - `keyword`: Option parameter whick will filter data based on project name
    - `client_id`: Option parameter which will filter data based on client ID
    - `verified_token: bool`: Token verification dependency, ensuring the user is authenticated.
    - `current_member: Members`: The current member object retrieved based on the authenticated user.
    - `page`: Option parameter whick will filter data based on page number
    - `page_size`: Option parameter whick will filter data based on page size
    - `sort_by` (str) this will sort the list based on the requested order

    **Returns:**
    - A list of assigned projects if the request is successful.
    - An error response if the token is invalid or if an internal server error occurs.

    **Response Codes:**
    - `200`: Successfully retrieved the list of assigned projects.
    - `401`: Invalid credentials if the token is not verified.
    - `500`: Internal server error.

    **Raises:**
    - `Exception`: If any unexpected errors occur during execution.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await project_controller.self_assign_project_list(
            db, module_type, current_member, project_status, bid_status, client_id, keyword, page, page_size, sort_by)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/v2/get_self_assigned_projects",status_code=status.HTTP_200_OK)
async def get_self_assigned_project(
    db: Session = Depends(get_db),
    project_status: str = Query(default=None),
    keyword: str = Query(default=None),
    verified_token: bool = Depends(verify_token),
    current_member: Members = Depends(get_current_member),
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None)
):
    """
    Retrieve a list of projects assigned to the current member.

    **Endpoint:** `/get-assign-project`

    **Method:** GET

    **Summary:**
    This endpoint fetches projects assigned to the current member who has a "Project Manager" role. 
    It ensures that the user is authenticated and has a valid token before proceeding. If the token is invalid, 
    it returns an invalid credential response.

    **Parameters:**
    - `db: Session`: Database session dependency.
    - `verified_token: bool`: Token verification dependency, ensuring the user is authenticated.
    - `current_member: Members`: The current member object retrieved based on the authenticated user.

    **Returns:**
    - A list of assigned projects if the request is successful.
    - An error response if the token is invalid or if an internal server error occurs.

    **Response Codes:**
    - `200`: Successfully retrieved the list of assigned projects.
    - `401`: Invalid credentials if the token is not verified.
    - `500`: Internal server error.

    **Raises:**
    - `Exception`: If any unexpected errors occur during execution.
    """
    try:
        print("Hello Starting..")
        if not verified_token:
            return invalid_credential_resp

        return await project_controller.self_assign_project_list_v2(db,project_status,current_member,keyword,page,page_size)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

@router.post("/assign_member/{project_id}", response_model=None,status_code=status.HTTP_201_CREATED)
async def assign_member(
    project_id: str,
    role_id: str = Form(...),
    member_ids: str = Form(None),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    Assign members to a project with a specific role.

    **Summary:**
    This endpoint allows assigning multiple members to a project using a specified role.
    The `member_ids` should be provided as a comma-separated string of member IDs.

    **Parameters:**
    - `project_id` (str): The unique identifier of the project.
    - `role_id` (str): The role ID to be assigned to the members.
    - `member_ids` (str, optional): A comma-separated string of member IDs to be assigned to the project. 
      Example: `"776876, 674657"`. If not provided, no members will be assigned.
    - `db` (Session, dependency): The database session used for the transaction.
    - `current_member` (Members, dependency): The current authenticated member.

    **Returns:**
    - `None`: The function does not return a response model. It handles the assignment operation.

    **Raises:**
    - `HTTPException`: Returns a JSON response with a message and status code 500 in case of any error during the assignment.
    """
    try:
        return await project_controller.assign_members_to_project(project_id, role_id, member_ids, db, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.get("/{project_id}/get_unassigned_members/role/{role_id}", response_model=MembersResponse, status_code=status.HTTP_200_OK)
async def get_unassigned_members(
    project_id: str,
    role_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    Retrieve a list of members who are not yet assigned to the specified project with the specified role.

    **Parameters:**
    - `project_id` (str): The unique identifier of the project.
    - `role_id` (str): The role ID for which unassigned members are to be fetched.
    - `db` (Session): The database session used for querying.
    - `verified_token` (bool): The verification status of the token.

    **Returns:**
    - `MembersResponse`: A list of members, each containing the `id` and `name` of an unassigned member.
    
    """
    if not verified_token:
        return invalid_credential_resp

    try:
        unassigned_members = await project_controller.get_unassigned_members(project_id, role_id, db)
        return unassigned_members

    except Exception as error:
        return JSONResponse(content={"status": "failure", "message": str(error)}, status_code=500)


@router.get("/{project_id}/get_assigned_members/role/{role_id}", response_model=MembersResponse, status_code=status.HTTP_200_OK)
async def get_assigned_members(
    project_id: str,
    role_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    Retrieve a list of members who are  assigned to the specified project with the specified role.

    **Parameters:**
    - `project_id` (str): The unique identifier of the project.
    - `role_id` (str): The role ID for which assigned members are to be fetched.
    - `db` (Session): The database session used for querying.
    - `verified_token` (bool): The verification status of the token.

    **Returns:**
    - `MembersResponse`: A list of members, each containing the `id` and `name` of an assigned member.
    """
    if not verified_token:
            return invalid_credential_resp

    try:
        unassigned_members = await project_controller.get_assigned_members(project_id, role_id, db)
        return unassigned_members

    except Exception as error:
        return JSONResponse(content={"status": "failure", "message": str(error)}, status_code=500)




@router.get("/project_members_with_roles/{project_id}", response_model=ProjectMemberRoleResponse,status_code=status.HTTP_200_OK)
async def list_project_members_with_roles(
    project_id: str,
    role_names: str = Query(None, description="Comma-separated string of role names"),
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    keyword: str = Query(default=None),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    **Summary:**
    Retrieve all project members along with their roles for a specific project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `role_names` (str, optional): Comma-separated string of role names to filter the members by. If not provided, all roles are included.
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency.

    **Returns:**
    - `ProjectMemberRoleResponse`: Paginated list of project members with their roles.
      Status code 200 if successful, 401 if authentication fails, and 500 if an exception occurs.
    """
    try:

        return await project_controller.get_project_members_with_roles(db, project_id, current_member, role_names, page, page_size, keyword)
    
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_project_info", status_code=status.HTTP_200_OK)
@logger.catch 
async def get_project_info(
    project_id: str = Query(None, description="The ID of the project for which to retrieve the current status."),
    verified_token: bool = Depends(verify_token),
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
        if not verified_token:
            return invalid_credential_resp
        return await project_controller.get_project_info(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_members", status_code=starlette_status.HTTP_200_OK)
async def get_members(
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    project_id: str = Query(alias="project_id"),
    role_id: str = Query(alias="role_id"),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving paginated list of members depending on the input range

    This method fetches a subset of members from the database based on the specified
    page number and page size.

    **Args:**
    - `db`: The database session object.
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `keyword` (str): this will be usefull for keyword search on name and email.
    - `project_id` (str): Project Id.
    """
    try:
        return await project_controller.get_members(db, page, page_size, keyword, project_id, role_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


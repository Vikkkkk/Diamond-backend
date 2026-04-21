from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path
from starlette import status
from models import get_db
from models.members import Members
from schemas.client_schemas import Client, ClientsResponse
from schemas.client_detail_schema import ClientResponse
from controller import client_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from utils.common import upload_to_s3

router = APIRouter(prefix="/client", tags=["Client APIs"])


@router.get("/get_clients", response_model=ClientsResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_clients(
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    project_id: str = Query(None, alias="project_id"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    
):
    """**Summary:**
    This method is responsible for retreaving paginated list of clients depending on the input range

    This method fetches a subset of clients from the database based on the specified
    page number and page size.

    **Args:**
    - `db`: The database session object.
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `keyword` (str): this will be usefull for keyword search on name and email.
    - `project_id` (str): Filter clients associated with a specific project.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await client_controller.get_clients(db, page, page_size, keyword,project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_client", response_model=ClientResponse, status_code=status.HTTP_200_OK)
@logger.catch 
async def get_client(
    id: str = Query(title="Client ID", description="client ID", default=None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    
):
    """**Summary:**
    This method is responsible for retreaving the details of the input client id

    **Args:**
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `id` (str): client Id for which it will run the fetch query. Defaults to Query(description="Client ID").
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not

    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await client_controller.get_client(db, id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/insert_client", status_code=status.HTTP_201_CREATED)
@logger.catch
async def insert_client(
    client_create_request: Client,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method takes single client data and add the client to the DB

    **Args:**
    - `client_create_request` (Client): client data to be added. reffer to the client schema for the structure
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.

    """
    try:
        return await client_controller.create_client(db, client_create_request, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.delete("/delete_client/{client_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_client(
    client_id: str,
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method deletes a client from the DB based on the provided client_id.

    **Args:**
    - `client_id` (int): The unique identifier of the client to be deleted.
    - `db` (Session): DB session reference. Defaults to Depends(get_db).
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not.

    """
    try:
        # Delete the client
        return await client_controller.delete_client_soft(db, client_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.put("/update_client/{client_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_client(
    client_id: str,
    client_update_request: Client,
    role_required = Depends(role_required(["Admin", "Chief Estimator"])),  # Specify allowed roles here
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
    
):
    """**Summary:**
    This method updates a client's data in the DB

    **Args:**
    - `client_id` (int): ID of the client to be updated
    - `client_update_request` (Client): Updated client data. Refer to the client schema for the structure
    - `db` (Session): db session reference. Defaults to Depends(get_db).
    """
    try:
        return await client_controller.update_client(db, client_id, client_update_request, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

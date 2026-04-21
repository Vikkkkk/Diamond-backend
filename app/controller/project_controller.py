"""
This module contains all logical operations and db operations related to projects.
"""
from typing import List, Optional
from utils.common import get_utc_time, generate_uuid, get_random_hex_code, generate_uuid
# from utils.request_handler import send_transfer_opening_request
from loguru import logger
from models.projects import Projects
from models.project_status_logs import ProjectStatusLogs
from models.status import Status
from models.roles import Roles
from models.clients import Clients
from models.client_projects import ClientProjects
from models.members import Members
from models.role_permissions import RolePermissions
from models.roles import Roles
from models.modules import Modules
from models.sub_modules import SubModules
from utils.common import generate_uuid, delete_file, save_uploaded_file, format_project_code
from repositories.member_repositories import get_project_members, get_project_member_permission, get_role_by_id
from repositories.project_repositories import project_member_association, project_client_association, get_sort_order
from repositories.permission_repositories import get_allowed_roles_by_name
from models.tender_documents import TenderDocuments
from models.quotation_revision import QuotationRevision
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, text, and_, not_, asc, desc, cast
import math
from utils.common import get_user_time
import os
from sqlalchemy.orm import Session
from fastapi import UploadFile
from schemas.project_schemas import ProjectListResponse, ProjectAssignResponse, MembersResponse, ProjectList
from models.project_members import ProjectMembers
from models.member_role import MemberRole
from fastapi import HTTPException, status
from datetime import datetime
import json
import time
from utils.common import upload_to_s3, delete_from_s3, download_from_s3
from models.projects import Priority
from controller.transfer_opening_controller import transfer_opening
from sqlalchemy.types import String

load_dotenv()
    

async def get_projects(
        db: Session, 
        page: int, 
        page_size: int, 
        keyword: str, 
        current_member: Members,
        module_type: Optional[str] = None,
        project_status: Optional[list] = None,
        bid_status: Optional[list] = None,  
        client_id: Optional[str] = None, 
        sort_by=None,
    ):
    """
    Fetches a list of projects with optional pagination, keyword search, and project status filtering.

    Args:
        db (Session): The database session object.
        page (Optional[int]): The page number to retrieve (None for no pagination).
        page_size (Optional[int]): The number of items per page (None to fetch all).
        keyword (Optional[str]): Search keyword for filtering by name or project_code.
        project_status (Optional[str]): Filter based on the project status.
        current_member (Members): The current member requesting the data.

    Returns:
        dict: Paginated or full project data with `data`, `page_count`, `item_count`, and `status`.
    """
    try:
        # prepare sort filter if provided
        if sort_by:
            order_by_clauses = await get_sort_order(sort_by)
            if not order_by_clauses:
                return JSONResponse(content={"message": f"Invalid sort field"}, status_code=400)

        # Base query to fetch non-deleted projects
        query = (
            db.query(Projects)
            .join(ClientProjects)
            .join(Clients)
            .filter(Projects.is_deleted == False)
        )

        # Apply filter 'module type' if provided
        if module_type and module_type == "Project Management":
            query = query.filter(Projects.is_estimation == False)

        # Apply keyword search on name and project_code
        if keyword:
            query = query.filter(
                or_(
                    Projects.name.ilike(f'%{keyword}%'),
                    Projects.project_code.ilike(f'%{keyword}%')
                )
            )

        # Apply project status filter if provided
        if project_status:
            project_status_filter = [field.strip() for field in project_status[0].split(",")]
            query = query.filter(Projects.current_project_status.in_(project_status_filter))

        # Apply bid status filter if provided
        if bid_status:
            bid_status_filter = [field.strip() for field in bid_status[0].split(",")]
            query = query.filter(Projects.current_bid_status.in_(bid_status_filter))
        
        # Apply 'client_id' filter if provided
        if client_id is not None:
            query = query.filter(ClientProjects.client_id == client_id)

        # Count total matching items (before pagination)
        item_count = query.distinct().count()

        # Apply sort if provided
        if sort_by:
            query = query.order_by(*order_by_clauses)
        
        # Apply pagination if provided
        if page is not None and page_size is not None:
            skip = (page - 1) * page_size
            query = query.offset(skip).limit(page_size)
        else:
            page = 1 
            page_size = item_count
            skip = 0

        # Fetch the project items
        project_items = query.all()

        # Construct the final project data
        final_project_data = []
        for item in project_items:
            project_obj = item.to_dict
            client_list = []

            if item.project_clients:
                for client_data in item.project_clients:
                    if client_data.client and not client_data.client.is_deleted:
                        client_list.append(client_data.client)

            project_obj["clients"] = client_list
            final_project_data.append(project_obj)

        # Calculate the total number of pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        # Return the response with paginated or full data
        response = {
            "data": final_project_data,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

        return response

    except Exception as e:
        logger.exception(f"get_projects::error - {str(e)}")
        raise e
   
    

async def get_project(db: Session, id: str):
    """**Summary:**
    This method is responsible for retreaving the details of the input project id

    **Args:**
        db (Session): db session referance
        id (String): project Id for which it will run the fetch query

    """
    try:
        project = (
            db.query(Projects)
            .join(ClientProjects)
            .join(Clients)
            .outerjoin(TenderDocuments, ((Projects.id == TenderDocuments.project_id)))
            .filter(
                Projects.id == id,
                Projects.is_deleted==False
            )
            .first()
        )

        # Check if project is None (no data found)
        if project is None:
            return JSONResponse(content={"message": "Project not found."},\
                                 status_code=404)
        project_members = []
        if project.project_members:
            project_members = await get_project_members(db, id)
        client_list = []
        if project.project_clients:
            for client_data in project.project_clients:
                if client_data.client and not client_data.client.is_deleted:
                    client_list.append(client_data.client)
        tender_documents = []
        if project.tender_documents:
            for tender_document in project.tender_documents:
                tender_documents.append(tender_document.to_dict) 
        project  = project.to_dict
        project['clients'] = client_list
        project['tender_documents'] = tender_documents
        project['project_members'] = project_members

        return  {"data": project, "status": "success"}
    except Exception as e:
        logger.exception("get_project:: error - " + str(e))
        raise e
        
      

async def get_project_role_members(db: Session, id: str, role_id: str):
    """**Summary:**
    This method is responsible for retreaving the member list for a module id within a project

    **Args:**
        - db (Session): db session referance
        - id (String): project Id for which it will return the members.
        - role_id (String): role Id for which it will return the members of a project.

    """
    try:
        project_role_members = await get_project_members(db, id, role_id)
        return  {"data": project_role_members, "status": "success"}
    except Exception as e:
        logger.exception("get_project_role_members:: error - " + str(e))
        raise e
        

async def create_project(
    db: Session, 
    project_data: dict, 
    files: List[UploadFile], 
    current_member: Members
    ):
    """**Summary:**
    This method takes a single project's data as input, checks if the project already exists based on its
    email, phone, and website. If it does not exist, the project is added to the database.

    Args:
        - project_data (dict): Project data. Refer to the project schema for the structure.
        - db (Session): Database session reference.
        - file (List[UploadFile]): List of file to be uploaded and associated with the project.
        - current_member (Members): This will contain member details of current loggedin member.

    Raises:
        - IntegrityError: If there is a violation of the database integrity when inserting the project.
        - Exception: For other unexpected errors during the project creation process.

    This method takes single project data as input, it check if the project is already exists or not,
    depending on its email, phone, website. If not exists then add the project to the DB
    """
    try:
        if 'member_ids' in project_data:
            member_id = project_data['member_ids']
            if member_id is None:
                member_ids = []
            else:
                member_ids = member_id[0].split(',')
            del project_data['member_ids']

        if 'client_ids' in project_data:   
            client_id = project_data['client_ids']
            if client_id is None:
                client_ids = []
            else:
                client_ids = client_id[0].split(',')
            del project_data['client_ids']
        current_project_status = "Pending"
        current_bid_status = "Estimating"
        id = generate_uuid()
        project_data['id'] = id
        project_data['created_by'] = current_member.id
        project_data['current_project_status'] = current_project_status
        project_data['current_bid_status'] = current_bid_status
        project_data['is_estimation'] = True
        # Handle priority if it exists in the request
        if "priority" in project_data:
            try:
                # Convert priority string (e.g., "HIGH", "MEDIUM", "LOW") to corresponding integer
                project_data['priority'] = Priority[project_data['priority'].upper()].value
            except KeyError:
                return JSONResponse(
                    content={"message": "Invalid priority value. Use 'HIGH', 'MEDIUM', or 'LOW'."}, 
                    status_code=400
                )
        else:
            # Default priority if not provided
            project_data['priority'] = Priority.LOW.value

        if "project_code" in project_data and project_data["project_code"] is not None and \
            db.query(Projects).filter(Projects.project_code==project_data["project_code"]).first():
            return JSONResponse(content={"message": "Project Code already exists, enter a different project Code."},\
                                 status_code=400)
        else:
            if db.in_transaction():
                # if there is an any active transaction then commit it
                db.commit()
            # Begin a transaction
            with db.begin():
                # Query the database to get the most recently created project
                project = db.query(Projects).order_by(Projects.created_at.desc()).first()
                project_code = None
                if project:
                    project_code = project.project_code
                # Format the project_code using the format_project_code function
                project_code = await format_project_code(project_code)
                project_data['project_code'] = project_code

                # Create a new project instance and add it to the database
                new_project = Projects(**project_data)
                db.add(new_project)
                db.flush()
                status_data = db.query(Status).filter(Status.category == "PROJECT_STATUS", Status.type == current_project_status).first()
                status_id = status_data.id
                # Log the initial project status
                await insert_project_logs(db, current_member, id, status_id)
                
                status_data = db.query(Status).filter(Status.category == "BID_STATUS", Status.type == current_bid_status).first()
                status_id = status_data.id
                # Log the initial bid status

                await insert_project_logs(db, current_member, id, status_id)

                # Associate project members
                role_data = db.query(Roles).filter(Roles.name == "Chief Estimator").first()
                role_id = str(role_data.id)
                await project_member_association(db, id, member_ids, role_id, current_member)

                # Associate Project clients
                await project_client_association(db, id, client_ids, current_member)

                for file in files:
                    file_name = file.filename
                    tender_document = TenderDocuments(file_name = file_name, project_id=id, \
                                                     created_by=current_member.id)
                    # Add the instance to the database session
                    db.add(tender_document)
                    db.flush()

                    # Claaing function "upload_to_s3" to upload the attachment to S3
                    upload_path = f"project_document/{new_project.id}/{tender_document.id}"
                    file_path = await upload_to_s3(file, upload_path)
                    tender_document.file_path = file_path

            # save all changes in DB
            # db.commit()
 
            return {"id": id, "message": "Data inserted successfully.", "status": "success"}
    except IntegrityError as e:
        db.rollback()
        logger.exception(f"IntegrityError: {e}")
        raise e
    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        if str(e) == "NOT_AN_ESTIMATOR":
            return JSONResponse(content={"message": "Not an Estimator"}, status_code=400)
        else:
            raise e



async def delete_project_soft(db: Session, id: str, current_member: Members):
    """
    Soft delete a project by updating the is_deleted flag.
    Args:
        db (Session): DB session reference.
        id (int): The unique identifier of the project to be soft deleted.
        current_member (Members): This will contain member details of current loggedin member.
    """
    project_exist = db.query(Projects).filter(Projects.id == id, Projects.is_deleted == False).first()
    if project_exist:
        project = db.query(Projects).get(id)
        project.is_deleted = True
        project.deleted_at = datetime.now()
        project.deleted_by = current_member.id
        db.commit()
        return {"message": "Data deleted successfully.", "status": "success"}
    else:
        return JSONResponse(content={"message": "Project not found"}, status_code=400)



async def update_project(
    db: Session, 
    id: str, 
    updated_project_data: dict, 
    current_member: Members, 
    files=None, 
    removed_tender_docs=None
):
    """**Summary:**
    Update an existing project in the database.

    Args:
    - db (Session): Database session reference.
    - id (str): The unique identifier of the project to be updated.
    - updated_project_data (dict): Updated project data. Refer to the project schema for the structure.
    - files (list, optional): List of uploaded files associated with the project.
    - removed_member_docs (list, optional): List of member document IDs to be removed.

    Raises:
    - IntegrityError: If there is a violation of the database integrity during the update process.
    - Exception: For other unexpected errors during the update process.

    Steps:
    1. Check if the project with the given project ID exists.
    2. Check the project uniqueness
    3. If member documents are to be removed, delete them from the database and file storage.
    4. Update the project data.
    5. If files are provided, save and associate them with the project.
    6. Return a success message upon successful update.

    Note:
    - In case of an IntegrityError, the changes are rolled back, and the error is logged and raised.
    - In case of other exceptions, the changes are rolled back, and the error is logged and raised.
    - The function ensures that changes to the database are committed in the 'finally' block.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            print(">>>>>>>>>>>", updated_project_data)
            # Check if the project with the given project ID exists
            existing_project = db.query(Projects).filter(Projects.id == id, Projects.is_deleted == False).first()
            if existing_project is None:
                return JSONResponse(content={"message": "Project with the given project ID not found."}, status_code=202)
            
            if "project_code" in updated_project_data:
                duplicate_project = db.query(Projects).filter(id == updated_project_data['project_code'], id != id,\
                                                            Projects.is_deleted == False).first()
                if duplicate_project:
                    return JSONResponse(content={"message": "Project Code already exists, enter a different project Code."}, status_code=400)
            
            role_data = db.query(Roles).filter(Roles.name == "Chief Estimator").first()
            role_id = str(role_data.id)
            # Update the project data
            updated_project_data['updated_by'] = current_member.id

            # Handle priority update
            if "priority" in updated_project_data and updated_project_data['priority'] is not None:
                try:
                    # Convert priority string (e.g., "HIGH", "MEDIUM", "LOW") to corresponding integer
                    updated_project_data['priority'] = Priority[updated_project_data['priority'].upper()].value
                except KeyError:
                    return JSONResponse(
                        content={"message": "Invalid priority value. Use 'HIGH', 'MEDIUM', or 'LOW'."}, 
                        status_code=400
                    )

            # Only update the attributes of the existing project where the corresponding value in updated_project_data is not None.
            for key, value in updated_project_data.items():
                if value is not None:
                    setattr(existing_project, key, value)
            
            # Associate Project members
            if updated_project_data['member_ids']:
                member_ids = updated_project_data['member_ids'][0].split(',')
                await project_member_association(db, id, member_ids, role_id, current_member, update=True)
            
            # Associate Project clients
            if updated_project_data['client_ids']:
                client_ids = updated_project_data['client_ids'][0].split(',')
                await project_client_association(db, id, client_ids, current_member)


            # If member documents are to be removed, delete them from the database
            if removed_tender_docs:
                # member_id = project_data['member_id']
                doc_ids = removed_tender_docs[0].split(',')
                for doc_id in doc_ids:
                    member_doc = db.query(TenderDocuments).filter_by(id=doc_id).first()
                    if member_doc:
                        # delete_file(member_doc.file_path)
                        await delete_from_s3(member_doc.file_path)
                        db.delete(member_doc)
                    db.flush()

                for file in files:
                    filename = file.filename
                    # Create a new instance of the TenderDocument model
                    created_by = current_member.id
                    tender_document = TenderDocuments(file_name=filename, project_id=id, created_by=created_by)
                    # Add the instance to the database session
                    db.add(tender_document)
                    db.flush()

                    # Claaing function "upload_to_s3" to upload the attachment to S3
                    upload_path = f"project_document/{id}/{tender_document.id}"
                    file_path = await upload_to_s3(file, upload_path)
                    tender_document.file_path = file_path

        # Save all changes in DB
        db.commit()
        return {"id": id, "message": "Project updated successfully.", "status": "success"}

    except IntegrityError as e:
        db.rollback()
        logger.exception(f"IntegrityError during project update: {e}")
        raise e
    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        if str(e) == "NOT_AN_ESTIMATOR":
            # print(str(e))
            return JSONResponse(content={"message": "Not an Estimator"}, status_code=400)
        else:
            raise e
    


async def download_file(db: Session, id: str):
    """
    Download File

    Retrieves and downloads a file from the database based on the provided file ID.

    Parameters:
    - `db` (Session): Database session.
    - `id` (str): The ID of the file to download.

    Returns:
    - FileResponse: Returns the file for download if successful.

    Raises:
    - HTTPException(404): If the specified file ID does not exist in the database.
    - HTTPException(404): If the file path specified in the database does not exist.
    - JSONResponse(202): If the file ID exists, but the file is marked as non-existent (status code 202).

    Note:
    The function assumes a database model named TenderDocuments with attributes:
    - `id`: Unique identifier for the file.
    - `file_path`: The path to the file on the server.
    - `file_name`: The name of the file.
    """

    tender_document = db.query(TenderDocuments).filter(TenderDocuments.id == id).first()
    if tender_document is None:
        return JSONResponse(content={"message": "File doesn't exists"}, status_code=202)
    
     # File path in S3
    file_path = tender_document.file_path

    file_stream, content_type, filename = download_from_s3(file_path)

    # Return the file as a streaming response
    return StreamingResponse(file_stream, media_type=content_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    # headers = {"Content-Disposition": "inline"}
    # return FileResponse(existing_project.file_path, headers=headers)




async def get_project_logs(db: Session, project_id: str, category: str):
    """**Summary:**
    This method is responsible for retreaving the project/bid log list for a project within a project

    **Args:**
        - db (Session): db session referance
        - project_id (String): project Id for which it will return the members.
        - category (String): category for which it will return the members of a project.

    """
    try:
        project_bid_logs = (db.query(ProjectStatusLogs)
                            .join(Status)
                            .filter(ProjectStatusLogs.project_id == project_id, Status.category == category)
                            .order_by(ProjectStatusLogs.created_at).all())
        response = []
        for log in project_bid_logs:
            res = log.to_dict
            res['status_info'] = log.status
            response.append(res)

        return  {"data": response, "status": "success"}
    
    except Exception as e:
        logger.exception("get_project_logs:: error - " + str(e))
        raise e
    


async def insert_project_logs(
    db: Session, 
    current_member: Members, 
    project_id: str, 
    status_id: str, 
    status_type=False, 
    data_return=False
    ):
    """**Summary:**
    Insert project status logs into the database.

    Args:
        db: Database session.
        current_member: Current member object.
        project_id: ID of the project.
        status_id: ID of the status.

    Raises:
        Exception: If an error occurs during the insertion process.
    """
    try:
        created_by = current_member.id

        # Create and add the status log
        status_log = ProjectStatusLogs(status_id=status_id, project_id=project_id, created_by=created_by)
        db.add(status_log)
        db.flush()

        # Fetch the status object
        status = db.query(Status).filter(Status.id == status_id).first()
        if not status:
            raise ValueError(f"Status with id {status_id} not found.")

        update_project = {}
        # Handle project status updates
        if status_type == "PROJECT_STATUS":
            update_project['current_project_status'] = status.type
            if status.type == "In Progress":
                update_project['is_estimation'] = False
     
        # Handle bid status updates
        elif status_type == "BID_STATUS":
            update_project['current_bid_status'] = status.type
            if status.type == "Bid Failed":
                project_status = "Failed"
                update_project['current_project_status'] = project_status
                project_status = db.query(Status).filter(Status.type == project_status, Status.category=="PROJECT_STATUS").first()
                project_status_id = project_status.id
                status_log = ProjectStatusLogs(status_id=project_status_id, project_id=project_id, created_by=created_by)
                db.add(status_log)
                db.flush()

            if status.type == "Bid Success":
                update_project['is_estimation'] = False
                quotation_revision_exists = db.query(QuotationRevision).filter(QuotationRevision.project_id == project_id).count()
                
                if not quotation_revision_exists:
                    return JSONResponse(
                        status_code=400,
                        content={"message": "No quotations found."},
                    )

            # Update the Projects table
        db.query(Projects).filter(Projects.id == project_id).update(update_project)

        if data_return:
            db.commit()
            return {"id": status_log.id, "message": "Status updated successfully.", "status": "success"}

    except ValueError as ve:
        logger.warning(f"insert_project_bid_logs:: validation error: {ve}")
        return {"message": str(ve), "status": "failure"}

    except Exception as e:
        logger.exception(f"insert_project_bid_logs:: unexpected error occurred: {e}")
        raise




async def get_project_status(db: Session, category: str):
    """**Summary:**
    This method is responsible for retreaving the project/bid status list

    **Args:**
        - db (Session): db session referance
        - category (String): category for which it will return the members of a project.
    """
    try:
        project_status = (db.query(Status)
                            .filter(Status.category == category).order_by(Status.sort_order).all())
        response = []
        for status in project_status:
            response.append(status.to_dict)

        return  {"data": response, "status": "success"}
    
    except Exception as e:
        logger.exception("get_project_status:: error - " + str(e))
        raise e
    
    

async def upload_tender_documents(db: Session, project_id: str, files, current_member: Members):
    """**Summary:**
    Uploads tender documents for a specific project and saves the file in the database.

    **Parameters:**
    - db: The database session to perform the operation.
    - project_id: The identifier of the project to associate the uploaded file with.
    - files: The file to be uploaded and associated with the project.
    - current_member (Members): This will contain member details of current loggedin member.

    Returns:
    A dictionary with a success message upon successful file upload.

    Raises:
    - HTTPException: If an unexpected error occurs during the file upload process.
    """
    try:
        for file in files:
            file_name = file.filename
            tender_document = TenderDocuments(file_name = file_name, project_id=project_id, \
                                                created_by=current_member.id)
            # Add the instance to the database session
            db.add(tender_document)
            db.flush()

            # Calling function "upload_to_s3" to upload the attachment to S3
            upload_path = f"tender_document/{project_id}/{tender_document.id}"
            file_path = await upload_to_s3(file, upload_path)
            tender_document.file_path = file_path

        # Commit the changes to the database
        db.commit()
        return {"message": "File uploaded successfully"}
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise


async def delete_tender_document(db: Session, document_id: str, current_member: Members):
    """**Summary:**
    Deletes a tender document for a specific project.

    **Parameters:**
    - db: The database session to perform the operation.
    - document_id: The identifier of the document to delete.
    - current_member (Members): This will contain member details of the current logged-in member.

    Returns:
    A dictionary with a success message upon successful deletion.

    Raises:
    - HTTPException: If the document is not found or if deletion fails.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            tender_document = db.query(TenderDocuments).filter_by(id=document_id).first()

            if not tender_document:
                raise HTTPException(status_code=404, detail="Document not found")

            # Call a function to delete the file from S3
            await delete_from_s3(tender_document.file_path)

            # Remove the document record from the database
            db.delete(tender_document)
            db.commit()

        return JSONResponse(status_code=200, content={"message": "Document deleted successfully", "status": "success"})

    except HTTPException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



async def get_all_projects(
    db: Session,
    keyword: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
):
    """
    Fetch a list of projects with the following conditions:
    - current_project_status = "Pending"
    - current_bid_status = "Bid Success"
    - The project is not associated with any member with the role "Project Manager".

    Args:
    - db (Session): The database session.
    - keyword (Optional[str]): A keyword to filter projects by name (default: None).
    - page (Optional[int]): The page number for pagination (default: None).
    - page_size (Optional[int]): The number of items per page for pagination (default: None).

    Returns:
    - dict: A dictionary containing the paginated projects, page count, item count, and status.
    """
    try:
        query = (
            db.query(Projects)
            .outerjoin(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .outerjoin(MemberRole, ProjectMembers.member_role_id == MemberRole.id)
            .outerjoin(Members, Members.id == MemberRole.member_id)
            .outerjoin(Roles, MemberRole.role_id == Roles.id)
            .filter(
                Projects.current_project_status == "Pending",
                Projects.current_bid_status == "Bid Success",
                # Projects.is_estimation == False,
                ~db.query(ProjectMembers.project_id)
                .join(MemberRole, ProjectMembers.member_role_id == MemberRole.id)
                .join(Roles, MemberRole.role_id == Roles.id)
                .filter(ProjectMembers.project_id == Projects.id, Roles.name == "Chief Project Manager")
                .exists()
            )
        )
        # Apply keyword search if provided
        if keyword:
            query = query.filter(Projects.name.ilike(f"%{keyword}%"))

        # Order by project name and priority
        query = query.order_by(Projects.priority.desc(), Projects.name.desc())

        # Get the total count of items
        query = query.distinct(Projects.id)
        item_count = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = item_count if item_count else 1
            page = 1

        projects = query.all()

        res_list = []
        for data in projects:
            for project_members in data.project_members:
                member_data = project_members.project_member_roles.member
                res = {
                    "project_id": data.id,
                    "project_name": data.name,
                    "start_date": data.start_date,
                    "due_date": data.due_date,
                    "current_project_status": data.current_project_status,
                    "member_id": member_data.id,
                    "member_name": member_data.first_name + " " + member_data.last_name,
                    "role_id": project_members.project_member_roles.role.id,
                    "role_name": project_members.project_member_roles.role.name
                }
                
                res_list.append(res)
        # Construct the response as before
        projects = {}
        for data in res_list:
            project_id = data['project_id']
            member_id = data['member_id']
            
            role_data = {"id": data['role_id'], "name": data['role_name']}
            
            if project_id not in projects:
                projects[project_id] = {
                    "id": project_id,
                    "name": data['project_name'],
                    "start_date": data['start_date'],
                    "due_date": data['due_date'],
                    "current_project_status": data['current_project_status'],
                    "project_members": {}
                }

            if member_id not in projects[project_id]['project_members']:
                projects[project_id]['project_members'][member_id] = {
                    "id": member_id, 
                    "name": data['member_name'], 
                    "roles": []
                }

            projects[project_id]['project_members'][member_id]['roles'].append(role_data)

        response = [project for project in projects.values()]
        for project in response:
            project['project_members'] = list(project['project_members'].values())

        # Calculate the total number of pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        return {
            "data": response,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An error occurred while fetching projects: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")




async def to_assign_project(project_id: str, start_date: datetime, due_date: datetime, db: Session, current_member: Members):
    try:
        # Ensure that any existing transactions are committed
        if db.in_transaction():
            db.commit()
        
        # Begin a transaction
        with db.begin():

        
            project_manager_role = (
                db.query(ProjectMembers)
                .join(MemberRole, ProjectMembers.member_role_id == MemberRole.id)
                .join(Roles, Roles.id == MemberRole.role_id)
                .filter(Roles.name == "Chief Project Manager")
                .filter(ProjectMembers.project_id == project_id)
                .first()
            )

            # print(project_manager_role)

            if project_manager_role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Already 'Chief Project Manager' found for this project")


            # Assign the current member to the project
            member_role = (
                db.query(MemberRole)
                .join(Roles, Roles.id == MemberRole.role_id)
                .filter(Roles.name == "Chief Project Manager")
                .filter(MemberRole.member_id == current_member.id)
            ).first()

            project_member = ProjectMembers(
                member_role_id=member_role.id,
                project_id=project_id,
                is_active=True,
                created_by=current_member.id
            )

            db.add(project_member)

            # Update the current project status to "In Progress"
            project = db.query(Projects).filter(Projects.id == project_id).first()
            if project:
                project.current_project_status = "In Progress"
                project.start_date = start_date if start_date else None
                project.due_date = due_date if due_date else None
                project.updated_by = current_member.id
                project.is_estimation = False
                db.add(project)

            current_project_status = "In Progress"
            status_data = db.query(Status).filter(Status.category == "PROJECT_STATUS", Status.type == current_project_status).first()
            status_id = status_data.id

            await insert_project_logs(db,current_member,project_id,status_id,status_type="PROJECT_STATUS") 
            db.flush()
            # Transfer project takeoffsheet opening data to opening schedule
            await transfer_opening(db, project_id, current_member)

        # await send_transfer_opening_request(project_id, current_member.token)
            
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Project assigned successfully", "status": "success"})
    
    except HTTPException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except IntegrityError as e:
        db.rollback()
        logger.exception(f"Database integrity error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database integrity error occurred.")

    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    finally:
        db.commit()


def get_client_details(project_id, client_data):
    for client in client_data:
        if project_id in client:
            return client[project_id] 
    return [] 



async def self_assign_project_list(
    db: Session,
    module_type: str,
    current_member: Members,
    project_status: Optional[list] = None,
    bid_status: Optional[list] = None,
    client_id: Optional[str] = None,
    keyword: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_by: Optional[list] = None
):
    try:
        # Prepare sort order
        if sort_by:
            order_by_clauses = await get_sort_order(sort_by)
            if not order_by_clauses:
                return JSONResponse(content={"message": f"Invalid sort field"}, status_code=400)

        project_ids_obj = (
            db.query(Projects.id.label('project_id'))
            .join(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .join(MemberRole, MemberRole.id == ProjectMembers.member_role_id)
            .filter(
                MemberRole.member_id == current_member.id,
                MemberRole.active_role == True,
                Projects.is_deleted == False
                )
            .group_by(Projects.id)
        )

        # Apply 'is_estimation' based on 'module_type'
        if module_type != "Estimation":
            project_ids_obj = project_ids_obj.filter(Projects.is_estimation == False)

        # Apply 'client_id' filter if provided
        if client_id is not None:
            project_ids_obj = project_ids_obj.join(ClientProjects, ClientProjects.project_id == Projects.id).filter(
                ClientProjects.client_id == client_id
            )

        # Apply 'project_status' filter if provided
        if project_status is not None:
            project_status_filter = [field.strip() for field in project_status[0].split(",")]
            project_ids_obj = project_ids_obj.filter(Projects.current_project_status.in_(project_status_filter))

        # Apply 'bid_status' filter if provided
        if bid_status is not None:
            bid_status_filter = [field.strip() for field in bid_status[0].split(",")]
            project_ids_obj = project_ids_obj.filter(Projects.current_bid_status.in_(bid_status_filter))

        # Fetch the result
        project_ids_obj = project_ids_obj.all()
        
        # Prepare list of project_ids
        project_ids = [str(project_id_obj.project_id) for project_id_obj in project_ids_obj]

        # apply projects_ids filter
        project_data_query = (
            db.query(Projects)
            .join(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .join(MemberRole, ProjectMembers.member_role_id == MemberRole.id)
            .join(Members, Members.id == MemberRole.member_id)
            .join(Roles, Roles.id == MemberRole.role_id)
            .filter(
                Projects.id.in_(project_ids)
            )
            .group_by(Projects.id)
        )

        # Apply sort if provided
        if sort_by:
            project_data_query = project_data_query.order_by(*order_by_clauses)

        # Get the unique project count
        unique_project_count = project_data_query.count()

        # Apply keyword search if provided
        if keyword:
            project_data_query = project_data_query.filter(Projects.name.ilike(f"%{keyword}%"))
            unique_project_count = project_data_query.count()

        # Apply pagination based on unique projects
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            project_data_query = project_data_query.offset(offset).limit(page_size)
        else:
            page_size = unique_project_count
            page = 1

        # Get the paginated project data
        project_data = project_data_query.all()

        res_list = []
        client_list = []
        for data in project_data:
            for project_members in data.project_members:
                member_data = project_members.project_member_roles.member
                # Convert the integer priority to its corresponding string
                priority_str = Priority(data.priority).name if data.priority else None
                res = {
                    "project_id": data.id,
                    "project_name": data.name,
                    "start_date": data.start_date,
                    "due_date": data.due_date,
                    "quotation_due_date": data.quotation_due_date,
                    "current_project_status": data.current_project_status,
                    "current_bid_status": data.current_bid_status,
                    "is_estimation": data.is_estimation,
                    "member_id": member_data.id,
                    "priority": priority_str,
                    "member_name": member_data.first_name + " " + member_data.last_name,
                    "role_id": project_members.project_member_roles.role.id,
                    "role_name": project_members.project_member_roles.role.name
                }
                
                res_list.append(res)

            clients = {}
            for project_clients in data.project_clients:

                client_id = project_clients.client.id
                client_name = project_clients.client.name
                project_id = project_clients.project_id

                client_data = {'project_id':project_id,'client_id': client_id, 'name': client_name}
                # print("client_data", client_data)
                client_data = {'id': client_id, 'name': client_name}
                if project_id not in clients:
                    clients[project_id] = [client_data]
                else:
                    clients[project_id].append(client_data)

            client_list.append(clients)

        # Construct the response as before
        projects = {}
        for data in res_list:
            project_id = data['project_id']
            member_id = data['member_id']
            
            role_data = {"id": data['role_id'], "name": data['role_name']}
            
            if project_id not in projects:
                client_details = get_client_details(project_id, client_list)

                projects[project_id] = {
                    "id": project_id,
                    "name": data['project_name'],
                    "start_date": data['start_date'],
                    "due_date": data['due_date'],
                    "quotation_due_date": data['quotation_due_date'],
                    "priority": data['priority'],
                    "current_project_status": data['current_project_status'],
                    "current_bid_status": data['current_bid_status'],
                    "is_estimation": data['is_estimation'],
                    "project_members": {},
                    "clients": client_details
                }

            if member_id not in projects[project_id]['project_members']:
                projects[project_id]['project_members'][member_id] = {
                    "id": member_id, 
                    "name": data['member_name'], 
                    "roles": []
                }

            projects[project_id]['project_members'][member_id]['roles'].append(role_data)

        response = [project for project in projects.values()]
        for project in response:
            project['project_members'] = list(project['project_members'].values())

        # Calculate the total number of pages
        page_count = math.ceil(unique_project_count / page_size) if page_size > 0 else 0

        return {
            "data": response,
            "page_count": page_count,
            "item_count": unique_project_count,
            "status": "success"
        }

    except Exception as error:
        # logger.exception(f"An error occurred while fetching projects: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def self_assign_project_list_v2(
    db: Session,
    project_status: str,
    current_member: Members,
    keyword: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
):
    try:
        start_time = time.time()
        
        project_status_list = ["In Progress", "Done"]

        if project_status in project_status_list:
            project_status_list = [project_status]

        project_ids_obj = (
            db.query(Projects.id.label('project_id'))
            .join(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .join(MemberRole, MemberRole.id == ProjectMembers.member_role_id)
            .filter(
                MemberRole.member_id == current_member.id,
                Projects.current_project_status.in_(project_status_list)
            )
        )

        # Apply keyword search if provided
        if keyword:
            project_ids_obj = project_ids_obj.filter(Projects.name.ilike(f"%{keyword}%"))

        # Fetch project IDs
        project_ids_obj = project_ids_obj.group_by(Projects.id).order_by(Projects.name.asc()).all()

        project_ids = ','.join(f"'{str(project_id_obj.project_id)}'" for project_id_obj in project_ids_obj)

        sql_query = f"""
            SELECT 
            p.id AS project_id, 
            p.name AS project_name, 
            p.current_project_status, 
            p.due_date, 
            p.quotation_due_date,
            p.start_date,
            (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT('client_id', c.id, 'client_name', c.name)
                )
                FROM clients c
                JOIN client_projects cp ON cp.client_id = c.id
                WHERE cp.project_id = p.id
            ) AS client_details,
            (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'member_id', m.id, 
                        'member_name', m.first_name, 
                        'role_id', r.id,
                        'role_name', r.name
                    )
                )
                FROM project_members pm
                JOIN member_role mr ON mr.id = pm.member_role_id
                JOIN roles r on r.id = mr.role_id
                JOIN members m ON m.id = mr.member_id
                WHERE pm.project_id = p.id
            ) AS member_details

            FROM projects p
            WHERE p.id IN ({project_ids})
            GROUP BY p.id;
        """
        # Apply pagination if both page and page_size are provided
        if page and page_size:
            offset = (page - 1) * page_size
            sql_query += f" LIMIT {page_size} OFFSET {offset}"

        # Executing raw SQL with session.execute()
        result = db.execute(text(sql_query))

        # Fetching the results
        projects = result.mappings().all()

        # Convert results into list of dicts (for pretty printing)
        project_list = [dict(row) for row in projects]

        # Print the result
        res = []
        for project in project_list:

            project_dict = {}
            project_dict['id'] = project['project_id']
            project_dict['name'] = project['project_name']
            project_dict['current_project_status'] = project['current_project_status']
            project_dict['start_date'] = project['start_date']
            project_dict['due_date'] = project['due_date']
            project_dict['quotation_due_date'] = project['quotation_due_date']

            client_details = json.loads(project['client_details'])
            member_details = json.loads(project['member_details'])

            member_data = {}
            for member in member_details:
                member_id = member['member_id']
                role = {"id": member['role_id'], "name": member['role_name']}
                if member_id in member_data:
                    member_data[member_id]["roles"].append(role)
                else:
                    member_data[member_id] = {
                        "id": member_id, 
                        "name": member['member_name'], 
                        "roles": [role]
                    }

            project_dict['project_members'] = list(member_data.values())
            project_dict["project_clients"] = client_details

            res.append(project_dict)

        # Calculate total project count
        total_projects = len(project_ids_obj)

        # Calculate page count only if pagination is applied
        if page and page_size:
            total_pages = math.ceil(total_projects / page_size) if page_size > 0 else 0
        else:
            total_pages = 1  # Single page if no pagination

        response = {"data": res, "page_count": total_pages, "item_count": total_projects, "status": "Success"}

        # End the timer
        end_time = time.time()

        # Calculate total execution time
        execution_time = end_time - start_time
        print(f"Execution Time: {execution_time:.4f} seconds")

        return response

    except Exception as e:
        print(str(e))



async def assign_members_to_project(project_id: str, role_id: str, member_ids: str, db: Session, current_member: Members):
    """
    Assign multiple members to a project with a specific role.

    This function assigns members to a project based on the provided `role_id` and 
    `member_ids`. It retrieves the `member_role_id` using the `role_id` and `member_id` 
    from the `MemberRole` table and assigns members to the project.

    Parameters:
    - project_id (str): The unique identifier of the project.
    - role_id (str): The role ID to be assigned to the members.
    - member_ids (str): A comma-separated string of member IDs to be assigned to the project.
    - db (Session): The database session used for the transaction.
    - current_member (Members): The current authenticated member making the assignment.

    Returns:
    - JSONResponse: A JSON response indicating success or failure of the assignment.

    """
    try:
        # Ensure that any existing transactions are committed
        if db.in_transaction():
            db.commit()

        # Begin a transaction
        with db.begin():

            role = db.query(Roles).filter(Roles.id == role_id, Roles.is_active == True).first()
            role_name = role.name
            
            # IT SHOULD BE A MIDDLEWARE:
            # Check assign/unassign of member based on bid status.
            allowed_project_status = ["Pending", "In Progress"]
            allowed_bid_status = ["Bid Success", "Estimating"]
            chief_roles = ["Chief Estimator","Chief Project Manager"]
            bid_status_wise_allowed_roles = [
                {
                    "Bid Success": [
                        "Chief Project Manager",
                        "Project Manager",
                        "Hardware Consultant",
                        "Door Consultant",
                        "Shipping Personal",
                        "Receiving Personal",
                        "Accountant",
                        "Purchase Manager",
                        "Installation Personal"
                    ]
                }, 
                {
                    "Estimating": [
                        "Chief Estimator",
                        "Estimator"
                    ]
                }
            ]
            
            project_bid_status = (db.query(Projects.current_project_status, Projects.current_bid_status)
                .filter(Projects.id == project_id, Projects.is_active == True, Projects.is_deleted == False).first())
            

            current_project_status = project_bid_status.current_project_status
            current_bid_status = project_bid_status.current_bid_status

            
            # if current_project_status not in allowed_project_status:
            #     return JSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={"message": f"Members with the role '{role_name}' cannot be assigned or unassigned when the project status is '{current_project_status}"}
            #     )

            # if current_bid_status not in allowed_bid_status:
            #     return JSONResponse(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         content={"message": f"Members with the role '{role_name}' cannot be assigned or unassigned when the bid status is '{current_bid_status}'."}
            #     )

            for bid_status_wise_allowed_role in bid_status_wise_allowed_roles:
                # bid_status_wise_allowed_role[current_bid_status]
                # print(bid_status_wise_allowed_role[current_bid_status])
                for key, value in bid_status_wise_allowed_role.items():

                    # if key == current_bid_status and role_name not in value:
                    #     return JSONResponse(
                    #         status_code=status.HTTP_400_BAD_REQUEST,
                    #         content={"message": f"Member with role '{role_name}' cannot be assigned or unassigned when bid status is '{current_bid_status}'."}
                    #     )
                    # elif key == current_bid_status and role_name in value:
                    if role_name not in chief_roles:
                        chief_role = value[0]

                        chief_estimator_assigned = (db.query(ProjectMembers)
                            .join(MemberRole)
                            .join(Roles)
                            .filter(ProjectMembers.project_id == project_id, Roles.name == chief_role)).first()
                        
                        if not chief_estimator_assigned:
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={"message": f"The '{chief_role}' must be assigned first"}
                            )

            # Convert the comma-separated string into a list of member IDs
            member_ids_list = [id.strip() for id in member_ids.split(",") if id.strip()] if member_ids else []

            # Check uniqueness of "Chief Estimator" & "Chief Project Manager" for a particular project.
            role_list = ['Chief Estimator', 'Chief Project Manager']
            if role_name in role_list:
                if len(member_ids_list) == 0:
                    return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": f"There must be at least one '{role_name}' assigned to the project."}
                )
                elif len(member_ids_list) > 1:
                    return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": f"Each project must have one '{role_name}' assigned."}
                )

            if not member_ids:
                query = (
                    db.query(MemberRole.id, Roles.name)
                    .join(Roles, Roles.id == MemberRole.role_id)
                    .filter(MemberRole.role_id == role_id)
                    .all()
                )

                if query:
                    
                    member_role_ids_list = []
                    member_role_name = []
                    for data in query:
                        member_role_ids_list.append(data.id)
                        member_role_name.append(data.name)
                    # Delete ProjectMembers associated with the  member_role_ids
                    db.query(ProjectMembers) \
                        .filter(ProjectMembers.member_role_id.in_(member_role_ids_list)) \
                        .filter(ProjectMembers.project_id == project_id) \
                        .delete(synchronize_session=False)
                    
                    # Check if the role is "project manager" and member is going to unassigned, after unassigned the member from the
                    # projet we need to change the project status from "In Progress" to "Pending".
                    if member_role_name[0] == "Chief Project Manager":
                        db.query(Projects).filter(Projects.id == project_id).update({'current_project_status': 'Pending'})
                        # We are going to insert the log data to the "project_logs" table.
                        current_project_status = "Pending"
                        status_data = db.query(Status).filter(Status.category == "PROJECT_STATUS", Status.type == current_project_status).first()
                        status_id = status_data.id

                        await insert_project_logs(db,current_member,project_id,status_id,status_type="PROJECT_STATUS")

                return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Data submitted successfully", "status": "success"})
            

            unassign_member_role_data = (

                    db.query(MemberRole)
                    .filter(MemberRole.role_id == role_id)
                    .filter(~MemberRole.member_id.in_(member_ids_list))
                    .all()
                )
            if unassign_member_role_data:
                member_role_ids = [str(data.id) for data in unassign_member_role_data]

                # Delete ProjectMembers associated with the unassigned member_role_ids
                db.query(ProjectMembers) \
                    .filter(ProjectMembers.member_role_id.in_(member_role_ids)) \
                    .filter(ProjectMembers.project_id == project_id) \
                    .delete(synchronize_session=False)

            
            # Retrieve the member_role_id using the role_id and member_id
            member_roles = (
                db.query(MemberRole)
                .filter(MemberRole.role_id == role_id)
                .filter(MemberRole.member_id.in_(member_ids_list))
                .all()
            )

            for member_role in member_roles:

                # Check if the member is already assigned to the project with this role
                existing_member = (
                    db.query(ProjectMembers)
                    .filter(ProjectMembers.member_role_id == member_role.id)
                    .filter(ProjectMembers.project_id == project_id)
                    .first()
                )

                if not existing_member:
                    project_member = ProjectMembers(
                        member_role_id=member_role.id,
                        project_id=project_id,
                        is_active=True,
                        created_by=current_member.id
                    )
                    db.add(project_member)

                    if role_name == "Chief Project Manager":
                        db.query(Projects).filter(Projects.id == project_id).update({'current_project_status': 'In Progress', 'priority': 3, 'is_estimation': False})
                        # We are going to insert the log data to the "project_logs" table.
                        current_project_status = "In Progress"
                        status_data = db.query(Status).filter(Status.category == "PROJECT_STATUS", Status.type == current_project_status).first()
                        status_id = status_data.id

                        await insert_project_logs(db,current_member,project_id,status_id,status_type="PROJECT_STATUS")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Data submitted successfully", "status": "success"})

    except IntegrityError as e:
        db.rollback()
        logger.exception(f"Database integrity error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database integrity error occurred.")

    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    finally:
        db.commit()

async def get_unassigned_members(project_id: str, role_id: str, db: Session):
    """
    Get a list of members who are not yet assigned to the project with the specified role.

    Parameters:
    - project_id (str): The unique identifier of the project.
    - role_id (str): The role ID for which unassigned members are to be fetched.
    - db (Session): The database session used for querying.

    Returns:
    - List[Dict[str, str]]: A list of dictionaries, each containing the `id` and `member_name` of an unassigned member.
    """
    try:

        subquery = (
            db.query(ProjectMembers.member_role_id)
            .filter(ProjectMembers.project_id == project_id)
        ).subquery()

        unassigned_members = (
            db.query(
                Members.id.label("member_id"),
                (Members.first_name + " " + Members.last_name).label("member_name")
            )
            .join(MemberRole, Members.id == MemberRole.member_id)
            .filter(
                MemberRole.role_id == role_id,
                ~MemberRole.id.in_(subquery)  # SQLAlchemy's equivalent of `NOT IN`
            )
        ).all()
        
        response = [{"id": member.member_id, "name": member.member_name} for member in unassigned_members]

        return {"data": response, "status": "success"}

    except Exception as error:
        logger.exception(f"An error occurred while fetching unassigned members: {error}")
        raise Exception("Internal server error")


async def get_assigned_members(project_id: str, role_id: str, db: Session):
    """
    Get a list of members who are assigned to the project with the specified role.

    Parameters:
    - project_id (str): The unique identifier of the project.
    - role_id (str): The role ID for which assigned members are to be fetched.
    - db (Session): The database session used for querying.

    Returns:
    - List[Dict[str, str]]: A list of dictionaries, each containing the `id` and `member_name` of an assigned member.
    """
    try:
        unassigned_members = (
            db.query(
                Members.id.label("member_id"),
                (Members.first_name + " " + Members.last_name).label("member_name")
            )
            .join(MemberRole, MemberRole.member_id == Members.id)
            .join(ProjectMembers, ProjectMembers.member_role_id == MemberRole.id)
            .filter(ProjectMembers.project_id == project_id)
            .filter(MemberRole.role_id == role_id)
            .group_by(Members.id, Members.first_name, Members.last_name)
            .all()
        )

        response = [{"id": member.member_id, "name": member.member_name} for member in unassigned_members]

        return {"data": response, "status": "success"}

    except Exception as error:
        logger.exception(f"An error occurred while fetching unassigned members: {error}")
        raise Exception("Internal server error")


async def get_project_members_with_roles(
    db: Session,
    project_id: str,
    current_member: Members,
    role_names: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    keyword: Optional[str] = None,
    
):
    """
    **Summary:**
    Retrieve project members along with their roles, ensuring no duplicate members are returned.

    **Args:**
    - `db` (Session): The database session.
    - `project_id` (str): The ID of the project.
    - `role_names` (Optional[str]): A comma-separated string of role names to filter members by.
    - `page` (Optional[int]): The page number for pagination.
    - `page_size` (Optional[int]): The number of items per page.
    - `keyword` (Optional[str]): A keyword to filter members by their names.

    **Returns:**
    - dict: A dictionary containing the paginated project members with their roles, page count, item count, and status.
    """
    try:

        role_details = await get_role_by_id(db, member_id = current_member.id, active_role = True)
        allowed_roles = await get_allowed_roles_by_name(db, role_name = role_details[0]['name'], sub_module_label = "Tasks")
        query = (
            db.query(ProjectMembers, Roles, MemberRole)
            .join(MemberRole, ProjectMembers.member_role_id == MemberRole.id)
            .join(Roles, MemberRole.role_id == Roles.id)
            .join(Members, MemberRole.member_id == Members.id)
            .filter(
                ProjectMembers.project_id == project_id,
                Roles.name.in_(allowed_roles)
            )
        )

        if role_names:
            role_names_list = role_names.split(',')
            query = query.filter(Roles.name.in_(role_names_list), Roles.is_active == True)
        
        if keyword:
            search_term = f"%{keyword}%"
            query = query.filter(
                or_(
                    Members.first_name.ilike(search_term),
                    Members.last_name.ilike(search_term),
                    (Members.first_name + " " + Members.last_name).ilike(search_term)
                )
            )

        # Get the total count of items
        item_count = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = item_count if item_count else 1
            page = 1

        project_members = query.all()
        member_roles_map = {}

        for project_member, role, member_role in project_members:
            member = member_role.member
            member_id = member_role.member_id
            member_name = f"{member.first_name} {member.last_name}".strip()

            if member_id in member_roles_map:
                member_roles_map[member_id]["roles"].append({
                    "id": role.id,
                    "role_name": role.name,
                    "member_role_id": member_role.id
                })
            else:
                member_roles_map[member_id] = {
                    "member_id": member_id,
                    "member_name": member_name,
                    "roles": [{
                        "id": role.id,
                        "role_name": role.name,
                        "member_role_id": member_role.id
                    }]
                }

        result = list(member_roles_map.values())

        # Calculate the total number of pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        return {
            "data": result,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_project_info(db: Session, project_id: str):
    """Retrieve the current status of a project by project ID."""
    try:
        # Validate project_id
        if not project_id:
            return JSONResponse(
                content={"message": "Invalid project_id provided."},
                status_code=400,
            )

        # Query the project status from the database
        project = (
            db.query(Projects)
            .filter(Projects.id == project_id, Projects.is_deleted == False)
            .first()
        )

        # Check if the project exists
        if not project:
            return JSONResponse(
                content={"message": "Project not found."},
                status_code=404,
            )

        # Convert the project object to a dictionary using the to_dict property
        project_data = project.to_dict

        # Return the project data as JSON
        return JSONResponse(content=project_data, status_code=200)

    except Exception as e:
        logger.exception(f"Error retrieving project information: {e}")
        return JSONResponse(
            content={"error": "An unexpected error occurred while retrieving project data."},
            status_code=500,
        )

async def get_members(
    db: Session,
    page: int,
    page_size: int,
    keyword: str,
    project_id: str,
    role_id: str,
):
    """
    Retrieve a paginated list of members with keyword, role, and project filtering.

    Args:
        db (Session): Database session.
        page (int): Page number.
        page_size (int): Number of items per page.
        keyword (str): Search keyword for first name, last name, or email.
        project_id (str): Project ID to filter members belonging to a project.
        role_id (str): Role ID to filter members by specific role.

    Returns:
        dict: A dictionary containing paginated member data and metadata.
    """
    try:
        # Pagination calculation
        if page_size:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = db.query(Members).filter(Members.is_deleted == False).count()
            page = 1

        # Subquery for member IDs
        subquery = db.query(cast(Members.id, String)).filter(Members.is_deleted == False)

        if keyword:
            subquery = subquery.filter(
                or_(
                    Members.first_name.ilike(f"%{keyword}%"),
                    Members.last_name.ilike(f"%{keyword}%"),
                    Members.email.ilike(f"%{keyword}%"),
                )
            )

        # Both role_id and project_id are required → single join path
        subquery = (
            subquery.join(MemberRole, Members.id == MemberRole.member_id)
            .join(ProjectMembers, MemberRole.id == ProjectMembers.member_role_id)
            .filter(
                MemberRole.role_id == role_id,
                ProjectMembers.project_id == project_id,
            )
        )

        # Paginate
        subquery_result = (
            subquery.order_by(Members.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        member_ids = [str(row[0]) for row in subquery_result]

        if page_size is None:
            page_size = len(member_ids)

        # Count items
        item_count = len(member_ids)

        # Main query to fetch full member data
        member_items = (
            db.query(Members)
            .outerjoin(MemberRole, Members.id == MemberRole.member_id)
            .outerjoin(Roles, Roles.id == MemberRole.role_id)
            .outerjoin(RolePermissions, RolePermissions.role_id == MemberRole.role_id)
            .outerjoin(SubModules, RolePermissions.sub_module_id == SubModules.id)
            .outerjoin(Modules, Modules.id == SubModules.module_id)
            .outerjoin(ProjectMembers, MemberRole.id == ProjectMembers.member_role_id)
            .outerjoin(
                Projects,
                (Projects.id == ProjectMembers.project_id)
                & (Projects.is_deleted == False)
                & (Projects.is_active == True),
            )
            .filter(
                Members.is_deleted == False,
                Members.id.in_(member_ids),
            )
            .order_by(Members.created_at.asc(), Modules.sort_order.asc(), SubModules.sort_order.asc())
            .all()
        )

        # Build response
        member_data = []
        for member in member_items:
            temp = member.to_dict
            temp["name"] = f"{temp['first_name']} {temp['last_name']}"
            temp["permissions"] = []

            for member_role in member.member_roles:
                for role_sub_module in member_role.role.role_sub_modules:
                    sub_module_data = role_sub_module.sub_module.to_dict
                    sub_module_data["is_read"] = role_sub_module.is_read
                    sub_module_data["is_write"] = role_sub_module.is_write
                    sub_module_data["is_delete"] = role_sub_module.is_delete

                    module_data = role_sub_module.sub_module.module.to_dict
                    existing_module = next(
                        (m for m in temp["permissions"] if m["id"] == module_data["id"]),
                        None,
                    )

                    if existing_module:
                        if all(sm["id"] != sub_module_data["id"] for sm in existing_module["sub_modules"]):
                            existing_module["sub_modules"].append(sub_module_data)
                    else:
                        module_data["sub_modules"] = [sub_module_data]
                        temp["permissions"].append(module_data)

            member_data.append(temp)

        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0

        return {
            "data": member_data,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success",
        }

    except Exception as error:
        logger.exception("get_members:: error - " + str(error))
        raise error

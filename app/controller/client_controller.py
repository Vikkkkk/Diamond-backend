"""
This module containes all logical operation and db operations those are related to clients add/update/read/delete.
"""
from datetime import datetime
from loguru import logger
from models.clients import Clients
from models.client_projects import ClientProjects
from models.projects import Projects
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from fastapi.responses import JSONResponse
import math
from utils.common import get_user_time
from sqlalchemy.orm import Session
from schemas.client_schemas import Client
from models.members import Members
from sqlalchemy import func


async def get_clients(
    db: Session, 
    page: int, 
    page_size: int, 
    keyword: str = None,
    project_id: str = None,
):
    try:
        base_query = db.query(Clients).filter(Clients.is_deleted == False)

        # Pagination setup
        if page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = base_query.count()
            page_size = limit

        item_query = base_query

        # Get total count
        item_count = base_query.count()

        # Apply keyword filter if keyword is provided
        if keyword:
            keyword_filter = or_(
                Clients.name.ilike(f'%{keyword}%'),
                Clients.email.ilike(f'%{keyword}%')
            )
            item_query = item_query.filter(keyword_filter)
            item_count = item_query.count()

        # Apply project filter if project_id is provided
        if project_id:
            item_query = item_query.join(ClientProjects, Clients.id == ClientProjects.client_id)
            item_query = item_query.filter(ClientProjects.project_id == project_id)
            item_count = item_query.count()

        # Fetch items with pagination
        items = item_query.order_by(Clients.created_at.asc()).offset(skip).limit(limit).all()

        # Get client IDs
        client_ids = [client.id for client in items]

        # Fetch total project count for each client
        project_count_dict = {}
        if client_ids:
            project_counts = (
                db.query(ClientProjects.client_id, func.count(ClientProjects.project_id).label("project_count"))
                .filter(ClientProjects.client_id.in_(client_ids))
                .group_by(ClientProjects.client_id)
                .all()
            )
            project_count_dict = {row.client_id: row.project_count for row in project_counts}

        # Build enriched response list with total_project_count
        enriched_clients = []
        for client in items:
            enriched_clients.append({
                "id": client.id,
                "name": client.name,
                "contact_name": client.contact_name,
                "email": client.email,
                "phone": client.phone,
                "fax": client.fax,
                "website": client.website,
                "street_address": client.street_address,
                "province": client.province,
                "country": client.country,
                "postal_code": client.postal_code,
                "note": client.note,
                "is_active": client.is_active,
                "is_deleted": client.is_deleted,
                "created_at": client.created_at,
                "created_by": client.created_by,
                "updated_at": client.updated_at,
                "updated_by": client.updated_by,
                "deleted_at": client.deleted_at,
                "deleted_by": client.deleted_by,
                "total_project_count": project_count_dict.get(client.id, 0)
            })

        # Calculate total pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0

        # Prepare final response
        response = {
            "data": enriched_clients,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

        return response

    except Exception as e:
        logger.exception("get_clients:: error - " + str(e))
        raise e



async def get_client(db: Session, id: str):
    """**Summary:**
    This method is responsible for retreaving the details of the input client id

    **Args:**
        - db (Session): db session referance
        - id (String): client Id for which it will run the fetch query

    """
    try:
        client = (db.query(Clients).outerjoin(ClientProjects).filter(Clients.id == id, Clients.is_deleted == False).first())
        client = client.to_dict
        return  {"data": client, "status": "success"}

    except Exception as e:
        logger.exception("get_client:: error - " + str(e))
        raise e
        
async def create_client(db: Session, client_data: Client, current_member: Members):
    """**Summary:**
    This method takes single client data as input, it check if the client is already exists or not,
    depending on its email, phone, website. If not exists then add the client to the DB

    **Args:**
        - data (Client): Client data. reffer to the client schema for the structure
        - db (Session): db session referance
        - current_member (Members): This will contain member details of current loggedin member.
    """
    # Check uniqueness before inserting
    client_data = client_data.dict()
    if not db.query(Clients).filter(or_(Clients.email==client_data["email"], Clients.phone==client_data["phone"])).first():
        try:
            # client_id = generate_uuid()
            # client_data['id'] = client_id
            client_data['created_by'] = current_member.id
            new_client = Clients(**client_data)
            db.add(new_client)
            db.commit()
            client_id = new_client.id
            return {"id": client_id,"message": "Data inserted successfully.", "status": "success"}
        except IntegrityError as i_error:
            logger.exception(f"IntegrityError: {i_error}")
            db.rollback()
            raise i_error
        except Exception as error:
            logger.exception(f"An unexpected error occurred: {error}")
            db.rollback()
            raise error
    else:
        return JSONResponse(content={"message": "Email or phone number already exists."}, status_code=400)



async def delete_client_soft(db: Session, id: str, current_member: Members):
    """
    Soft delete a client by updating the is_deleted flag.
    Args:
        db (Session): DB session reference.
        id (int): The unique identifier of the client to be soft deleted.
        current_member (Members): This will contain member details of current loggedin member.
    """
    client_exist = db.query(Clients).filter(Clients.id == id, Clients.is_deleted == False).first()
    if client_exist:
        client = db.query(Clients).get(id)
        client.is_deleted = True
        client.deleted_at = datetime.now()
        client.deleted_by = current_member.id
        db.commit()
        return {"message": "Data deleted successfully.", "status": "success"}
    else:
        return JSONResponse(content={"message": "Client not found"}, status_code=400)
    


async def update_client(db: Session, id: str, client_data: Client, current_member: Members):
    """**Summary:**
    This method updates client data based on the provided client ID.

    **Args:**
        - db (Session): db session reference
        - id (int): ID of the client to be updated
        - client_data (Client): Updated client data. Refer to the client schema for the structure
        - current_member (Members): This will contain member details of current loggedin member.
    """
    try:
        existing_client = db.query(Clients).filter(Clients.id == id, Clients.is_deleted == False).first()

        if existing_client:
            client_data = client_data.model_dump(exclude_unset=True)
            if "email" in client_data:
                duplicate_client = (
                    db.query(Clients)
                    .filter(
                        or_(Clients.email == client_data['email'],
                        Clients.phone == client_data['phone']),
                        Clients.id != id,
                        Clients.is_deleted==False
                    )
                    .first()
                )
                if duplicate_client:
                    return JSONResponse(content={"message": "Email or phone number already exists."},\
                                        status_code=400)
            # Update existing client data
            client_data['updated_by'] = current_member.id
            # Update the attributes of the existing client with the values from the client_data dictionary.
            for key, value in client_data.items():
                setattr(existing_client, key, value)
            db.commit()
            return {"message": f"Client updated successfully.", "status": "success"}
            
        else:
            return JSONResponse(content={"message": f"Client not found."}, status_code=400)

    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
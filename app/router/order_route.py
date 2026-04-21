from typing import List, Union, Optional
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File, HTTPException
from starlette import status
from middleware.user_authorization_middleware import admin_required
from models import get_db
from models.members import Members
# from schemas.project_schemas import Project
from schemas.project_details_schema import ProjectResponse, ProjectsResponse, ProjectModuleMemberResponse
from schemas.project_status_logs_schema import ProjectStatusLogs
from controller import order_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required
from schemas.ordered_item_schema import OrderRequest, ActivePoInsertRequest, ActivePoUpdateRequest, UpdatePOItemsStatusRequest, RequestShipItems
from datetime import datetime
import traceback

router = APIRouter(prefix="/order", tags=["Order APIs"])


@router.get("/{project_id}/get_unrequested_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_unrequested_items(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    component_type: str = Query(title="Component Type", description="The type of the component i.e. 'DOOR', 'FRAME', 'HARDWARE'"),
    keyword: str = Query(None, alias="keyword"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve unrequested items for a given project based on component type.

    This endpoint fetches unrequested items associated with the specified project.
    The type of component requested must be one of the following: 'DOOR', 'FRAME', or 'HARDWARE'.
    It requires authentication and checks the current member's permissions before
    accessing the database.

    Args:
    - project_id (str): The unique identifier of the project.
    - component_type (str): The type of the component ('DOOR', 'FRAME', or 'HARDWARE').
    - keyword (str, optional): A keyword for filtering the unrequested items (if applicable).
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the unrequested items or an error message.

    Raises:
    - ValueError: If an invalid component type is provided.
    - Exception: If an error occurs during data retrieval.
    """
    try:
        allowed_types = {"DOOR", "FRAME", "HARDWARE"}
        if component_type not in allowed_types:
            raise ValueError(f"Invalid component type: {component_type}. Allowed types: {allowed_types}")
        
        if component_type == "DOOR":
            return await order_controller.get_unrequested_door(db, project_id)
        if component_type == "FRAME":
            return await order_controller.get_unrequested_frame(db, project_id)
        if component_type == "HARDWARE":
            return await order_controller.get_unrequested_hardware(db, project_id)
        
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/request_order", status_code=status.HTTP_200_OK)
@logger.catch
async def request_order(
    data: OrderRequest,
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Submit a request for an order within a given project.

    This endpoint allows a project member to request an order for materials, hardware, 
    or other project-related items. The request is processed and stored in the database.

    Args:
    - data (OrderRequest): The order request payload containing order details.
    - project_id (str): The unique identifier of the project.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object confirming the order request or an error message.

    Raises:
    - Exception: If an error occurs during order processing.
    """
    try:
        return await order_controller.request_order(db, project_id, data)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.post("/{project_id}/update_request_order", status_code=status.HTTP_200_OK)
@logger.catch
async def update_request_order(
    data: OrderRequest,
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Submit a request for an order within a given project.

    This endpoint allows a project member to request an order for materials, hardware, 
    or other project-related items. The request is processed and stored in the database.

    Args:
    - data (OrderRequest): The order request payload containing order details.
    - project_id (str): The unique identifier of the project.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object confirming the order request or an error message.

    Raises:
    - Exception: If an error occurs during order processing.
    """
    try:
        return await order_controller.update_request_order(db, project_id, data)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_requested_orders", status_code=status.HTTP_200_OK)
@logger.catch
async def get_requested_orders(
    project_id: str = Path(title="Project ID", description="The ID of the project"),
    component_type: str = Query(title="Component Type", description="The type of the component"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve all requested orders for a given project.

    This endpoint fetches a list of requested orders based on the specified project ID
    and component type. It requires authentication and checks the current member's permissions 
    before accessing the database.

    Args:
    - project_id (str): The unique identifier of the project.
    - component_type (str): The type of component for which orders are requested (e.g., hardware, doors, frames).
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the requested order data or an error message.

    Raises:
    - Exception: If an error occurs during data retrieval.
    """
    try:
        return await order_controller.get_requested_orders(db, project_id, component_type)
    except Exception as error:
        print(traceback.format_exc)
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/get_requested_grouped_orders", status_code=status.HTTP_200_OK)
@logger.catch
async def get_requested_grouped_orders(
    db: Session = Depends(get_db),
    component_type: str = Query(title="Component Type", description="The type of the component i.e. 'DOOR', 'FRAME', 'HARDWARE'"),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve requested grouped orders based on component type.

    This endpoint fetches grouped orders that have been requested for a given component type.
    The component type must be one of the following: 'DOOR', 'FRAME', or 'HARDWARE'.
    It requires authentication and checks the current member's permissions before
    accessing the database.

    Args:
    - db (Session): Database session dependency.
    - component_type (str): The type of the component ('DOOR', 'FRAME', or 'HARDWARE').
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the requested grouped orders or an error message.

    Raises:
    - ValueError: If an invalid component type is provided.
    - Exception: If an error occurs during data retrieval.
    """
    try:
        allowed_types = {"DOOR", "FRAME", "HARDWARE"}
        if component_type not in allowed_types:
            raise ValueError(f"Invalid component type: {component_type}. Allowed types: {allowed_types}")
        
        if component_type == "DOOR":
            return await order_controller.get_door_requested_grouped_orders(db)
        if component_type == "FRAME":
            return await order_controller.get_frame_requested_grouped_orders(db)
        if component_type == "HARDWARE":
            return await order_controller.get_hwd_requested_grouped_orders(db)
    except Exception as error:
        print(traceback.format_exc)
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

    
@router.post("/purchase_order", status_code=status.HTTP_200_OK)
@logger.catch
async def purchase_order(
    data: ActivePoInsertRequest,
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Create a new purchase order.

    This endpoint allows a project member to create and submit a purchase order (PO) 
    for requested materials, hardware, or other project-related items. 
    The request is processed and stored in the database.

    Args:
    - data (ActivePoRequest): The purchase order request payload containing PO details.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object confirming the purchase order creation or an error message.

    Raises:
    - Exception: If an error occurs during purchase order processing.
    """
    try:
        return await order_controller.purchase_order(data, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/{active_po_id}/_modify_purchase_order", status_code=status.HTTP_200_OK)
@logger.catch
async def modify_purchase_order(
    data: ActivePoUpdateRequest,
    active_po_id: str = Path(title="Active PO ID", description="The ID of the Active PO"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Create a new purchase order.

    This endpoint allows a project member to create and submit a purchase order (PO) 
    for requested materials, hardware, or other project-related items. 
    The request is processed and stored in the database.

    Args:
    - data (ActivePoRequest): The purchase order request payload containing PO details.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object confirming the purchase order creation or an error message.

    Raises:
    - Exception: If an error occurs during purchase order processing.
    """
    try:
        return await order_controller.modify_purchase_order(active_po_id, data, db)
    except Exception as error:
        print(str(error))
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_purchase_orders", status_code=status.HTTP_200_OK)
@logger.catch
async def get_purchase_orders(
    component_type: str = Query(title="Component Type", description="The type of the component"),
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve a list of purchase orders for a given project.

    This endpoint fetches purchase orders associated with a specified project ID and component type.
    It requires authentication and verifies the current member’s permissions before accessing the database.

    Args:
    - component_type (str): The type of component for which purchase orders are requested 
                              (e.g., HARDWARE, DOOR, FRAME).
    - project_id (str): The unique identifier of the project.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the list of purchase orders or an error message.

    Raises:
    - Exception: If an error occurs during data retrieval.
    """
    try:
        return await order_controller.get_purchase_order_list(project_id, component_type, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/get_active_purchase_orders", status_code=status.HTTP_200_OK)
@logger.catch
async def get_active_purchase_order_list(
    component_type: str = Query(title="Component Type", description="The type of the component"),
    project_id: str = Query(None, title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve a list of active purchase orders.

    This endpoint fetches active purchase orders based on the specified component type. 
    Optionally, the results can be filtered by a specific project ID. 
    It requires authentication and verifies the current member’s permissions before 
    accessing the database.

    Args:
    - component_type (str): The type of component for which active purchase orders are requested 
                              (e.g., hardware, doors, frames).
    - project_id (str, optional): The unique identifier of the project. If not provided, 
                                    purchase orders for all projects will be retrieved.
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the list of active purchase orders or an error message.

    Raises:
    - Exception: If an error occurs during data retrieval.
    """
    try:
        return await order_controller.get_active_purchase_order_list(db, component_type, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{active_po_id}/get_active_purchase_order_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_active_purchase_order_items(
    active_po_id: str = Path(title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve active purchase order items for a given project.

    **Args:**
    - active_po_id (str): The ID of the active purchase order.
    - db (Session): The database session dependency.
    - current_member (Members): The currently authenticated user.

    **Returns:**
    - JSONResponse: A structured JSON response containing the active purchase order items.

    **Raises:**
    - HTTPException (500): If an unexpected error occurs.

    **Example Response:**
    ```json
    {
        "status": "success",
        "message": "Active purchase order items retrieved successfully.",
        "data": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "po_number": "PO123456",
                "material": "Steel Plates",
                "quantity": 500,
                "final_price": 1200.50,
                "created_at": "2025-03-10T10:00:00"
            }
        ],
        "total_records": 1
    }
    ```
    """
    try:
        return await order_controller.get_active_purchase_order_item_list(db, active_po_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.patch("/po-items/{active_po_id}/update_po_status", status_code=status.HTTP_200_OK)
@logger.catch
async def update_po_status(
    data: UpdatePOItemsStatusRequest,
    active_po_id: str = Path(title="Active PO ID", description="The Active PO ID of the Orders"),
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    """
    Update the status of purchase order (PO) items.

    **Args:**
    - data (UpdatePOItemsStatusRequest): The request payload containing PO item status updates.
    - db (Session): The database session dependency.
    - current_member (Members): The currently authenticated user.

    **Returns:**
    - JSONResponse: A structured JSON response indicating the update status.

    **Raises:**
    - HTTPException (400): If invalid PO item IDs are provided or status validation fails.
    - HTTPException (500): If a database error or unexpected exception occurs.

    **Example Request:**
    ```json
    {
        "order_items": {
            "550e8400-e29b-41d4-a716-446655440000": {
                "is_received": true,
                "is_missing": false,
                "is_damaged": false
            },
            "720e5400-e49b-42d5-b726-556655441111": {
                "is_received": false,
                "is_missing": true,
                "is_damaged": false
            }
        }
    }
    ```

    **Example Response:**
    ```json
    {
        "status": "success",
        "message": "PO status updated successfully."
    }
    ```
    """
    try:
        return await order_controller.update_po_status(db, data, active_po_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/{active_po_id}/active-po-details/", status_code=status.HTTP_200_OK)
@logger.catch
async def get_active_po(
    active_po_id: str = Path(title="Active PO ID", description="The Active PO ID of the Orders"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    Retrieve details of an active purchase order (PO).

    **Args:**
    - active_po_id (str): The unique identifier of the active purchase order.
    - db (Session): The database session dependency.
    - current_member (Members): The currently authenticated user.

    **Returns:**
    - JSONResponse: A structured JSON response containing active PO details.

    **Raises:**
    - HTTPException (404): If the active PO is not found.
    - HTTPException (500): If a database error or unexpected exception occurs.

    **Example Request:**
    ```
    GET /{active_po_id}/active-po-details/
    ```

    **Example Response:**
    ```json
    {
        "status": "success",
        "message": "Active PO details retrieved successfully.",
        "data": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "po_number": "PO123456",
            "company_address": "123 Main St, NY",
            "customer": "ABC Corp",
            "order_contact": "John Doe",
            "order_contact_email": "john.doe@example.com",
            "ordered_date": "2025-03-10",
            "final_price": 5000.00,
            "status": "Pending"
        }
    }
    ```
    """
    try:
        return await order_controller.get_active_po(db, active_po_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/ordered-item-docs/upload/", status_code=201)
async def upload_ordered_item_docs(
    order_item_id: str = Form(..., description="ID of the ordered item"),
    files: list[UploadFile] = File(..., description="List of files to upload"),
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member)
):
    """
    **Upload Multiple Ordered Item Documents**
    
    This API uploads multiple documents related to an ordered item and stores metadata in the database as wel as in the  AWS S3
    
    **Request:**
    - `order_item_id` (str): ID of the ordered item.
    - `files` (list[UploadFile]): List of files to upload.

    **Response:**
    - Success: {"message": "Files uploaded successfully", "documents": [{...}]}
    - Failure: HTTP 400 or 500 error.
    """
    try:
        return await order_controller.upload_ordered_item_docs(db, order_item_id, files)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/ordered-item-docs/{order_item_id}", status_code=200)
async def list_ordered_item_docs(
    order_item_id: str,
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)

):
    """
    **Retrieve Ordered Item Documents**
    
    Fetches all documents associated with a given `order_item_id`.

    **Path Parameter:**
    - `order_item_id` (str): The ID of the ordered item.

    **Response:**
    - Success: Returns a list of documents with metadata.
    - Failure: HTTP 404 if no documents are found.
    """
    try:
        return await order_controller.list_ordered_item_docs(db, order_item_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.delete("/ordered-item-docs/{document_id}", status_code=200)
async def delete_ordered_item_doc(
    document_id: str,
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    **Delete an Ordered Item Document**
    
    Deletes a document from the database and from AWS S3 based on its `document_id`.

    **Path Parameter:**
    - `document_id` (str): The ID of the document to be deleted.

    **Response:**
    - Success: Returns a success message.
    - Failure: HTTP 404 if the document is not found.
    """
    try:
        return await order_controller.delete_ordered_item_doc(db, document_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_received_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_received_items(
    component_type: str = Query(..., title="Component Type", description="The type of the component"),
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve received items for a given project and component type.

    This endpoint fetches all ordered items that have been marked as received 
    for a specific project and component type.

    Args:
        component_type (str): The type of component (e.g., "DOOR" or "FRAME").
        project_id (str): The unique identifier of the project.
        db (Session): The database session dependency.
        current_member (Members): The authenticated user making the request.

    Returns:
        JSONResponse: A JSON object containing the received items or an error message 
                      if the retrieval fails.

    Raises:
        HTTPException (500): If an unexpected error occurs during retrieval.
    """
    try:
        return await order_controller.get_received_items(project_id, component_type, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/{project_id}/request_ship_items", status_code=status.HTTP_200_OK)
@logger.catch
async def request_ship_items(
    request_payload: RequestShipItems,
    component_type: str = Query(None, title="Component Type", description="The type of the component"),
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    """
    Request shipment of ordered items for a given project and component type.

    This endpoint updates the shipping status of selected ordered items to "IN PROGRESS"
    for a specified project and component type.

    Args:
        request_payload (RequestShipItems): The request body containing a list of item IDs.
        component_type (str): The type of component (e.g., "DOOR" or "FRAME").
        project_id (str): The unique identifier of the project.
        db (Session): The database session dependency.
        current_member (Members): The authenticated user making the request.

    Returns:
        JSONResponse: A JSON object indicating the success of the operation, including 
                      updated item IDs, or an error message if the request fails.

    Raises:
        HTTPException (500): If an unexpected error occurs during processing.
    """
    try:
        return await order_controller.request_ship_items(project_id, component_type, request_payload, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_requested_shipping_grouped_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_requested_shipping_grouped_items(
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve grouped shipping items that have been requested.

    This endpoint fetches and returns shipping items that are currently 
    in the "IN PROGRESS" status, grouped by project details.

    Args:
        db (Session): The database session dependency.
        current_member (Members): The authenticated user making the request.

    Returns:
        JSONResponse: A JSON object containing the grouped shipping items 
                      or an error message if the operation fails.
    
    Raises:
        HTTPException (500): If an unexpected error occurs during retrieval.
    """
    try:
        return await order_controller.get_requested_shipping_grouped_items(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_shipping_grouped_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_shipping_grouped_items(
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    """
    Retrieve grouped shipping items that have been requested.

    This endpoint fetches and returns shipping items that are currently 
    in the "IN PROGRESS" status, grouped by project details.

    Args:
        db (Session): The database session dependency.
        current_member (Members): The authenticated user making the request.

    Returns:
        JSONResponse: A JSON object containing the grouped shipping items 
                      or an error message if the operation fails.
    
    Raises:
        HTTPException (500): If an unexpected error occurs during retrieval.
    """
    try:
        return await order_controller.get_shipping_grouped_items(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_shipped_grouped_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_shipped_grouped_items(
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    """
    Retrieve grouped shipping items that have been requested.

    This endpoint fetches and returns shipping items that are currently 
    in the "IN PROGRESS" status, grouped by project details.

    Args:
    - db (Session): The database session dependency.
    - current_member (Members): The authenticated user making the request.

    Returns:
    - JSONResponse: A JSON object containing the grouped shipping items 
                      or an error message if the operation fails.
    
    Raises:
    -  HTTPException (500): If an unexpected error occurs during retrieval.
    """
    try:
        return await order_controller.get_shipped_grouped_items(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.get("/{project_id}/get_shipped_items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_shipped_items(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    component_type: str = Query(title="Component Type", description="The type of the component"),
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    """
    Retrieve shipped items for a specific project.

    Args:
    - project_id (str): The unique identifier of the project.
    - component_type (str): The type of the component (e.g., "FRAME", "DOOR", "HARDWARE").
    - db (Session): Database session dependency.
    - current_member (Members): The authenticated user making the request.

    Returns:
    - JSONResponse | list[dict]: A list of shipped items matching the project and component type.
    
    Raises:
    - HTTPException (500): If an unexpected error occurs during retrieval.
    """
    try:
        return await order_controller.get_shipped_items(db, project_id, component_type)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_purchase_order_history", status_code=status.HTTP_200_OK)
@logger.catch
async def get_active_purchase_order_list(
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
):
    """
    Retrieve a list of purchase order history.

    This endpoint fetches active purchase orders based on the specified component type. 
    Optionally, the results can be filtered by a specific project ID. 
    It requires authentication and verifies the current member’s permissions before 
    accessing the database.

    Args:
    - db (Session): Database session dependency.
    - current_member (Members): The currently authenticated project member.

    Returns:
    - JSONResponse: A JSON object containing the list of active purchase orders or an error message.

    Raises:
    - Exception: If an error occurs during data retrieval.
    """
    try:
        return await order_controller.get_purchase_order_history(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_po_information", status_code=status.HTTP_200_OK)
@logger.catch
async def get_po_information(
    item_ids: str = Query(..., description="item ids"),
    component_type: str = Query(title="Component Type", description="The type of the component"),
    db: Session = Depends(get_db),
    # current_member: Members = Depends(get_current_member),
):
    try:
        return await order_controller.get_po_information(db, item_ids, component_type)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

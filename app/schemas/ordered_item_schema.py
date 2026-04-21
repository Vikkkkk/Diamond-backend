"""
This module containes all schemas those are related to permissions add/update/read/delete requests.
"""
from typing import List, Optional, Dict, Union, Any
from enum import Enum
from pydantic import BaseModel, Field, Json, root_validator
from uuid import UUID
from datetime import datetime, date


class COMPONENT_TYPE(str, Enum):
    """**Summary:**
    This class contains the schema of COMPONENT_TYPE
    """
    DOOR = 'DOOR'
    FRAME = 'FRAME'
    HARDWARE = 'HARDWARE'

class ShippingStatus(str, Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    AWAIT_SHIPPING = 'AWAIT_SHIPPING'

class OrderRequest(BaseModel):
    required_by_date: date = Field(..., description="Required completion date")
    component_type: COMPONENT_TYPE = Field(..., description="Type of component")
    schedule_ids: List[str] = Field(..., description="List of schedule IDs")


class OrderInsert(BaseModel):
    manufacturer_id: str = Field(..., description="ID of the manufacturer")
    manufacturer_name: str = Field(..., description="Name of the manufacturer")
    brand_id: Optional[str] = Field(None, description="ID of the brand")
    brand_name: Optional[str] = Field(None, description="Name of the brand")
    ordered_metadata: Dict[str, Any] = Field(..., description="Metadata related to the order")
    total_price: float = Field(..., description="Total price of the order")
    total_base_price: float = Field(..., description="Total base price of the order")
    quantity: int = Field(..., description="Quantity of items in the order")
    final_price: float = Field(..., description="Final calculated price of the order")
    final_base_price: float = Field(..., description="Final base price after calculations")
    project_id: str = Field(..., description="ID of the project")
    project_name: str = Field(..., description="Name of the project")
    project_number: str = Field(..., description="Code representing the project")
    schedule_id: str = Field(..., description="ID of the schedule")
    opening_number: str = Field(..., description="Opening number of the order")
    door_type: str = Field(..., description="Type of door in the order")
    hand: str = Field(..., description="Handing of the door")
    door_mat: str = Field(..., description="Material of the door")
    frame_mat: str = Field(..., description="Material of the frame")
    component_type: COMPONENT_TYPE = Field(..., description="Type of component being ordered")
    required_by_date: date = Field(..., description="Date when the order was placed")
    # estimated_delivery_date: date = Field(..., description="Estimated delivery date of the order")
    part_number: int = Field(None, description= "Part number")
    shipping_status: ShippingStatus


class ActivePoInsert(BaseModel):
    company_address: Optional[str] = Field(None, description="Company address")
    sold_to: str = Field(..., description="Sold to details")
    ship_to: str = Field(..., description="Shipping address")
    order_contact: str = Field(..., description="Order contact person")
    po_number: Optional[str] = Field(None, description="Purchase order number")
    required_by_date: Optional[Union[str, date]] = Field(None, description="Required by date for the order")
    order_contact_email: Optional[str] = Field(None, description="Email of the order contact")
    delivery_contact_phone: Optional[str] = Field(None, description="Delivery contact phone number")
    ordered_date: Optional[Union[str, date]] = Field(None, description="Datetime when the order was placed")
    material: Optional[str] = Field(None, description="Material details")
    quote: str = Field(..., description="Quote reference")
    scheduled_ship_date: Optional[Union[str, date]] = Field(None, description="Scheduled shipping date")
    customer: Optional[str] = Field(None, description="Customer name")
    description: Optional[str] = Field(None, description="Order description")
    po_acknowledgement: Optional[str] = Field(None, description="PO acknowledgment details")
    ship_via: str = Field(..., description="Shipping method")
    ship_instructions: Optional[str] = Field(None, description="Shipping instructions")
    order_type: str = Field(..., description="Order type")
    order_type_description: Optional[str] = Field(None, description="Order type description")
    carrier: Optional[str] = Field(None, description="Carrier details")
    service_center: Optional[str] = Field(None, description="Service center information")
    transfer_point_ship_via: Optional[str] = Field(None, description="Transfer point shipping method")
    transfer_point_carrier: Optional[str] = Field(None, description="Transfer point carrier")
    bundling_code: Optional[str] = Field(None, description="Bundling code")
    prepaid_collect_code_id: Optional[str] = Field(None, description="Prepaid collect code ID")
    is_job_site: bool = Field(False, description="Indicates if it is a job site order")

    class Config:
        from_attributes = True  # Enables loading from ORM or other objects' attributes
        json_schema_extra = {
            "examples": [
                {
                    "company_address": "123 Business St, NY",
                    "sold_to": "ABC Corp",
                    "ship_to": "XYZ Warehouse",
                    "po_number": "PO-12345",
                    "order_contact": "John Doe",
                    "required_by_date": "2024-09-15",
                    "order_contact_email": "johndoe@company.com",
                    "delivery_contact_phone": "+1-800-123-4567",
                    "ordered_date": "2024-09-01",
                    "material": "Steel Pipes",
                    "quote": "QT-45678",
                    "scheduled_ship_date": "2024-09-20",
                    "customer": "XYZ Inc.",
                    "description": "Order for construction materials",
                    "po_acknowledgement": "Acknowledged",
                    "ship_via": "FedEx",
                    "ship_instructions": "Handle with care",
                    "order_type": "Standard",
                    "order_type_description": "Regular customer order",
                    "carrier": "FedEx Freight",
                    "service_center": "SC-1234",
                    "transfer_point_ship_via": "UPS",
                    "transfer_point_carrier": "DHL",
                    "bundling_code": "BND-001",
                    "prepaid_collect_code_id": "ID0012",
                    "is_job_site": True,
                }
            ]
        }


class ActivePoInsertRequest(BaseModel):
    component_type: COMPONENT_TYPE = Field(..., description="Type of component")
    order_ids: List[str]
    po_info: ActivePoInsert



class ActivePoUpdate(BaseModel):
    company_address: Optional[str] = Field(None, description="Company address")
    sold_to: Optional[str] = Field(None, description="Sold to details")
    ship_to: Optional[str] = Field(None, description="Shipping address")
    po_number: Optional[str] = Field(None, description="Purchase order number")
    order_contact: Optional[str] = Field(None, description="Order contact person")
    required_by_date: Optional[Union[str, date]] = Field(None, description="Date required for the order")
    order_contact_email: Optional[str] = Field(None, description="Email of the order contact")
    delivery_contact_phone: Optional[str] = Field(None, description="Delivery contact phone number")
    purchase_order: Optional[str] = Field(None, description="Purchase order reference")
    ordered_date: Optional[Union[str, date]] = Field(None, description="Datetime when the order was placed")
    material: Optional[str] = Field(None, description="Material details")
    quote: Optional[str] = Field(None, description="Quote reference")
    scheduled_ship_date: Optional[Union[str, date]] = Field(None, description="Scheduled shipping date")
    customer: Optional[str] = Field(None, description="Customer name")
    description: Optional[str] = Field(None, description="Order description")
    po_acknowledgement: Optional[str] = Field(None, description="PO acknowledgment details")
    ship_via: Optional[str] = Field(None, description="Shipping method")
    ship_instructions: Optional[str] = Field(None, description="Shipping instructions")
    order_type: Optional[str] = Field(None, description="Order type")
    order_type_description: Optional[str] = Field(None, description="Order type description")
    carrier: Optional[str] = Field(None, description="Carrier details")
    service_center: Optional[str] = Field(None, description="Service center information")
    transfer_point_ship_via: Optional[str] = Field(None, description="Transfer point shipping method")
    transfer_point_carrier: Optional[str] = Field(None, description="Transfer point carrier")
    bundling_code: Optional[str] = Field(None, description="Bundling code")
    prepaid_collect_code_id: Optional[str] = Field(None, description="Prepaid collect code ID")
    is_job_site: Optional[bool] = Field(False, description="Indicates if it is a job site order")

    class Config:
        from_attributes = True  # Enables loading from ORM or other objects' attributes
        json_schema_extra = {
            "examples": [
                {
                    "company_address": "123 Business St, NY",
                    "sold_to": "ABC Corp",
                    "ship_to": "XYZ Warehouse",
                    "po_number": "PO-12345",
                    "order_contact": "John Doe",
                    "required_by_date": "2024-09-15",
                    "order_contact_email": "johndoe@company.com",
                    "delivery_contact_phone": "+1-800-123-4567",
                    "ordered_date": "2024-09-01",
                    "material": "Steel Pipes",
                    "quote": "QT-45678",
                    "scheduled_ship_date": "2024-09-20",
                    "customer": "XYZ Inc.",
                    "description": "Order for construction materials",
                    "po_acknowledgement": "Acknowledged",
                    "ship_via": "FedEx",
                    "ship_instructions": "Handle with care",
                    "order_type": "Standard",
                    "order_type_description": "Regular customer order",
                    "carrier": "FedEx Freight",
                    "service_center": "SC-1234",
                    "transfer_point_ship_via": "UPS",
                    "transfer_point_carrier": "DHL",
                    "bundling_code": "BND-001",
                    "prepaid_collect_code_id": "ID1001",
                    "is_job_site": True,
                }
            ]
        }


class ActivePoUpdateRequest(BaseModel):
    component_type: COMPONENT_TYPE = Field(..., description="Type of component")
    order_ids: List[str]
    po_info: ActivePoUpdate


# class ActivePoInsert(BaseModel):
#     id: Optional[str] = Field(None, description="Unique ID of the purchase order")
#     po_number: Optional[str] = Field(None, description="Purchase order number")
#     company_address: Optional[str] = Field(None, description="Company address")
#     sold_to: str = Field(..., description="Sold to details")
#     ship_to: str = Field(..., description="Shipping address")
#     po_name: Optional[str] = Field(None, description="Purchase order name")
#     order_contact: str = Field(..., description="Order contact person")
#     date_required: Optional[date] = Field(None, description="Date required for the order")
#     order_contact_email: Optional[str] = Field(None, description="Email of the order contact")
#     delivery_contact_phone: Optional[str] = Field(None, description="Delivery contact phone number")
#     purchase_order: str = Field(..., description="Purchase order reference")
#     ordered_date: Optional[date] = Field(None, description="Datetime when the order was placed")
#     material: Optional[str] = Field(None, description="Material details")
#     quote: str = Field(..., description="Quote reference")
#     scheduled_ship_date: Optional[date] = Field(None, description="Scheduled shipping date")
#     customer: Optional[str] = Field(None, description="Customer name")
#     description: Optional[str] = Field(None, description="Order description")
#     po_acknowledgement: Optional[str] = Field(None, description="PO acknowledgment details")
#     ship_via: str = Field(..., description="Shipping method")
#     ship_instructions: Optional[str] = Field(None, description="Shipping instructions")
#     order_type: str = Field(..., description="Order type")
#     order_type_description: Optional[str] = Field(None, description="Order type description")
#     carrier: Optional[str] = Field(None, description="Carrier details")
#     service_center: Optional[str] = Field(None, description="Service center information")
#     transfer_point_ship_via: Optional[str] = Field(None, description="Transfer point shipping method")
#     transfer_point_carrier: Optional[str] = Field(None, description="Transfer point carrier")
#     bundling_code: Optional[str] = Field(None, description="Bundling code")
#     prepaid_collect_code_id: Optional[int] = Field(None, description="Prepaid collect code ID")
#     is_job_site: bool = Field(False, description="Indicates if it is a job site order")
#     ordered_item_quantity: Optional[int] = Field(None, description="Ordered item quantity")
#     final_price: Optional[float] = Field(None, description="Final price")



class ItemStatus(BaseModel):
    is_received: Optional[bool] = Field(None, description="Mark item as received")
    is_missing: Optional[bool] = Field(None, description="Mark item as missing")
    is_damaged: Optional[bool] = Field(None, description="Mark item as damaged")

class UpdatePOItemsStatusRequest(BaseModel):
    order_items: Dict[str, ItemStatus] = Field(..., description="Mapping of order item IDs to their status")
    

class RequestShipItems(BaseModel):
    shipping_status: ShippingStatus
    estimated_fulfillment_date: Optional[date] = Field(None, description="Estimated fulfillment date")
    items: List[str] = Field(..., description="Item IDs")

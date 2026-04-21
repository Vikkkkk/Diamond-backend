from typing import List
from utils.common import upload_path_to_s3, upload_to_s3, get_aws_full_path, delete_from_s3
from loguru import logger
from models.sections import Sections
# from schemas.project_schemas import Project
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import math
from utils.common import get_user_time
from schemas.shippimg_schema import GenerateLabelRequest
from models.ordered_items import OrderedItems
from models.active_po import ActivePo
import json
import os
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

load_dotenv()
    




async def generate_shipping_label_pdf(order_item_id, crate_no, bucket_name = None):
    """Generate a shipping label for a given order item and crate number.

    Args:
        order_item_id (str): The order item ID.
        crate_no (str): The crate number.
        bucket_name (Optional[str]): The S3 bucket name. Defaults to `BUCKET_NAME`.

    Returns:
        Optional[str]: The URL of the generated shipping label, or `None` if generation failed.
    """
    try:
        # # Generate a unique filename for the shipping label
        # shipping_label_path = f"shipping_labels/{order_item_id}_{crate_no}.pdf"
        # TODO: label generation process
        # Upload the generated shipping label to S3
        shipping_label_path = os.path.join(".", "uploads", "sample.pdf")
        upload_path = "shipping_labels"
        file_key = await upload_path_to_s3(shipping_label_path, upload_path, bucket_name)
        return file_key
    except Exception as error:
        print(f"Error generating shipping label: {error}")
        return None
    

async def generate_shipping_label(req_data: GenerateLabelRequest,db: Session):
    try:
        error_count = 0
        response = []
        for order_item_id, crate_no in req_data.data.items():
            if not crate_no:
                return JSONResponse(content={"message": f"Valid Create not found"}, status_code=400)
            order_item_id = str(order_item_id)
            order_item = db.query(OrderedItems).filter(OrderedItems.id == order_item_id).first()
            if not order_item:
                # return JSONResponse(content={"message": f"Order item '{order_item_id}' not found"}, status_code=400)
                response.append({"order_item_id": order_item_id, "crate_no": crate_no, "shipping_label_path": None, "message": f"Order item '{order_item_id}' not found"})
                error_count += 1
            else:
                desc =  f"opening_number: {order_item.opening_number}, door_type: {order_item.door_type}, hand: {order_item.hand}, door_mat: {order_item.door_mat}, frame_mat: {order_item.frame_mat}"
                if order_item.shipping_status.value in ["PENDING", "DONE"]:
                    # return JSONResponse(content={"message": f"Shipping label generation not allowed for '{desc}'"}, status_code=400)
                    response.append({"order_item_id": order_item_id, "crate_no": crate_no, "shipping_label_path": None, "message": f"Shipping label generation not allowed for '{desc}'"})
                    error_count += 1
                else:
                    if order_item.label_file_path is not None:
                        await delete_from_s3(order_item.label_file_path)
                    shipping_label_path = await generate_shipping_label_pdf(order_item_id, crate_no)
                    print("shipping_label_path", shipping_label_path)
                    order_item.label_content_type = "application/pdf"
                    order_item.label_file_name = os.path.split(shipping_label_path)[-1]
                    order_item.label_file_path = shipping_label_path
                    order_item.crate_number = crate_no
                    db.commit()
                    s3_full_path = get_aws_full_path(shipping_label_path)
                    response.append({"order_item_id": order_item_id, "crate_no": crate_no, "shipping_label_path": s3_full_path, "message": f"Shipping label generated successfully"})
        return JSONResponse(content={"message": "Shipping labels generated successfully", "data": response, "error_count": error_count}, status_code=200)
    except Exception as error:
        logger.exception("generate_shipping_label:: error - " + str(error))
        raise error
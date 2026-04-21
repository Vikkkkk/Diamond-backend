"""
This module is responsible for all brand related operations
"""
from loguru import logger
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.manufacturers import Manufacturers
from models.brands import Brands
from schemas.brand_schema import BrandRequest
from sqlalchemy.orm import Session



async def add_brand(brand_request: BrandRequest, db: Session):

    """**Summary:**
    This module is responsible for creating a hardware material for a project hardware group.

    **Args:**
    - `brand_request` (BrandRequest): Brand Request body.
    - `db` (Session): Dependency to get the database session.

    **Return:**
    - `id` (str): created project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        # Ensure that only set fields are considered
        brand_req_data = brand_request.model_dump(exclude_unset=True)
        
        print("brand_req_data::", brand_req_data)
        if "code" in brand_req_data:
            code = brand_req_data['code']
        elif "brandCode" in brand_req_data:
            code = brand_req_data["brandCode"]
        else:
            raise Exception("code not found in request data")
        if "manufacturerCode" in brand_req_data:
            manufacturerCode = brand_req_data['manufacturerCode']
            manufacture = await db.query(Manufacturers).filter(Manufacturers.code == brand_req_data['manufacturerCode']).first()
            if manufacture:
                brand_req_data["manufacturer_id"] = manufacture.id
            else:
                raise Exception("manufacturer not found")
        brand_id = None
        # Check if the manufacturer already exists
        brand = db.query(Brands).filter(Brands.code == code).first()
        if brand:
            brand_id = brand.id
            # Update existing brand
            for key, value in brand_req_data.items():
                setattr(brand, key, value)
            
        else:
            # Add new brand
            new_brand_data = Brands(**brand_req_data)
            db.add(new_brand_data)
            brand_id = new_brand_data.id
        db.commit()
        # Return success message and created brand ID
        return {"id": brand_id, "message": "brand added.", "status": "success"}
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error

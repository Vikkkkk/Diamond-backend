"""
This module contains all manufacturer related operations
"""
from models.manufacturers import Manufacturers
from loguru import logger
from sqlalchemy.orm import Session
from schemas.manufacture_schema import Manufacturer


async def addManufacture(request_data: Manufacturer, db: Session):
    """
    Add or update a manufacturer in the database.

    Args:
        request_data (dict): Data of the manufacturer to be added or updated.
        db: Database session object.

    Returns:
        bool: True if the operation is successful.

    Raises:
        Exception: If an unexpected error occurs during database operations.
    """
    try:
        request_data = request_data.model_dump(exclude_unset=True)
        if "code" in request_data:
            code = request_data['code']
        elif "manufacturerCode" in request_data:
            code = request_data["manufacturerCode"]
        else:
            raise Exception("code not found in request data")
        manu_id = None
        # Check if the manufacturer already exists
        manufacture = db.query(Manufacturers).filter(Manufacturers.code == code).first()
        if manufacture:
            manu_id = manufacture.id
            # Update existing manufacturer
            for key, value in request_data.items():
                setattr(manufacture, key, value)
            
        else:
            
            # Add new manufacturer
            material_data = Manufacturers(**request_data)
            db.add(material_data)
            manu_id = material_data.id
            
        db.commit()
        # Return success message and created manufacturer ID
        return {"id": manu_id, "message": "manufacturer added.", "status": "success"}
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        await db.rollback()
        raise error
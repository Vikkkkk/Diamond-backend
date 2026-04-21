from models.brands import Brands
from models.manufacturers import Manufacturers
from sqlalchemy.orm import joinedload


def get_catalog_details(db, catalog_name):
    """
    Retrieve catalog details based on whether the given catalog_name is a brand or manufacturer.
    """
    # Check if it belongs to a brand
    brand = db.query(Brands).filter(Brands.name == catalog_name).options(
        joinedload(Brands.manufacturer) 
    ).first()

    if brand:
        data = {
            "brand_id": brand.id,
            "brand_name": brand.name,
            "manufacturer_id": brand.manufacturer.id if brand.manufacturer else None,
            "manufacturer_name": brand.manufacturer.name if brand.manufacturer else None
        }

    # Check if it belongs to a manufacturer
    manufacturer = db.query(Manufacturers).filter(Manufacturers.name == catalog_name).first()
    if manufacturer:
        data = {
            "manufacturer_id": manufacturer.id,
            "manufacturer_name": manufacturer.name
        }
    return data


async def get_manufacturer_name(db, manufacturer_id):
    data = db.query(Manufacturers).get(manufacturer_id)
    return data.name if data else None


async def get_brand_name(db, brand_id):
    data = db.query(Brands).filter(Brands.id == brand_id).first()
    return data.name if data else None
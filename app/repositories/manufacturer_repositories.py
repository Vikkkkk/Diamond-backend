"""
This file contains all commonly used repositories.
"""
from loguru import logger
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_charges import ProjectTakeOffSheetCharges
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.raw_materials import RawMaterials
from sqlalchemy import or_, and_, update, func, text, case


def get_manufacture_by_id(db, id: str):
    return db.query(Manufacturers).filter(Manufacturers.id == id).first()
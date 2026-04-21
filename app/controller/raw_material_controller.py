"""
This file contains all the controller operations related to raw materials.
"""
from models.raw_materials import RawMaterials
from models.section_raw_materials import SectionRawMaterials
from models.project_raw_materials import ProjectRawMaterials
from repositories.common_repositories import get_raw_materialwise_total
from sqlalchemy.orm import Session
from models.sections import Sections
from fastapi.responses import JSONResponse


async def get_project_raw_materials(db: Session, project_id: str):
    """
        Asynchronously retrieves all raw materials for a given project from the database.
        Args:
            db: The database connection.
            project_id: The ID of the project.
        Returns:
            A dictionary containing the retrieved data and the status of the operation.
    """
    try:
        data = await get_raw_materialwise_total(db, project_id)
        return {"data": data, "status": "success"}
    except Exception as e:
        print(e)
        raise e


async def get_all_raw_materials(db: Session, section_id: str):
    """
        Retrieves all raw materials from the database based on the given material type("DOOR" | "FRAME")
        Parameters:
            db (Database): The database connection object.
            material_type (str): The type of material to filter the raw materials by ("DOOR" | "FRAME"). If None, all raw materials will be retrieved.
        Returns:
            dict: A dictionary containing the retrieved raw materials and the status of the operation.
                - data (list): A list of dictionaries representing the raw materials.
                - status (str): The status of the operation ("success" if successful, otherwise an error message).
        Raises:
            Exception: If an error occurs during the retrieval process.
    """
    # we need to "DOOR" to be converted to "Door" such that it can match the name in raw_materials table.
    try:
        query = (
            db.query(SectionRawMaterials)
            .filter(SectionRawMaterials.section_id == section_id)
            .join(RawMaterials, RawMaterials.id == SectionRawMaterials.raw_material_id)
            .order_by(RawMaterials.sort_order.asc())
            .all()
        )
        data = []
        for elm in query:
            temp_data = elm.raw_material.to_dict
            temp_data["section_id"] = section_id
            temp_data["is_door"] = True if "door" in elm.raw_material.name.lower() else False 
            temp_data["is_frame"] = True if "frame" in elm.raw_material.name.lower() else False 
            data.append(temp_data)
        return {"data": data, "status": "success"}
    except Exception as e:
        print(e)
        raise e
    


async def get_raw_materials(db: Session, keyword: str):
    """
        Retrieves all raw materials from the database based on the given keyword "door" | "frame"
        Parameters:
            db (Database): The database connection object.
            keyword (str): Material name keyword to filter the raw materials by ("door" | "frame").
        Returns:
            dict: A dictionary containing the retrieved raw materials and the status of the operation.
                - data (list): A list of dictionaries representing the raw materials.
                - status (str): The status of the operation ("success" if successful, otherwise an error message).
        Raises:
            Exception: If an error occurs during the retrieval process.
    """
    try:
        data = (
            db.query(RawMaterials)
            .filter(RawMaterials.name.ilike(f'%{keyword}%'))
            .order_by(RawMaterials.sort_order.asc())
            .all()
        )
        return {"data": data, "status": "success"}
    except Exception as e:
        print(e)
        raise e

async def get_all_project_raw_materials(db: Session, project_id: str):
    """
        Retrieves all raw materials from the database based on the given material type("DOOR" | "FRAME")
        Parameters:
            db (Database): The database connection object.
            material_type (str): The type of material to filter the raw materials by ("DOOR" | "FRAME"). If None, all raw materials will be retrieved.
        Returns:
            dict: A dictionary containing the retrieved raw materials and the status of the operation.
                - data (list): A list of dictionaries representing the raw materials.
                - status (str): The status of the operation ("success" if successful, otherwise an error message).
        Raises:
            Exception: If an error occurs during the retrieval process.
    """
    # we need to "DOOR" to be converted to "Door" such that it can match the name in raw_materials table.
    try:
        query = (
            db.query(ProjectRawMaterials)
            .filter(ProjectRawMaterials.project_id == project_id)
            .join(RawMaterials, RawMaterials.id == ProjectRawMaterials.raw_material_id)
            .order_by(RawMaterials.sort_order.asc())
            .all()
        )
        data = []
        for elm in query:
            temp_data = elm.to_dict
            temp_data["project_raw_material_id"] = temp_data["id"]
            temp_data["id"] = elm.raw_material.id
            temp_data["item_number"] = elm.raw_material.item_number
            temp_data["sort_order"] = elm.raw_material.sort_order
            temp_data["code"] = elm.raw_material.code
            temp_data["name"] = elm.raw_material.name
            temp_data["is_door"] = True if "door" in elm.raw_material.name.lower() else False 
            temp_data["is_frame"] = True if "frame" in elm.raw_material.name.lower() else False 
            data.append(temp_data)
        return {"data": data, "status": "success"}
    except Exception as e:
        print(e)
        raise e


async def get_raw_material_details(db: Session, keywords: str):
    # we need to "DOOR" to be converted to "Door" such that it can match the name in raw_materials table.
    try:
        if keywords is None:
            return JSONResponse(content={"message": f"Need to pass atleast one keyword."}, status_code=400)
        keywords = keywords.split(",")
        query = (
            db.query(RawMaterials)
            .filter(RawMaterials.code.in_(keywords), Sections.code != "MXD")
            .order_by(RawMaterials.sort_order.asc())
            .all()
        )
        data = []
        for elm in query:
            temp_data = elm.to_dict
            for section_data in elm.raw_material_sections:
                section_data = section_data.section
                if section_data.code != "MXD":
                    temp_data["section"] = section_data.to_dict
            data.append(temp_data)
        return {"data": data, "status": "success"}
    except Exception as e:
        print(e)
        raise e
    
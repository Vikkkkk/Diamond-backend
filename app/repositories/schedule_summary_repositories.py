from loguru import logger
import re
from sqlalchemy import func
from sqlalchemy import or_, and_, not_, text
from sqlalchemy.orm import Session
from repositories.schedule_repositories import update_schedule_stats
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.project_raw_material_manufacturer_quotes import ProjectRawMaterialManufacturerQuotes
from models.adon_opening_fields import AdonOpeningFields
from utils.common import delete_from_s3, get_exact_breakup_amount, get_user_time, upload_to_s3
from models.raw_materials import RawMaterials
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.schedules import Schedules
from models.task_activity import TaskActivity
from models.members import Members
from difflib import SequenceMatcher
from models.task_status import TaskStatus
from datetime import date, datetime, timedelta
from fastapi import UploadFile
from models.schedule_data import ScheduleData, COMPONENT_TYPE
from typing import List
from repositories.material_repositories import get_ctalog_details
import pandas as pd
from models.opening_change_stats import OpeningChangeStats
from fastapi.responses import JSONResponse
from repositories.catelog_repositories import get_catalog_details, get_brand_name, get_manufacturer_name
import os
from collections import defaultdict
import json



async def get_project_schedule_component_summary(db, project_id):
    try:
        query_text = """
            SELECT
                temp_table.schedule_id AS schedule_id,
                s.opening_number AS opening_number,
                s.desc AS description,
                temp_table.part_number AS part_number,
                temp_table.component AS component,
                ROUND(SUM(temp_table.quantity),3) AS quantity,
                ROUND(SUM(temp_table.total_amount),3) AS total_amount,
                ROUND(SUM(temp_table.total_base_amount),3) AS total_base_amount,
                ROUND(SUM(temp_table.total_sell_amount),3) AS total_sell_amount,
                ROUND(SUM(temp_table.total_extended_sell_amount),3) AS total_extended_sell_amount,
                ROUND(SUM(temp_table.final_amount),3) AS final_amount,
                ROUND(SUM(temp_table.final_base_amount),3) AS final_base_amount,
                ROUND(SUM(temp_table.final_sell_amount),3) AS final_sell_amount,
                ROUND(SUM(temp_table.final_extended_sell_amount),3) AS final_extended_sell_amount
            FROM
                (
                    (
                        SELECT 
                            schedule_id,
                            part_number,
                            component,
                            CASE 
                                WHEN is_adon_field = TRUE THEN 0
                                ELSE 1
                            END AS quantity,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_amount)
                                ELSE MAX(sd.total_amount)
                            END AS total_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_base_amount)
                                ELSE MAX(sd.total_base_amount)
                            END AS total_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_sell_amount)
                                ELSE MAX(sd.total_sell_amount)
                            END AS total_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_extended_sell_amount)
                                ELSE MAX(sd.total_extended_sell_amount)
                            END AS total_extended_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_amount)
                                ELSE MAX(sd.final_amount)
                            END AS final_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_base_amount)
                                ELSE MAX(sd.final_base_amount)
                            END AS final_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_sell_amount)
                                ELSE MAX(sd.final_sell_amount)
                            END AS final_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_extended_sell_amount)
                                ELSE MAX(sd.final_extended_sell_amount)
                            END AS final_extended_sell_amount
                        FROM
                            schedule_data AS sd
                        WHERE 
                            sd.has_price_dependancy = TRUE
                            AND 
                            sd.latest_data = TRUE
                            AND 
                            sd.component in ("DOOR", "FRAME")
                        GROUP BY 
                            schedule_id,
                            part_number,
                            component,
                            is_adon_field
						HAVING schedule_id in (
							SELECT 
								id
							FROM
								schedules
							WHERE
								schedules.project_id = :project_id
								AND
								schedules.is_active = TRUE
						)
                    ) 
                    UNION
                    (
                        SELECT
                            schedule_id,
                            NULL AS part_number,
                            "HARDWARE" AS component,
                            SUM(quantity) AS quantity,
                            SUM(total_amount) AS total_amount,
                            SUM(total_base_amount) AS total_base_amount,
                            SUM(total_sell_amount) AS total_sell_amount,
                            SUM(total_extended_sell_amount) AS total_extended_sell_amount,
                            SUM(final_amount) AS final_amount,
                            SUM(final_base_amount) AS final_base_amount,
                            SUM(final_sell_amount) AS final_sell_amount,
                            SUM(final_extended_sell_amount) AS final_extended_sell_amount
                        FROM
                            schedule_opening_hardware_materials AS sohm
                        GROUP BY 
                            schedule_id
						HAVING schedule_id in (
							SELECT 
								id
							FROM
								schedules
							WHERE
								schedules.project_id = :project_id
								AND
								schedules.is_active = TRUE
						)
                    )
                ) as temp_table
            JOIN schedules s ON s.id = temp_table.schedule_id
            GROUP BY
                temp_table.schedule_id, s.opening_number, s.desc, temp_table.component, temp_table.part_number;
        """
        result = db.execute(
            text(query_text), 
            {
                "project_id": project_id,
            }
        )
        rows = result.fetchall()
        columns = result.keys()

        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.exception(f"get_project_schedule_component_summary:: Error : {e}")
        return []
    

async def get_project_schedule_summary(db, project_id):
    try:
        query_text = """
            SELECT
                temp_table.schedule_id AS schedule_id,
                s.opening_number AS opening_number,
                s.desc AS description,
                ROUND(SUM(temp_table.quantity),3) AS quantity,
                ROUND(SUM(temp_table.total_amount),3) AS total_amount,
                ROUND(SUM(temp_table.total_base_amount),3) AS total_base_amount,
                ROUND(SUM(temp_table.total_sell_amount),3) AS total_sell_amount,
                ROUND(SUM(temp_table.total_extended_sell_amount),3) AS total_extended_sell_amount,
                ROUND(SUM(temp_table.final_amount),3) AS final_amount,
                ROUND(SUM(temp_table.final_base_amount),3) AS final_base_amount,
                ROUND(SUM(temp_table.final_sell_amount),3) AS final_sell_amount,
                ROUND(SUM(temp_table.final_extended_sell_amount),3) AS final_extended_sell_amount
            FROM
                (
                    (
                        SELECT 
                            schedule_id,
                            part_number,
                            component,
                            CASE 
                                WHEN is_adon_field = TRUE THEN 0
                                ELSE 1
                            END AS quantity,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_amount)
                                ELSE MAX(sd.total_amount)
                            END AS total_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_base_amount)
                                ELSE MAX(sd.total_base_amount)
                            END AS total_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_sell_amount)
                                ELSE MAX(sd.total_sell_amount)
                            END AS total_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_extended_sell_amount)
                                ELSE MAX(sd.total_extended_sell_amount)
                            END AS total_extended_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_amount)
                                ELSE MAX(sd.final_amount)
                            END AS final_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_base_amount)
                                ELSE MAX(sd.final_base_amount)
                            END AS final_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_sell_amount)
                                ELSE MAX(sd.final_sell_amount)
                            END AS final_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_extended_sell_amount)
                                ELSE MAX(sd.final_extended_sell_amount)
                            END AS final_extended_sell_amount
                        FROM
                            schedule_data AS sd
                        WHERE 
                            sd.has_price_dependancy = TRUE
                            AND 
                            sd.latest_data = TRUE
                            AND 
                            sd.component in ("DOOR", "FRAME")
                        GROUP BY 
                            schedule_id,
                            part_number,
                            component,
                            is_adon_field
						HAVING schedule_id in (
							SELECT 
								id
							FROM
								schedules
							WHERE
								schedules.project_id = :project_id
								AND
								schedules.is_active = TRUE
						)
                    ) 
                    UNION
                    (
                        SELECT
                            schedule_id,
                            NULL AS part_number,
                            "HARDWARE" AS component,
                            SUM(quantity) AS quantity,
                            SUM(total_amount) AS total_amount,
                            SUM(total_base_amount) AS total_base_amount,
                            SUM(total_sell_amount) AS total_sell_amount,
                            SUM(total_extended_sell_amount) AS total_extended_sell_amount,
                            SUM(final_amount) AS final_amount,
                            SUM(final_base_amount) AS final_base_amount,
                            SUM(final_sell_amount) AS final_sell_amount,
                            SUM(final_extended_sell_amount) AS final_extended_sell_amount
                        FROM
                            schedule_opening_hardware_materials AS sohm
                        GROUP BY 
                            schedule_id
						HAVING schedule_id in (
							SELECT 
								id
							FROM
								schedules
							WHERE
								schedules.project_id = :project_id
								AND
								schedules.is_active = TRUE
						)
                    )
                ) as temp_table
            JOIN schedules s ON s.id = temp_table.schedule_id
            GROUP BY
                temp_table.schedule_id, s.opening_number, s.desc;
        """
        result = db.execute(
            text(query_text), 
            {
                "project_id": project_id,
            }
        )
        rows = result.fetchall()
        columns = result.keys()

        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.exception(f"get_project_schedule_summary:: Error : {e}")
        return []
    

async def get_schedule_component_summary(db, schedule_id):
    try:
        query_text = """
            SELECT
                temp_table.schedule_id AS schedule_id,
                s.opening_number AS opening_number,
                s.desc AS description,
                temp_table.part_number AS part_number,
                temp_table.component AS component,
                ROUND(SUM(temp_table.quantity),3) AS quantity,
                ROUND(SUM(temp_table.total_amount),3) AS total_amount,
                ROUND(SUM(temp_table.total_base_amount),3) AS total_base_amount,
                ROUND(SUM(temp_table.total_sell_amount),3) AS total_sell_amount,
                ROUND(SUM(temp_table.total_extended_sell_amount),3) AS total_extended_sell_amount,
                ROUND(SUM(temp_table.final_amount),3) AS final_amount,
                ROUND(SUM(temp_table.final_base_amount),3) AS final_base_amount,
                ROUND(SUM(temp_table.final_sell_amount),3) AS final_sell_amount,
                ROUND(SUM(temp_table.final_extended_sell_amount),3) AS final_extended_sell_amount
            FROM
                (
                    (
                        SELECT 
                            schedule_id,
                            part_number,
                            component,
                            CASE 
                                WHEN is_adon_field = TRUE THEN 0
                                ELSE 1
                            END AS quantity,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_amount)
                                ELSE MAX(sd.total_amount)
                            END AS total_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_base_amount)
                                ELSE MAX(sd.total_base_amount)
                            END AS total_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_sell_amount)
                                ELSE MAX(sd.total_sell_amount)
                            END AS total_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.total_extended_sell_amount)
                                ELSE MAX(sd.total_extended_sell_amount)
                            END AS total_extended_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_amount)
                                ELSE MAX(sd.final_amount)
                            END AS final_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_base_amount)
                                ELSE MAX(sd.final_base_amount)
                            END AS final_base_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_sell_amount)
                                ELSE MAX(sd.final_sell_amount)
                            END AS final_sell_amount,
                            CASE 
                                WHEN is_adon_field = TRUE THEN SUM(sd.final_extended_sell_amount)
                                ELSE MAX(sd.final_extended_sell_amount)
                            END AS final_extended_sell_amount
                        FROM
                            schedule_data AS sd
                        WHERE 
                            sd.schedule_id = :schedule_id
                            AND
                            sd.has_price_dependancy = TRUE
                            AND 
                            sd.latest_data = TRUE
                            AND 
                            sd.component in ("DOOR", "FRAME")
                        GROUP BY 
                            schedule_id,
                            part_number,
                            component,
                            is_adon_field
                    ) 
                    UNION
                    (
                        SELECT
                            schedule_id,
                            NULL AS part_number,
                            "HARDWARE" AS component,
                            SUM(quantity) AS quantity,
                            SUM(total_amount) AS total_amount,
                            SUM(total_base_amount) AS total_base_amount,
                            SUM(total_sell_amount) AS total_sell_amount,
                            SUM(total_extended_sell_amount) AS total_extended_sell_amount,
                            SUM(final_amount) AS final_amount,
                            SUM(final_base_amount) AS final_base_amount,
                            SUM(final_sell_amount) AS final_sell_amount,
                            SUM(final_extended_sell_amount) AS final_extended_sell_amount
                        FROM
                            schedule_opening_hardware_materials AS sohm
                        WHERE 
                            sohm.schedule_id = :schedule_id
                    )
                ) AS temp_table
            JOIN schedules s ON s.id = temp_table.schedule_id
            GROUP BY
                temp_table.schedule_id, s.opening_number, s.desc, temp_table.component, temp_table.part_number;
        """
        result = db.execute(
            text(query_text), 
            {
                "schedule_id": schedule_id,
            }
        )
        rows = result.fetchall()
        columns = result.keys()

        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.exception(f"get_schedule_component_summary:: Error : {e}")
        return None
    


async def get_schedule_discount_data(db, project_id):
    try:
        query_text = """
            SELECT 
                * 
            FROM
            (
                (
                    SELECT
                        schedule_id,
                        sd.id AS ref_id,
                        NULL AS part_number,
                        NULL AS manufacturer_id,
                        NULL AS brand_id,
                        component,
                        name,
                        value,
                        is_basic_discount,
                        discount,
                        discount_type
                    FROM
                        schedule_data AS sd
                    WHERE 
                        schedule_id in (
                            SELECT 
                                id
                            FROM
                                schedules
                            WHERE
                                schedules.project_id = :project_id
                            AND
                                schedules.is_active = TRUE
                        )
                    AND
                    sd.latest_data = TRUE
                    AND
                    name like '%catalog%'
                )
                UNION
                (
                    SELECT
                        sohm.schedule_id AS schedule_id,
                        sohm.id AS ref_id,
                        NULL AS part_number,
                        ohm.manufacturer_id AS manufacturer_id,
                        ohm.brand_id AS brand_id,
                        "HARDWARE" AS component,
                        ohm.short_code AS name,
                        NULL AS value,
                        ohm.is_basic_discount,
                        ohm.discount,
                        ohm.discount_type
                    FROM
                        schedule_opening_hardware_materials AS sohm 
                    JOIN
                        opening_hardware_materials AS ohm on sohm.opening_hardware_material_id = ohm.id
                    WHERE 
                        ohm.project_id = :project_id
                )
            ) temp_table
        """
        result = db.execute(
            text(query_text), 
            {
                "project_id": project_id,
            }
        ).fetchall()
        schedule_data = {}
        discount_data = []
        for res in result:
            obj = {
                "schedule_id": res.schedule_id,
                "ref_id": res.ref_id,
                "manufacturer_id": res.manufacturer_id,
                "manufacturer_name": None,
                "brand_id": res.brand_id,
                "brand_name": None,
                "component": res.component,
                "name": res.name,
                "value": res.value,
                "is_basic_discount": res.is_basic_discount,
                "discount": res.discount,
                "discount_type": res.discount_type
            }
            component = res.component
            if component != "HARDWARE":
                catalog = res.value
                catelog_data = get_catalog_details(db, catalog)
                if "brand_id" in catelog_data:
                    obj["brand_id"] = catelog_data["brand_id"]
                    obj["brand_name"] = catelog_data["brand_name"]
                obj["manufacturer_id"] = catelog_data["manufacturer_id"]
                obj["manufacturer_name"] = catelog_data["manufacturer_name"]
            else:
                if res.brand_id:
                   obj["brand_name"] = await get_brand_name(db, res.brand_id) 
                obj["manufacturer_name"] = await get_manufacturer_name(db, res.manufacturer_id) 
                raw_mat_data = db.query(RawMaterials).filter(RawMaterials.code == "HWD").first()
                obj["raw_material_code"] = raw_mat_data.code
                obj["raw_material_id"] = raw_mat_data.id
            if res.schedule_id not in schedule_data:
                data = db.query(Schedules).get(res.schedule_id)
                temp_data = {
                    "door_material_code": data.door_material_code,
                    "door_material_id": data.door_material_id,
                    "frame_material_code": data.frame_material_code,
                    "frame_material_id": data.frame_material_id
                }
                if component == "DOOR":
                    obj["raw_material_code"] = data.door_material_code
                    obj["raw_material_id"] = data.door_material_id
                elif component == "FRAME":
                    obj["raw_material_code"] = data.frame_material_code
                    obj["raw_material_id"] = data.frame_material_id
                schedule_data[res.schedule_id] = temp_data
            else:
                temp_data = schedule_data[res.schedule_id]
                if component == "DOOR":
                    obj["raw_material_code"] = temp_data["door_material_code"]
                    obj["raw_material_id"] = temp_data["door_material_id"]
                elif component == "FRAME":
                    obj["raw_material_code"] = temp_data["frame_material_code"]
                    obj["raw_material_id"] = temp_data["frame_material_id"]

            
            discount_data.append(obj)
        
        
        # Convert to DataFrame
        df = pd.DataFrame(discount_data)
        df = df.fillna("")
        # Group by the three keys
        grouped_df = (
            df.groupby(["raw_material_id", "manufacturer_id", "brand_id"], dropna=False)
            .agg({
                "schedule_id": "first",
                "ref_id": "first",
                "component": "first",
                "name": "first",
                "value": "first",
                "raw_material_code": "first",
                "manufacturer_name": "first",
                "brand_name": "first",
                "discount": "mean",
                "discount_type": "first",
                "is_basic_discount": "mean"
            })
            .reset_index()
        )

        # Convert back to list of dicts if needed
        result = grouped_df.to_dict(orient="records")
        for elm in result:
            if len(elm["brand_id"]) == 0:
                elm["brand_id"] = None
            if len(elm["brand_name"]) == 0:
                elm["brand_name"] = None
            if not elm["is_basic_discount"]:
                catalog_mapping = (
                    db.query(RawMaterialCatalogMapping)
                    .filter(
                        RawMaterialCatalogMapping.manufacturer_id==elm["manufacturer_id"],
                        RawMaterialCatalogMapping.brand_id==elm["brand_id"],
                        RawMaterialCatalogMapping.raw_material_id==elm["raw_material_id"]
                    )
                    .first()
                )
                quote_data = (
                    db.query(ProjectRawMaterialManufacturerQuotes)
                    .filter(
                        ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id == catalog_mapping.id,
                        ProjectRawMaterialManufacturerQuotes.project_id == project_id,
                    )
                    .first()
                )
                elm["quote_data"] = quote_data.to_dict
            else:
                elm["quote_data"] = {}
        return result, discount_data
    except Exception as e:
        logger.exception(f"get_schedule_discount_data:: Error : {e}")
        return []
    


async def update_schedule_charges(db, schedule_id):
    """
    A function to update the material's `total_base_amount`, `total_sell_amount` based on different discount types.
    
    Parameters:
    - db: the database connection object
    - project_material_id: the unique identifier of the project material
    
    Returns:
    No explicit return value, but updates the material charges in the database.
    """
    try:
        
        query_text = f"""
            SELECT 
                id,
                quantity,
                total_amount,
                discount,
                discount_type,
                markup,
                surcharge,
                surcharge_type,

                -- Calculated discount amount
                ROUND(CASE 
                    WHEN discount_type = 'PERCENTAGE' THEN COALESCE(total_amount * discount, 0)
                    WHEN discount_type = 'MULTIPLIER' THEN COALESCE(total_amount * (1 - discount), 0)
                    ELSE 0
                END, 2) AS discount_amount,

                -- Calculated total_base_amount
                CASE 
                    WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                    WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                    ELSE total_amount
                END AS total_base_amount,

                -- total_sell_amount = total_base_amount * (1 + markup)
                ROUND(
                    (
                    CASE 
                        WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                        WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                        ELSE total_amount
                    END
                    ) * (1 + COALESCE(markup, 0)),
                2) AS total_sell_amount,

                -- total_extended_sell_amount = total_sell_amount + surcharge_amount
                ROUND(
                    (
                    (
                        CASE 
                        WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                        WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                        ELSE total_amount
                        END
                    ) * (1 + COALESCE(markup, 0))
                    ) + CASE 
                        WHEN surcharge_type = 'PERCENTAGE' THEN ROUND(COALESCE(
                            (
                            (
                                CASE 
                                WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                                WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                                ELSE total_amount
                                END
                            ) * (1 + COALESCE(markup, 0))
                            ) * surcharge, 0), 2)
                        WHEN surcharge_type = 'MULTIPLIER' THEN ROUND(COALESCE(
                            (
                            (
                                CASE 
                                WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                                WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                                ELSE total_amount
                                END
                            ) * (1 + COALESCE(markup, 0))
                            ) * surcharge, 0), 2)
                        ELSE 0
                        END,
                2) AS total_extended_sell_amount
            FROM 
                schedule_data
            WHERE 
                schedule_id = '{schedule_id}'
                AND latest_data = TRUE;
        """
        # print("project_material_id:: ",project_material_id)
        rows = db.execute(text(query_text))
        material_data = rows.mappings().first()
        result = db.execute(
            text(query_text)
        )
        rows = result.fetchall()
        columns = result.keys()
        results = [dict(zip(columns, row)) for row in rows]
        for material_data in results:
            update_query = f"""
                UPDATE schedule_data
                SET 
                    total_amount = {material_data['total_amount']},
                    total_base_amount = {material_data['total_base_amount']},
                    total_sell_amount = {material_data['total_sell_amount']},
                    total_extended_sell_amount = {material_data['total_extended_sell_amount']},
                    final_amount = {material_data['quantity'] * material_data['total_amount']},
                    final_base_amount = {material_data['quantity'] * material_data['total_base_amount']},
                    final_sell_amount = {material_data['quantity'] * material_data['total_sell_amount']},
                    final_extended_sell_amount = {material_data['quantity'] * material_data['total_extended_sell_amount']}
                WHERE id = '{material_data["id"]}';
            """
            rows = db.execute(text(update_query))
            db.flush()
    except Exception as error:
        # Handle the error appropriately
        print("update_schedule_charges:: An error occurred:", error)
        raise error
    


async def add_schedule_discount_project_quote(
    db: Session, 
    discount_project_quote: dict, 
    files: List[UploadFile], 
    project_id: str,  
    current_member: Members
):
    """
    Adds a discount to a project quote.
 
    Args:
        db: Database session object.
        discount_project_quote (dict): Discount project quote data.
        files: List of uploaded files.
        project_id (str): Identifier of the project.
        current_member: Current member performing the operation.
    """
    try:
        manufacturer_id = str(discount_project_quote["manufacturer_id"]) if discount_project_quote["manufacturer_id"] is not None else None
        brand_id = str(discount_project_quote["brand_id"]) if discount_project_quote["brand_id"] is not None else None
        raw_material_id = str(discount_project_quote["raw_material_id"]) if discount_project_quote["raw_material_id"] is not None else None
        catalog_mapping = (
            db.query(RawMaterialCatalogMapping)
            .filter(
                RawMaterialCatalogMapping.manufacturer_id==manufacturer_id,
                RawMaterialCatalogMapping.brand_id==brand_id,
                RawMaterialCatalogMapping.raw_material_id==raw_material_id
            )
            .first()
        )
        if not catalog_mapping:
            return JSONResponse(content={"message": "wrong catalog selection"}, status_code=400)

        catalog_discount_quote = (
            db.query(ProjectRawMaterialManufacturerQuotes)
            .filter(
                ProjectRawMaterialManufacturerQuotes.project_id==project_id,
                ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id==catalog_mapping.id,
                ProjectRawMaterialManufacturerQuotes.expiry_date <= date.today() - timedelta(days=7)
            ).first()
        )
        if catalog_discount_quote:
            return JSONResponse(content={"message": "Valid discount already exists"}, status_code=400)
        catalog_raw_material_code = catalog_mapping.catalog_raw_material.code
        catalog_raw_material_name = catalog_mapping.catalog_raw_material.name
        insert_arr = {}
        is_file = False
        if 'discount_quote_number' in discount_project_quote:
            discount_quote_number = discount_project_quote['discount_quote_number']
            insert_arr['quote_text'] = discount_quote_number
        else:
            is_file = True
        if "expiry_date" in discount_project_quote:
            insert_arr['expiry_date'] = discount_project_quote["expiry_date"]

        discount = discount_project_quote['discount']
        discount_type = discount_project_quote['discount_type']

        insert_arr['project_id'] = project_id
        insert_arr['discount'] = discount
        insert_arr['raw_materials_catalog_mapping_id'] = catalog_mapping.id
        insert_arr['discount_type'] = discount_type
        insert_arr['created_by'] = current_member.id

        catalog_discount_quote = (
            db.query(ProjectRawMaterialManufacturerQuotes)
            .filter(
                ProjectRawMaterialManufacturerQuotes.project_id==project_id,
                ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id==catalog_mapping.id
            ).first()
        )
        if catalog_discount_quote:
            for key, value in insert_arr.items():
                if hasattr(catalog_discount_quote, key):
                    setattr(catalog_discount_quote, key, value)
            db.flush()
            discount_manufacturer_quote = catalog_discount_quote
        else:
            discount_manufacturer_quote = ProjectRawMaterialManufacturerQuotes(**insert_arr)
            db.add(discount_manufacturer_quote)
            db.flush()
        
        if is_file and files is not None:
            # Claaing function "upload_to_s3" to upload the attachment to S3
            for file in files:
                upload_path = f"discount_project_quote_documents/{discount_manufacturer_quote.id}"
                file_path = await upload_to_s3(file, upload_path)
                discount_manufacturer_quote.file_path = file_path

        update_arr = {
            "discount_type": discount_type,
            "is_basic_discount": False,
            # "updated_by": current_member.id,
            "updated_at": datetime.now(),
            "discount": discount
        }
        _, schedule_discount_data = await get_schedule_discount_data(db, project_id)
        if catalog_raw_material_code != "HWD":
            # In case the request for adding discount is for hardware materials
            for elm in schedule_discount_data:
                # chnage the discount type and discount amount in scehdule data so that we can recalculate the discounted price.
                if elm["component"] != "HARDWARE" and elm["component"].lower() in catalog_raw_material_name.lower():  
                    if (elm["manufacturer_id"] == manufacturer_id) and (elm["brand_id"] == brand_id):
                        (
                            db.query(ScheduleData)
                            .filter(
                                ScheduleData.schedule_id == elm["schedule_id"],
                                ScheduleData.component == elm["component"],
                                ScheduleData.latest_data == True
                            )
                            .update(update_arr)
                        )
                        db.flush()
        else:
            # In case the request for adding discount is for non-hardware materials like any door or frame
            for elm in schedule_discount_data:
                # chnage the discount type and discount amount in scehdule data so that we can recalculate the discounted price.
                if elm["component"] == "HARDWARE":  
                    if (elm["manufacturer_id"] == manufacturer_id) and (elm["brand_id"] == brand_id):
                        (
                            db.query(OpeningHardwareMaterials)
                            .filter(
                                OpeningHardwareMaterials.short_code == elm["name"],
                                OpeningHardwareMaterials.manufacturer_id == elm["manufacturer_id"],
                                OpeningHardwareMaterials.brand_id == elm["brand_id"],
                                OpeningHardwareMaterials.project_id == project_id,
                                OpeningHardwareMaterials.is_deleted == False
                            )
                            .update(update_arr)
                        )
                        db.flush()
        # Update the stats in all table using update stats
        for elm in schedule_discount_data:
            if elm["component"] == "HARDWARE" or elm["component"].lower() in catalog_raw_material_name.lower():  
                await update_schedule_charges(db, elm["schedule_id"])
                db.flush()
                await update_schedule_stats(db, elm["schedule_id"])
                db.flush()
        return discount_manufacturer_quote.id
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def delete_schedule_discount_project_quote(
    db: Session, 
    request_data: dict, 
    current_member: Members
):
    """
    Adds a discount to a project quote.
 
    Args:
        db: Database session object.
        discount_project_quote (dict): Discount project quote data.
        files: List of uploaded files.
        project_id (str): Identifier of the project.
        current_member: Current member performing the operation.
    """
    try:
        raw_material_id = str(request_data["raw_material_id"]) if request_data["raw_material_id"] is not None else None
        manufacturer_id = str(request_data["manufacturer_id"]) if request_data["manufacturer_id"] is not None else None
        brand_id = str(request_data["brand_id"]) if request_data["brand_id"] is not None else None
        project_id = str(request_data["project_id"])
        catalog_mapping = (
            db.query(RawMaterialCatalogMapping)
            .filter(
                RawMaterialCatalogMapping.manufacturer_id==manufacturer_id,
                RawMaterialCatalogMapping.brand_id==brand_id,
                RawMaterialCatalogMapping.raw_material_id==raw_material_id
            )
            .first()
        )
        if not catalog_mapping:
            return JSONResponse(content={"message": "wrong catalog selection"}, status_code=400)

        update_arr = {
            "discount_type": "PERCENTAGE",
            "is_basic_discount": True,
            # "updated_by": current_member.id,
            "updated_at": datetime.now(),
            "discount": catalog_mapping.discount_percentage if catalog_mapping.discount_percentage is not None else 0
        }
        _, schedule_discount_data = await get_schedule_discount_data(db, project_id)
        catalog_raw_material_code = catalog_mapping.catalog_raw_material.code
        catalog_raw_material_name = catalog_mapping.catalog_raw_material.name
        if catalog_raw_material_code != "HWD":
            # In case the request for adding discount is for hardware materials
            for elm in schedule_discount_data:
                # chnage the discount type and discount amount in scehdule data so that we can recalculate the discounted price.
                if elm["component"] != "HARDWARE" and elm["component"].lower() in catalog_raw_material_name.lower():  
                    if (elm["manufacturer_id"] == manufacturer_id) and (elm["brand_id"] == brand_id):
                        (
                            db.query(ScheduleData)
                            .filter(
                                ScheduleData.schedule_id == elm["schedule_id"],
                                ScheduleData.component == elm["component"],
                                ScheduleData.latest_data == True
                            )
                            .update(update_arr)
                        )
                        db.flush()
        else:
            # In case the request for adding discount is for non-hardware materials like any door or frame
            for elm in schedule_discount_data:
                # chnage the discount type and discount amount in scehdule data so that we can recalculate the discounted price.
                if elm["component"] == "HARDWARE":  
                    if (elm["manufacturer_id"] == manufacturer_id) and (elm["brand_id"] == brand_id):
                        (
                            db.query(OpeningHardwareMaterials)
                            .filter(
                                OpeningHardwareMaterials.short_code == elm["name"],
                                OpeningHardwareMaterials.manufacturer_id == elm["manufacturer_id"],
                                OpeningHardwareMaterials.brand_id == elm["brand_id"],
                                OpeningHardwareMaterials.project_id == project_id,
                                OpeningHardwareMaterials.is_deleted == False
                            )
                            .update(update_arr)
                        )
                        db.flush()


        # delete the quote info
        project_raw_material_quote_data = (
            db.query(ProjectRawMaterialManufacturerQuotes)
            .filter(
                ProjectRawMaterialManufacturerQuotes.project_id==project_id,
                ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id==catalog_mapping.id,
            )
        )

        project_raw_material_quote_data_first = project_raw_material_quote_data.first()

        if project_raw_material_quote_data_first.file_path is not None:
            # delete file
            await delete_from_s3(project_raw_material_quote_data_first.file_path)

        project_raw_material_quote_data.delete()

        # Update the stats in all table using update stats
        for elm in schedule_discount_data:
            if elm["component"] == "HARDWARE" or elm["component"].lower() in catalog_raw_material_name.lower():  
                await update_schedule_charges(db, elm["schedule_id"])
                db.flush()
                await update_schedule_stats(db, elm["schedule_id"])
                db.flush()
        return True
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        raise error



async def get_project_comparison_data(db, project_id):
    try:
        query_text = """
            SELECT 
                schedule_id,
                opening_number,
                CASE 
                    WHEN component = 'DOOR' THEN CONCAT(component, '-', part_number)
                    ELSE component
                END AS comp_part_key,
                ROUND(SUM(schedule_final_amount - take_off_final_amount), 3) AS final_amount,
                ROUND(SUM(schedule_final_base_amount - take_off_final_base_amount), 3) AS final_base_amount,
                ROUND(SUM(schedule_final_sell_amount - take_off_final_sell_amount), 3) AS final_sell_amount,
                ROUND(SUM(schedule_final_extended_sell_amount - take_off_final_extended_sell_amount), 3) AS final_extended_sell_amount
            FROM 
                opening_change_stats
            WHERE 
                project_id = :project_id
            GROUP BY
                schedule_id, opening_number, comp_part_key;
        """
        result = db.execute(text(query_text), {"project_id": project_id})

        results = result.fetchall()
        # Initialize an empty dictionary to store the final nested JSON
        nested_json = {}
        # Process the results into a nested JSON
        for row in results:
            schedule_id = row.schedule_id
            comp_part_key = row.comp_part_key
            
            # If schedule_id doesn't exist in the nested_json, create an empty dictionary for it
            if schedule_id not in nested_json:
                nested_json[schedule_id] = {}
            # Add the component and part number info under the respective schedule_id
            nested_json[schedule_id][comp_part_key] = {
                'final_amount': row.final_amount,
                'final_base_amount': row.final_base_amount,
                'final_sell_amount': row.final_sell_amount,
                'final_extended_sell_amount': row.final_extended_sell_amount
            }
        # print("nested_json: ", nested_json)
        return nested_json

    except Exception as e:
        logger.exception(f"comparison_opening_data:: Error : {e}")
        raise e



async def get_schedule_comparison_data(db, schedule_id):
    try:
        query_text = """
            SELECT 
                CASE 
                    WHEN component = 'DOOR' THEN CONCAT(component, '-', part_number)
                    ELSE component
                END AS comp_part_key,
                ROUND(SUM(schedule_final_amount - take_off_final_amount), 3) AS final_amount,
                ROUND(SUM(schedule_final_base_amount - take_off_final_base_amount), 3) AS final_base_amount,
                ROUND(SUM(schedule_final_sell_amount - take_off_final_sell_amount), 3) AS final_sell_amount,
                ROUND(SUM(schedule_final_extended_sell_amount - take_off_final_extended_sell_amount), 3) AS final_extended_sell_amount
            FROM 
                opening_change_stats
            WHERE 
                schedule_id = :schedule_id
            GROUP BY
                comp_part_key;
        """
        result = db.execute(text(query_text), {"schedule_id": schedule_id})

        results = result.fetchall()
        # Initialize an empty dictionary to store the final nested JSON
        nested_json = {}
        # Process the results into a nested JSON
        for row in results:
            comp_part_key = row.comp_part_key
            nested_json[comp_part_key] = {
                'final_amount': row.final_amount,
                'final_base_amount': row.final_base_amount,
                'final_sell_amount': row.final_sell_amount,
                'final_extended_sell_amount': row.final_extended_sell_amount
            }
        return nested_json
    except Exception as e:
        logger.exception(f"comparison_opening_data:: Error : {e}")
        raise e



async def get_schedule_fetaure_data_summary(db, schedule_id):
    try:
        query_text = """
            SELECT
                TRIM(CONCAT(component, ' ', IFNULL(part_number, ''))) AS info,
                -- base features
                (
                    SELECT JSON_OBJECTAGG(name, value)
                    FROM schedule_data b
                    WHERE b.schedule_id = a.schedule_id
                    AND b.component = a.component
                    AND b.latest_data = TRUE
                    AND IFNULL(b.part_number, '') = IFNULL(a.part_number, '')
                    AND b.is_adon_field = FALSE
                ) AS base_features,
                -- adon features
                (
                    SELECT JSON_OBJECTAGG(name, JSON_ARRAY(value))
                    FROM schedule_data c
                    WHERE c.schedule_id = a.schedule_id
                    AND c.component = a.component
                    AND c.latest_data = TRUE
                    AND IFNULL(c.part_number, '') = IFNULL(a.part_number, '')
                    AND c.is_adon_field = TRUE
                ) AS adon_features
            FROM
                schedule_data a
            WHERE
                a.schedule_id = :schedule_id
                AND
                a.latest_data = TRUE
            GROUP BY
                a.component, a.part_number;
        """
        result = db.execute(text(query_text), {"schedule_id": schedule_id})

        results = result.fetchall()
        # Initialize an empty dictionary to store the final nested JSON
        nested_json = {}
        # Process the results into a nested JSON
        for row in results:
            info = row.info
            if info not in ["HARDWARE"]:
                nested_json[info] = {
                    'base_features': row.base_features,
                    'adon_features': row.adon_features
                }
        return nested_json
    except Exception as e:
        logger.exception(f"get_schedule_fetaure_data_summary:: Error : {e}")
        raise e



async def get_schedule_hardware_fetaure_data_summary(db, schedule_id):
    try:
        query_text = """
            SELECT 
                schedule_opening_hardware_materials.id AS schedule_opening_hardware_material_id,
                short_code,
                opening_hardware_materials.desc,
                base_feature,
                adon_feature
            FROM
                opening_hardware_materials
            JOIN
                schedule_opening_hardware_materials
            ON
                schedule_opening_hardware_materials.opening_hardware_material_id = opening_hardware_materials.id
            WHERE
                schedule_opening_hardware_materials.schedule_id = :schedule_id;
        """
        result = db.execute(text(query_text), {"schedule_id": schedule_id})

        results = result.fetchall()
        # Initialize an empty dictionary to store the final nested JSON
        data = []
        # Process the results into a nested JSON
        for row in results:

            base_feature = json.loads(row.base_feature) if row.base_feature is not None else {}
            adon_feature = json.loads(row.adon_feature) if row.adon_feature is not None else {}
            obj = {
                "schedule_opening_hardware_material_id": row.schedule_opening_hardware_material_id,
                "name": row.short_code,
                "desc": row.desc,
                "base_feature": {
                    k: v["optionCode"]
                    for k, v in base_feature.items()
                    if isinstance(v, dict) and "optionCode" in v and v["optionCode"] is not None
                },
                "adon_feature": {
                    k: v["optionCode"]
                    for k, v in adon_feature.items()
                    if isinstance(v, dict) and "optionCode" in v and v["optionCode"] is not None
                },
            }
            data.append(obj)
        return data
    except Exception as e:
        logger.exception(f"get_schedule_hardware_fetaure_data_summary:: Error : {e}")
        raise e

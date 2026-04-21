from loguru import logger
import re
from sqlalchemy import func
from sqlalchemy import or_, and_, not_, text
from sqlalchemy.orm import Session
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.project_raw_material_manufacturer_quotes import ProjectRawMaterialManufacturerQuotes
from models.adon_opening_fields import AdonOpeningFields
from utils.common import delete_from_s3, get_exact_breakup_amount, get_user_time, upload_to_s3
from models.raw_materials import RawMaterials
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.schedules import Schedules
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from models.task_activity import TaskActivity
from models.members import Members
from difflib import SequenceMatcher
from models.task_status import TaskStatus
from datetime import date
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
from schemas.schedule_schemas import AdonOpeningFieldCreateSchema
import json

async def get_hing_locations(db: Session, schedule_id: str, component: str = "FRAME"):
    try:
        quantity = None
        height = None
        hing_location = None
        hing_keyword = "hing"
        height_keyword = "height"
        quantity_query_text = f"""
            SELECT 
                quantity
            FROM 
                schedule_opening_hardware_materials
            WHERE 
                schedule_id = :schedule_id
            AND (
                opening_hardware_material_id IN (
                    SELECT id AS hardware_material_id
                    FROM opening_hardware_materials
                    WHERE hardware_product_category_id IN (
                        SELECT id AS catgory_id
                        FROM hardware_product_category
                        WHERE search_keywords like '%{hing_keyword}%'
                    )
                    OR name  like '%{hing_keyword}%'
                    OR short_code  like '%{hing_keyword}%'
                )
            );
        """
        frame_height_query_text = f"""
        SELECT 
            name,
            value
        FROM 
            schedule_data
        WHERE 
            name like '%{height_keyword}%'
            AND component = "{component}"
            AND is_adon_field = false
            AND has_price_dependancy = true
            AND latest_data = true
            AND schedule_id = :schedule_id;
        """
        rows = db.execute(text(quantity_query_text), {"schedule_id": schedule_id})
        quantity_data = rows.mappings().first()
        if quantity_data:
            quantity = quantity_data["quantity"]
        rows = db.execute(text(frame_height_query_text), {"schedule_id": schedule_id})
        height_data = rows.mappings().first()
        if height_data:
            height = re.findall(r'\d+\.\d+|\d+', str(height_data["value"]))[0]
        if quantity is not None and height is not None:
            hing_location = (float(height) - 20.125) / (float(max(quantity, 2)) - 1)
        return hing_location
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"get_hing_locations:: Error : {e}")
        raise e

async def set_location_data(db: Session, schedule_id: str):
    try:
        query_text = """
        SELECT 
            id AS adon_filed_id,
            name,
            search_keywords
        FROM 
            adon_opening_fields
        WHERE 
            field_category like '%OPENING_SCHEDULE%'
            AND name like '%location%'
            AND name not like '%hing%'
            AND is_hw_data = true;
        """
        rows = db.execute(text(query_text))
        records = rows.mappings().all()
        data = []
        if len(records) > 0:
            for elm in records:
                curr_data = dict(elm)
                print("curr_data:: ",curr_data)
                for item in curr_data["search_keywords"].split(","):
                    hwd_data = await get_associated_hardware(db, item, schedule_id)
                    print("hwd_data:: ",hwd_data)
                    if hwd_data is not None and len(hwd_data) > 0:
                        data.append((curr_data, item, hwd_data[0]["name"] + "-" + hwd_data[0]["desc"] ))
        for elm in data:
            print(elm)
            resp_data = await get_values(elm[1],elm[2])
            # print("resp_data:: ",resp_data)
            if resp_data:
                existing_data = (
                    db.query(ScheduleData)
                    .filter(
                        ScheduleData.schedule_id == schedule_id, 
                        ScheduleData.name == elm[0]["name"], 
                        ScheduleData.component == "HARDWARE",
                        ScheduleData.part_number == None,
                        ScheduleData.latest_data == True
                    )
                    .first()
                )
                                    
                if existing_data:
                    existing_data.value = resp_data[0]["value"]
                    db.flush()
                else:
                    data = {
                        "schedule_id": schedule_id,
                        "name": elm[0]["name"], 
                        "desc": elm[2], 
                        "component": "HARDWARE",
                        "part_number": None,
                        "value": resp_data[0]["value"],
                        "adon_field_id": elm[0]["adon_filed_id"],
                        "is_adon_field": True,
                        "has_price_dependancy": False
                    }
                    new_data = ScheduleData(**data)
                    db.add(new_data)
                    db.flush()
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"set_location_data:: Error : {e}")
        raise e

async def set_hardware_prep_data(db: Session, schedule_id: str, component: str):
    try:
        if component == "FRAME":
            await set_location_data(db, schedule_id)
            location_data = await get_hing_locations(db, schedule_id, component)
            if location_data is not None:
                hing_loc_data = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == "hinge_location_on_frame").first()
                existing_data = (
                    db.query(ScheduleData)
                    .filter(
                        ScheduleData.schedule_id == schedule_id, 
                        ScheduleData.name == hing_loc_data.name, 
                        ScheduleData.component == COMPONENT_TYPE.HARDWARE,
                        ScheduleData.part_number == None,
                        ScheduleData.latest_data == True
                        )
                        .first()
                    )
                
                if existing_data:
                    existing_data.value = location_data
                    db.flush()
                else:
                    data = {
                        "schedule_id": schedule_id,
                        "name": hing_loc_data.name, 
                        "desc": hing_loc_data.desc, 
                        "component": COMPONENT_TYPE.HARDWARE,
                        "part_number": None,
                        "value": location_data,
                        "adon_field_id": hing_loc_data.id,
                        "is_adon_field": True,
                        "has_price_dependancy": False
                    }
                    new_data = ScheduleData(**data)
                    db.add(new_data)
                    db.flush()
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"set_hardware_prep_data:: Error : {e}")
        raise e



async def get_associated_hardware(db: Session, keyword: str, schedule_id: str):
    try:
        query_text = f"""
            SELECT 
                opening_hardware_materials.id,
                ifnull(name, " ") name,
                short_code,
                opening_hardware_materials.desc,
                series,
                schedule_opening_hardware_materials.quantity 
            FROM 
                schedule_opening_hardware_materials
            JOIN 
                opening_hardware_materials
            ON 
                opening_hardware_materials.id = schedule_opening_hardware_materials.opening_hardware_material_id
            WHERE 
                schedule_id = :schedule_id
            AND (
                opening_hardware_material_id IN (
                    SELECT id AS hardware_material_id
                    FROM opening_hardware_materials
                    WHERE hardware_product_category_id IN (
                        SELECT id AS catgory_id
                        FROM hardware_product_category
                        WHERE search_keywords like '%{keyword}%'
                    )
                    OR name  like '%{keyword}%'
                    OR short_code  like '%{keyword}%'
                )
            );
        """
        rows = db.execute(text(query_text), {"schedule_id": schedule_id})
        records = rows.mappings().all()
        data = []
        if len(records) > 0:
            for elm in records:
                data.append(dict(elm))
        return data
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"get_associated_hardware:: Error : {e}")
        raise e

async def get_values(name, value):
    try:
        location_data = await load_location_data()
        matched_category = await find_best_match_dict_mod([name], location_data, "category")
        if matched_category:
            matched_value = await find_best_match_dict_mod([value], matched_category, "category", 0.8)
            # print("matched_category:: ",matched_category)
            # print("matched_value:: ",matched_value)
            if matched_value is not None:
                return matched_value
            else:
                return matched_category
        else:
            return None
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"get_values:: Error : {e}")
        raise e


async def find_best_match_dict_mod(target_strings, dict_list, key, threshold=0.3):
    try:
        # Calculate cumulative similarity scores for each dictionary
        similarity_scores = []
        for d in dict_list:
            if key in d:
                # Calculate a cumulative score based on substring matches
                total_score = sum(
                    1.0 if target.lower() in d[key].lower() else 0.5 * SequenceMatcher(None, target.lower(), d[key].lower()).ratio()
                    for target in target_strings
                )
                if total_score > threshold:
                    similarity_scores.append((d, total_score))
        if threshold >= 0.8:
            print("similarity_scores:: ",similarity_scores)
            # Find the dictionary with the highest cumulative similarity score
            best_match = max(similarity_scores, key=lambda x: x[1], default=(None, 0))
            
            # Return the dictionary with the highest score
            filterred_data = [best_match[0]] if best_match[1] > 0.6 else None
        else:
            filterred_data = [elm[0] for elm in similarity_scores]
        return filterred_data
    except Exception as e:
        # Handle exceptions appropriately
        logger.exception(f"find_best_match_dict_mod:: error occurred: {e}")
        return None
    
async def load_location_data():
    try:
        file_path = os.path.join(".","app","templates","location_data.csv")
        df = pd.read_csv(file_path)
        df = df.dropna()
        data = df.to_dict("records")
        return data
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"load_location_data:: Error : {e}")
        raise e


async def comparison_opening_data(db, schedule_id):
    try:
        query_text = """
            SELECT 
                *
            FROM 
                opening_change_stats
            WHERE 
                schedule_id = :schedule_id;
        """
        result = db.execute(text(query_text), {"schedule_id": schedule_id})
        records = result.mappings().all()

        member_query = """
            SELECT JSON_OBJECTAGG(id, CONCAT(first_name, ' ', last_name)) AS user_dict
            FROM members
            WHERE is_active = TRUE;
        """
        member_result = db.execute(text(member_query)).mappings().first()

        user_dict = {}
        if member_result and member_result["user_dict"]:
            user_dict = json.loads(member_result["user_dict"])

        schedule_amount_query = """
            SELECT final_extended_sell_amount
            FROM schedules
            WHERE id = :schedule_id;
        """
        schedule_result = db.execute(text(schedule_amount_query), {"schedule_id": schedule_id}).mappings().first()
        current_schedule_final_extended_sell_amount = schedule_result["final_extended_sell_amount"] if schedule_result else 0

        response_data = defaultdict(lambda: defaultdict(dict))
        total_price_difference = 0 

        response_data["components"] = {}

        for row in records:
            updated_by = row["updated_by"]
            full_name = user_dict.get(updated_by, "") if updated_by else ""

            if row["component"].lower() == "door":
                component = f"{row['component']}-{row['part_number']}"
            else:
                component = row["component"]

            field = row["field_name"]
            row_dict = dict(row)
            row_dict["updated_by"] = full_name

            # schedule_final_base_amount = row["schedule_final_base_amount"] or 0
            # take_off_final_base_amount = row["take_off_final_base_amount"] or 0
            schedule_final_extended_sell_amount = row["schedule_final_extended_sell_amount"] or 0
            take_off_final_extended_sell_amount = row["take_off_final_extended_sell_amount"] or 0
            price_difference = schedule_final_extended_sell_amount - take_off_final_extended_sell_amount

            row_dict["price_difference"] = price_difference
            total_price_difference += price_difference
            if component not in response_data["components"]:
                response_data["components"][component] = {}

            response_data["components"][component][field] = row_dict
        
        current_schedule_final_extended_sell_amount = current_schedule_final_extended_sell_amount if current_schedule_final_extended_sell_amount else 0
        total_price_difference = total_price_difference if total_price_difference else 0
        response_data["total"] = {
            "total_previous_value": current_schedule_final_extended_sell_amount - total_price_difference,
            "total_current_price": current_schedule_final_extended_sell_amount,
            "total_price_difference": total_price_difference
        }

        return response_data, "Data fetched successfully"

    except Exception as e:
        logger.exception(f"comparison_opening_data:: Error : {e}")
        raise e




async def set_opening_discount_to_schedule_data(
        db, 
        price_component_data, 
        manufacturer_id,
        brand_id,
        raw_material_id,
        project_id,
        discount, 
        discount_type
    ):
    try:
        if discount is None:
            if price_component_data.discount and price_component_data.discount != 0:
                discount = price_component_data.discount
                discount_type = price_component_data.discount_type.value if price_component_data.discount_type else "PERCENTAGE"
            else:
                query_text = """
                    SELECT 
                        COALESCE(prmmq.discount, rmcm.discount_percentage) AS discount,
                        COALESCE(prmmq.discount_type, "PERCENTAGE") AS discount_type
                    FROM
                        raw_material_catalog_mapping AS rmcm
                    left JOIN
                        project_raw_material_manufacturer_quotes AS prmmq
                        ON
                        prmmq.raw_materials_catalog_mapping_id = rmcm.id
                        AND
                        prmmq.project_id = :project_id
                    WHERE 
                        rmcm.manufacturer_id = :manufacturer_id
                    AND 
                        rmcm.raw_material_id = :raw_material_id
                    AND 
                        (
                            (:brand_id IS NULL AND rmcm.brand_id IS NULL) OR rmcm.brand_id = :brand_id
                        );
                """
                result = db.execute(
                    text(query_text), 
                    {
                        "project_id": project_id,
                        "raw_material_id": raw_material_id,
                        "manufacturer_id": manufacturer_id,
                        "brand_id": brand_id
                    }
                ).fetchone()
                if result:
                    discount = result.discount
                    discount_type = result.discount_type if isinstance(result.discount_type, str) else result.discount_type.value
                else:
                    discount = 0
                    discount_type = "PERCENTAGE"
        price_component_data.discount = discount
        price_component_data.discount_type = discount_type
        db.flush()
        return discount, discount_type
    except Exception as e:
        logger.exception(f"set_opening_discount_to_schedule_data:: Error : {e}")
        raise e


async def set_opening_breakups_to_schedule_data(db, schedule_id, component):
    try:
        if component in ["FRAME", "DOOR"]:
            manufacturer_id = None
            brand_id = None
            discount = None
            discount_type = None
            surcharge = None
            surcharge_type = None
            margin = None
            markup = None
            catalog_field = f"{component.lower()}_catalog"
            catalog_data = None
            series_field = f"{component.lower()}_series"
            series_data = None
            scedule_info = db.query(Schedules).get(schedule_id)
            project_id = scedule_info.project_id
            # print("project_id:: ",project_id)
            price_component_data = db.query(ScheduleData).filter(
                ScheduleData.schedule_id == schedule_id, 
                ScheduleData.component == component, 
                ScheduleData.has_price_dependancy == True,
                ScheduleData.latest_data == True
            ).all()
            for data in price_component_data:
                if data.name == catalog_field:
                    catalog_data = data
                if data.name == series_field:
                    series_data = data
            catalog_mapping = await get_ctalog_details(db, catalog_data.value)
            if "manufacturer" in catalog_mapping:
                manufacturer_id = catalog_mapping["manufacturer"]["id"]
            if "brand" in catalog_mapping:
                brand_id = catalog_mapping["brand"]["id"]
            raw_material_id = None
            if component.lower() == "frame":
                raw_material_id = scedule_info.frame_material_id
            if component.lower() == "door":
                raw_material_id = scedule_info.door_material_id
            for data in price_component_data:
                if data.name not in [catalog_field, series_field]:
                    if discount is None:
                        discount, discount_type = await set_opening_discount_to_schedule_data(db, data, manufacturer_id, brand_id, raw_material_id, project_id, discount, discount_type)
                    if surcharge is None:
                        surcharge = data.surcharge
                    if surcharge_type is None:
                        surcharge_type = data.surcharge_type.value if data.surcharge_type else "PERCENTAGE"
                    if margin is None:
                        margin = data.margin
                    if markup is None:
                        markup = data.markup
                    quantity = data.quantity
                    total_amount = data.total_amount
                    total_base_amount = total_amount - await get_exact_breakup_amount(total_amount, discount, discount_type)
                    total_sell_amount = total_base_amount + await get_exact_breakup_amount(total_base_amount, markup)
                    total_extended_sell_amount = total_sell_amount + await get_exact_breakup_amount(total_sell_amount, surcharge, surcharge_type)
                    final_amount = total_amount * quantity
                    final_base_amount = quantity * total_base_amount
                    final_sell_amount = quantity * total_sell_amount
                    final_extended_sell_amount = quantity * total_extended_sell_amount
                    data.discount = discount
                    data.discount_type = discount_type
                    data.surcharge = surcharge
                    data.surcharge_type = surcharge_type
                    data.margin = margin
                    data.markup = markup
                    data.total_amount = total_amount
                    data.total_base_amount = total_base_amount
                    data.total_sell_amount = total_sell_amount
                    data.total_extended_sell_amount = total_extended_sell_amount
                    data.final_amount = final_amount
                    data.final_base_amount = final_base_amount
                    data.final_sell_amount = final_sell_amount
                    data.final_extended_sell_amount = final_extended_sell_amount
                    db.flush()
        return True
    except Exception as e:
        logger.exception(f"set_opening_breakups_to_schedule_data:: Error : {e}")
        raise e



async def get_schedule_summary(db, schedule_id):
    try:
        query_text = """
            SELECT
                schedule_id,
                ROUND(SUM(total_amount),3) AS total_amount,
                ROUND(SUM(total_base_amount),3) AS total_base_amount,
                ROUND(SUM(total_sell_amount),3) AS total_sell_amount,
                ROUND(SUM(total_extended_sell_amount),3) AS total_extended_sell_amount,
                ROUND(SUM(final_amount),3) AS final_amount,
                ROUND(SUM(final_base_amount),3) AS final_base_amount,
                ROUND(SUM(final_sell_amount),3) AS final_sell_amount,
                ROUND(SUM(final_extended_sell_amount),3) AS final_extended_sell_amount
            FROM
                (
                    (
                        SELECT 
                            schedule_id,
                            part_number,
                            component,
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
                            sd.component in ("DOOR", "FRAME")
                            AND 
                            sd.latest_data = true
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
            GROUP BY
                schedule_id;
        """
        result = db.execute(
            text(query_text), 
            {
                "schedule_id": schedule_id,
            }
        )
        columns = result.keys()
        data = result.fetchone()
        result = dict(zip(columns, data))
        return result
    except Exception as e:
        logger.exception(f"get_schedule_summary:: Error : {e}")
        return None
    

async def update_schedule_stats(db, schedule_id):
    try:
        await update_schedule_opening_hardware_stats(db, schedule_id)
        db.flush()
        result = await get_schedule_summary(db, schedule_id)
        print("--------------------------------")
        print("result:: ",result)
        print("------------------------")

        if result:
            (
                db.query(Schedules)
                .filter(
                    Schedules.id == schedule_id
                )
                .update(
                    {
                        "total_amount": result["total_amount"],
                        "total_base_amount": result["total_base_amount"],
                        "total_sell_amount": result["total_sell_amount"],
                        "total_extended_sell_amount": result["total_extended_sell_amount"],
                        "final_amount": result["final_amount"],
                        "final_base_amount": result["final_base_amount"],
                        "final_sell_amount": result["final_sell_amount"],
                        "final_extended_sell_amount": result["final_extended_sell_amount"],
                    },
                    synchronize_session=False
                )
            )
            db.flush()
        return True
    except Exception as e:
        logger.exception(f"update_schedule_stats:: Error : {e}")
        raise e

async def update_schedule_opening_hardware_stats(db: Session, schedule_id: str):
    try:
        schedule_opening_hardware_data = db.query(ScheduleOpeningHardwareMaterials).filter(
            ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
        ).all()
        for elm in schedule_opening_hardware_data:
            if elm:
                # Update the necessary fields
                db.query(ScheduleOpeningHardwareMaterials).filter(
                    ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
                ).update(
                    {
                        "final_amount": elm.quantity * elm.total_amount,
                        "final_base_amount": elm.quantity * elm.total_base_amount,
                        "final_sell_amount": elm.quantity * elm.total_sell_amount,
                        "final_extended_sell_amount": elm.quantity * elm.total_extended_sell_amount,
                    },
                    synchronize_session=False
                )
        return True
    except Exception as e:
        logger.exception(f"update_schedule_opening_hardware_stats:: Error : {e}")
        raise e

async def create_adon_opening_field(db: Session, payload: AdonOpeningFieldCreateSchema):
    try:
        new_field = AdonOpeningFields(
            name=payload.name,
            desc=payload.name,
            search_keywords=payload.name,
            has_price_dependancy=False,
            is_active=False,
            field_type=payload.field_type,
            field_category="OPENING_SCHEDULE",
            is_adon_field=True,
            is_door_data=False,
            is_frame_data=False,
            is_hw_data=False,
            is_opening_data=True,
            sort_order=9999,
            rule=None
        )

        db.add(new_field)
        db.flush()
        db.refresh(new_field)
        return new_field.to_dict
    except Exception as e:
        logger.exception(f"create_adon_opening_field:: Error : {e}")
        raise e
    

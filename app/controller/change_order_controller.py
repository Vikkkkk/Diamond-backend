import json
from loguru import logger
from fastapi import UploadFile, HTTPException
from models.change_order_status_logs import ChangeOrderStatusLogs
from repositories.schedule_repositories import update_schedule_stats
from models.change_order import ChangeOrder
from utils.schedule_data_helper import compare_schedule_data
from utils.schedule_hardware_data_helper import compare_schedule_hardware_data
from models.schedule_data import ScheduleData
from models.schedules import Schedules
from utils.common import generate_uuid
from utils.request_handler import call_post_api
from controller.schedule_controller import get_left_over_feature_data, post_process_price_data, prepare_price_fetch_data
from repositories import change_order_repositories
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from collections import defaultdict
from schemas.schedule_data_schema import changeOrderScheduleDataBulkSaveSchema
from schemas.hardware_group_material_schema import ScheduleHardwarMaterialRequest



async def create_change_order(db: Session, current_member, data: dict, files: dict):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            co_id, message = await change_order_repositories.create_change_order(
                db=db,
                data=data,
                files=files,
                created_by=current_member.id
            )
            if not co_id:
                db.rollback()
                return JSONResponse(status_code=400, content={"message": message, "status": "failed"})

            return JSONResponse(
                status_code=201,
                content={
                    "change_order_id": co_id,
                    "message": message
                }
            )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error creating change order: {str(e)}")


async def update_change_order(
    db: Session,
    current_member,
    project_id: str,
    change_order_id: str,
    data: dict,
    files: dict,
):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            co_id, message = await change_order_repositories.update_change_order(
                db=db,
                project_id=project_id,
                change_order_id=change_order_id,
                data=data,
                files=files,
                updated_by=current_member.id
            )
            if not co_id:
                db.rollback()
                return JSONResponse(status_code=400, content={"message": message, "status": "failed"})
            return JSONResponse(
                status_code=200,
                content={
                    "change_order_id": co_id,
                    "message": message
                }
            )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error updating change order: {str(e)}")


async def delete_change_order(
    db: Session,
    project_id: str,
    change_order_id: str
):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            co_id, message = await change_order_repositories.delete_change_order(
                db=db,
                project_id=project_id,
                change_order_id=change_order_id,
            )

            if not co_id:
                db.rollback()
                return JSONResponse(status_code=404, content={"message": message, "status": "failed"})

            return JSONResponse(
                status_code=200,
                content={
                    "change_order_id": co_id,
                    "message": message,
                }
            )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error deleting change order: {str(e)}")


async def list_change_orders(
    db: Session,
    project_id: str,
    is_completed: bool,
    page: int,
    page_size: int,
):
    try:
        result_data, page_count, total_items = await change_order_repositories.get_all_change_orders(
            db, project_id,is_completed,page, page_size
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": result_data,
                "page_count": page_count,
                "item_count": total_items,
            },
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list change orders: {str(e)}")



async def get_change_order_detail(db: Session, change_order_id: str):
    try:
        if db.in_transaction():
            db.commit()
        with db.begin():
            co_data = await change_order_repositories.get_change_order_detail(
                db=db,
                change_order_id=change_order_id
            )
            if not co_data:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order not found", "status": "failed"}
                )
            return JSONResponse(
            status_code=200,
            content={
                "data": co_data,
                "status":"success"
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error fetching change order detail: {str(e)}")



async def get_next_possible_change_order_number(db: Session):
    try:
        co_number = await change_order_repositories.get_next_possible_change_order_number(db=db)

        return JSONResponse(
            status_code=200,
            content={
                "data": co_number,
                "status": "success"
            }
        )
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get next possible change order number: {str(e)}")


async def get_change_order_openings_data(db: Session, project_id: str):
    try:
        openings = await change_order_repositories.get_change_order_openings_info(db, project_id)

        if not openings:
            return JSONResponse(
                status_code=200,
                content={"data": {}, "message": "No Change Order openings found."},
            )
        grouped_data = defaultdict(list)
        print("available_schedules:: ", len(openings))
        for co_schedule in openings:
            co_schedule_dict = co_schedule.to_dict
            area_name = co_schedule.area or "Unknown Area"
            grouped_data[area_name].append(co_schedule_dict)
        return JSONResponse(
            status_code=200,
            content={"data": dict(grouped_data), "message": "Data fetched successfully."},
        )

    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        )


async def update_schedule_data(db: Session, co_id: str, payload: changeOrderScheduleDataBulkSaveSchema, updated_by: str):
    try:
        with db.begin():
            co_info = db.query(ChangeOrder).get(co_id)
            if not co_info:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order not found", "status": "failed"}
                )
            if co_info.current_status.value.lower() == "in_review":
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order already in review", "status": "failed"}
                )
            if co_info.current_status.value.lower() == "approved":
                return JSONResponse(
                    status_code=400,
                    content={"message": "Approved Change Orders can not be modified", "status": "failed"}
                )
        schedule_data_dict = payload.model_dump(exclude_unset=True)
        fields = schedule_data_dict.get('fields', {})
        component = schedule_data_dict.get('component')
        schedule_id = schedule_data_dict.get("schedule_id")
        part_number = schedule_data_dict.get("part_number", None)
        # print("component:: ",component)
        request_data= await prepare_price_fetch_data(db, fields, component, schedule_id, part_number)
        original_request_data = request_data["original_request_data"]
        base_price_request_data = request_data["base_price"]
        adon_price_request_data = request_data["adon_price"]
        del request_data["original_request_data"]
        with db.begin():
            if (len(base_price_request_data.keys()) > 0) or (len(adon_price_request_data)):
                # In case we are performing operation for Frame or door as it will have something related to base price and adon price
                # print("request_data", request_data)
                response = await call_post_api("diamond/bulkprice/get_bulkprice", json.dumps(request_data))
                if int(response["status_code"]) == 200:
                    resp_data = response["response"]["data"]
                    left_over_feature_data = resp_data["left_over_feature_data"]
                    base_price = resp_data["base_price"]
                    adon_prices = resp_data["adon_prices"]
                    if left_over_feature_data is not None:
                        # In case we need to have further selection to make in order to get the base price
                        selected_data = {}
                        for indx, elm in enumerate(left_over_feature_data):
                            if "_id" in elm:
                                left_over_feature_data[indx]["id"] = elm["_id"]
                                del left_over_feature_data[indx]["_id"]
                            left_over_selected_data = await get_left_over_feature_data(
                                db,
                                elm["featureCode"],
                                schedule_id,
                                component
                            )
                            if left_over_selected_data is not None:
                                selected_data[elm["featureCode"]] = left_over_selected_data
                        return JSONResponse(content={"message": "Need to select further information in order to get the base price", "data": left_over_feature_data, "selected_data": selected_data}, status_code=202)
                    else:
                        # In case we dont have any pending field to be selected
                        if base_price is None:
                            return JSONResponse(content={"message": "Invalid Option selection"}, status_code=400)
                        else:
                            response_data = await post_process_price_data(
                                db,
                                base_price_request_data["manufacturerCode"],
                                base_price_request_data["brandCode"],
                                original_request_data,
                                base_price,
                                adon_prices,
                                component
                            )
                            final_resp = {}
                            for indx, elm in enumerate(response_data):
                                print(indx, elm['name'])
                                final_resp[elm["name"]] = elm
                                # print("elm:: ",elm["name"])
                                existing_data = (
                                    db.query(ScheduleData)
                                    .filter(
                                        ScheduleData.schedule_id == schedule_id, 
                                        ScheduleData.name == elm["name"], 
                                        ScheduleData.component == elm["component"],
                                        ScheduleData.part_number == part_number
                                    )
                                    .first()
                                )
                                if existing_data:
                                    final_resp[elm["name"]]["id"] = existing_data.id
                                else:
                                    new_data = ScheduleData(**elm)
                                    db.add(new_data)
                                    db.flush()
                                    final_resp[elm["name"]]["id"] = generate_uuid()
                            if component == "FRAME":
                                frame_data = await change_order_repositories.get_frame_hardware_prep_data(db, schedule_id, component)
                                if frame_data is not None:
                                    frame_data["id"] = generate_uuid()
                                    final_resp[frame_data["name"]] = frame_data
                            payload.fields = final_resp
                else:
                    return JSONResponse(content={"message": "Unable to fetch pricebook data"}, status_code=int(response["status_code"]))
            else:
                final_resp = {}
                # print("original_request_data:: ",original_request_data)
                for field_name, field_value in original_request_data.items():
                    old_prep_data = (
                        db.query(ScheduleData)
                        .filter(
                            ScheduleData.schedule_id == schedule_id, 
                            ScheduleData.component == component,
                            ScheduleData.part_number == part_number,
                            ScheduleData.name == field_name,
                        )
                        .first()
                    )
                    prep_id = None
                    if old_prep_data:
                        prep_id = old_prep_data.id
                    else:
                        prep_id = generate_uuid()
                    final_resp[field_value["name"]] = field_value
                    final_resp[field_value["name"]]["id"] = prep_id
                if component == "FRAME":
                    frame_data = await change_order_repositories.get_frame_hardware_prep_data(db, schedule_id, component)
                    if frame_data is not None:
                        frame_data["id"] = generate_uuid()
                        final_resp[frame_data["name"]] = frame_data
                payload.fields = final_resp
            updated_schedule = await change_order_repositories.update_co_schedule_data(
                db=db,
                co_id=co_id,
                payload=payload,
                updated_by=updated_by
            )
            if not updated_schedule:
                return JSONResponse(
                    status_code=400,
                    content={"message": "CoSchedule not found", "status": "failed"}
                )
        return JSONResponse(
            status_code=200,
            content={
                "data": updated_schedule,
                "message": "Schedule data updated successfully"
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error updating schedule data: {str(e)}")


async def get_change_order_schedule_data(db: Session, co_id: str, opening_type: str, part_number: str, schedule_id: str):
    """
    Controller: Get schedule data from CoSchedules.current_version
    """
    try:
        data = await change_order_repositories.get_change_order_schedule_data(
            db=db, co_id=co_id, opening_type=opening_type, part_number=part_number,schedule_id = schedule_id
        )
        return {
            "data": data,
            "message": "Data fetch successfull",
            "component": opening_type,
            "part_number": int(part_number) if part_number and part_number.isnumeric() else None,
        }
    except Exception as e:
        logger.error(f"get_change_order_schedule_data:: Error for co_id={co_id}: {str(e)}")


async def update_change_order_hardware_data(
    db: Session, co_id: str, schedule_id: str, payload: ScheduleHardwarMaterialRequest, updated_by: str
):
    try:
        with db.begin():
            co_info = db.query(ChangeOrder).get(co_id)
            if not co_info:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order not found", "status": "failed"}
                )
            if co_info.current_status.value.lower() == "in_review":
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order already in review", "status": "failed"}
                )
            if co_info.current_status.value.lower() == "approved":
                return JSONResponse(
                    status_code=400,
                    content={"message": "Approved Change Orders can not be modified", "status": "failed"}
                )
        with db.begin():
            updated_hardware = await change_order_repositories.update_co_hardware_data(
                db=db,
                co_id=co_id,
                schedule_id=schedule_id,
                payload=payload,
                updated_by=updated_by
            )
            if not updated_hardware:
                return JSONResponse(
                    status_code=400,
                    content={"message": "CoHardware not found", "status": "failed"}
                )
        return JSONResponse(
            status_code=200,
            content={
                "data": updated_hardware,
                "message": "Hardware data updated successfully"
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error updating hardware data: {str(e)}")





async def get_change_order_hardware_data(db: Session, co_id: str, schedule_id: str):
    """
    Controller: Get hardware data from CoSchedules.current_version
    """
    try:
        data = await change_order_repositories.get_change_order_hardware_data(
            db=db, co_id=co_id, schedule_id=schedule_id
        )
        return {
            "data": data,
            "message": "Data fetch successfull",
        }
    except Exception as e:
        logger.error(f"get_change_order_hardware_data:: Error for co_id={co_id}: {str(e)}")




async def get_change_order_version_comparison(
        db: Session,
        change_order_id: str,
        project_id: str,
        schedule_id: str):
    try:
        if db.in_transaction():
            db.commit()
        with db.begin():
            hardware_data_current_version_fields, schedule_data_current_version_fields, opening_data = await change_order_repositories.get_change_order_schedule_data_versions(
                db=db,
                co_id=change_order_id,
                schedule_id=schedule_id,
                version=None,
                is_latest=True
            )
            hardware_data_v0_version_fields, schedule_data_v0_version_fields, opening_data = await change_order_repositories.get_change_order_schedule_data_versions(
                db=db,
                co_id=change_order_id,
                schedule_id=schedule_id,
                version="v0",
                is_latest=False
            )
            if (
                hardware_data_current_version_fields is None and 
                schedule_data_current_version_fields is None and 
                hardware_data_v0_version_fields is None and
                schedule_data_v0_version_fields is None
            ):
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order versions not found", "status": "failed"}
                )
            # print("schedule_data_v0_version_fields:: ", schedule_data_v0_version_fields.keys())
            # print("schedule_data_current_version_fields:: ", schedule_data_current_version_fields.keys())
            schedule_data_version_diff = await compare_schedule_data(
                schedule_data_v0_version_fields,
                schedule_data_current_version_fields,
                project_id=project_id,
                schedule_id=schedule_id,
                opening_number=opening_data.get("opening_number", None),
            )
            hardware_data_v0_version_fields = hardware_data_v0_version_fields.get("fields", {}) if hardware_data_v0_version_fields else {}
            hardware_data_current_version_fields = hardware_data_current_version_fields.get("fields", {}) if hardware_data_current_version_fields else {}
            schedule_hardware_data_version_diff = await compare_schedule_hardware_data(
                hardware_data_v0_version_fields,
                hardware_data_current_version_fields,
                project_id=project_id,
                schedule_id=schedule_id,
                opening_number=opening_data.get("opening_number", None),
            )

            if not schedule_data_version_diff and not schedule_hardware_data_version_diff:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order differences not found", "status": "failed"}
                )
            response = []
            response.extend(schedule_data_version_diff)
            response.extend(schedule_hardware_data_version_diff)


            response_data = defaultdict(lambda: defaultdict(dict))
            total_price_difference = 0 
            total_initial_schedule_data_final_amount = 0
            total_current_schedule_data_final_amount = 0
            response_data["components"] = {}

            for row in response:
                if row["component"].lower() == "door":
                    component = f"{row['component']}-{row['part_number']}"
                else:
                    component = row["component"]

                field = row["field_name"]
                row_dict = dict(row)

                initial_schedule_final_base_amount = row["initial_schedule_final_base_amount"] or 0
                current_schedule_final_base_amount = row["current_schedule_final_base_amount"] or 0
                price_difference = current_schedule_final_base_amount - initial_schedule_final_base_amount

                row_dict["price_difference"] = price_difference
                total_price_difference += price_difference
                total_initial_schedule_data_final_amount += initial_schedule_final_base_amount
                total_current_schedule_data_final_amount += current_schedule_final_base_amount
                if component not in response_data["components"]:
                    response_data["components"][component] = {}

                response_data["components"][component][field] = row_dict
            
            response_data["total"] = {
                "total_previous_value": total_initial_schedule_data_final_amount,
                "total_current_price": total_current_schedule_data_final_amount,
                "total_price_difference": total_price_difference
            }

            return JSONResponse(
            status_code=200,
            content={
                "data": response_data,
                "status":"success"
            }
        )

    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error fetching change order detail: {str(e)}")
    





async def apply_change_order_changes(
        db: Session,
        change_order_id: str,
        project_id: str,
        created_by: str
    ):
    try:
        if db.in_transaction():
            db.commit()
        with db.begin():
            co_info = db.query(ChangeOrder).get(change_order_id)
            co_current_status = co_info.current_status if co_info.current_status and isinstance(co_info.current_status, str) else co_info.current_status.value if co_info.current_status else None
            if co_current_status is None:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Valid change Order status not found", "status": "failed"}
                )
            if not co_info:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order not found", "status": "failed"}
                )
            if co_current_status.lower() == "completed" or co_info.has_applied:
                return JSONResponse(
                    status_code=400,
                    content={"message": "Change Order already applied or completed", "status": "failed"}
                )
            if co_current_status.lower() != "approved":
                return JSONResponse(
                    status_code=400,
                    content={"message": "Only approved Change Orders can be applied", "status": "failed"}
                )
            for co_schedule in co_info.co_schedules:
                schedule_id = co_schedule.schedule_id
                schedule_info = db.query(Schedules).get(schedule_id)
                comparison_data = {}
                schedule_data_json = {}
                schedule_hardware_data_json = {}
                hardware_data_current_version_fields, schedule_data_current_version_fields, opening_data = await change_order_repositories.get_change_order_schedule_data_versions(
                    db=db,
                    co_id=change_order_id,
                    schedule_id=schedule_id,
                    version=None,
                    is_latest=True
                )
                schedule_data_json = {
                    "current_version": schedule_data_current_version_fields
                }
                schedule_hardware_data_json = {
                    "current_version": hardware_data_current_version_fields
                }
                if schedule_info and (schedule_info.has_door_ordered or schedule_info.has_frame_ordered or schedule_info.has_hw_ordered):
                    
                    
                    hardware_data_v0_version_fields, schedule_data_v0_version_fields, opening_data = await change_order_repositories.get_change_order_schedule_data_versions(
                        db=db,
                        co_id=change_order_id,
                        schedule_id=schedule_id,
                        version="v0",
                        is_latest=False
                    )
                    if (
                        hardware_data_current_version_fields is not None and 
                        schedule_data_current_version_fields is not None and 
                        hardware_data_v0_version_fields is not None and
                        schedule_data_v0_version_fields is not None
                    ):
                        # print("schedule_data_v0_version_fields:: ", schedule_data_v0_version_fields.keys())
                        # print("schedule_data_current_version_fields:: ", schedule_data_current_version_fields.keys())
                        schedule_data_version_diff = await compare_schedule_data(
                            schedule_data_v0_version_fields,
                            schedule_data_current_version_fields,
                            project_id=project_id,
                            schedule_id=schedule_id,
                            opening_number=opening_data.get("opening_number", None),
                        )
                        hardware_data_v0_version_fields = hardware_data_v0_version_fields.get("fields", {}) if hardware_data_v0_version_fields else {}
                        hardware_data_current_version_fields = hardware_data_current_version_fields.get("fields", {}) if hardware_data_current_version_fields else {}
                        schedule_hardware_data_version_diff = await compare_schedule_hardware_data(
                            hardware_data_v0_version_fields,
                            hardware_data_current_version_fields,
                            project_id=project_id,
                            schedule_id=schedule_id,
                            opening_number=opening_data.get("opening_number", None),
                        )
                    response = []
                    if schedule_data_version_diff or schedule_hardware_data_version_diff:
                        response.extend(schedule_data_version_diff)
                        response.extend(schedule_hardware_data_version_diff)
                    response_data = defaultdict(lambda: defaultdict(dict))
                    total_price_difference = 0 
                    total_initial_schedule_data_final_amount = 0
                    total_current_schedule_data_final_amount = 0
                    response_data["components"] = {}
                    for row in response:
                        if row["component"].lower() == "door":
                            component = f"{row['component']} {row['part_number']}"
                        else:
                            component = row["component"]

                        field = row["field_name"]
                        row_dict = dict(row)
                        initial_schedule_final_base_amount = row["initial_schedule_final_base_amount"] or 0
                        current_schedule_final_base_amount = row["current_schedule_final_base_amount"] or 0
                        price_difference = current_schedule_final_base_amount - initial_schedule_final_base_amount
                        row_dict["price_difference"] = price_difference
                        total_price_difference += price_difference
                        total_initial_schedule_data_final_amount += initial_schedule_final_base_amount
                        total_current_schedule_data_final_amount += current_schedule_final_base_amount
                        if component not in response_data["components"]:
                            response_data["components"][component] = {}

                        response_data["components"][component][field] = row_dict
                
                    response_data["total"] = {
                        "total_previous_value": total_initial_schedule_data_final_amount,
                        "total_current_price": total_current_schedule_data_final_amount,
                        "total_price_difference": total_price_difference
                    }
                    comparison_data = response_data
                comparison_data_json = comparison_data.get("components", {})
                await change_order_repositories.save_current_version_to_schedule(
                    db=db,
                    schedule_id=schedule_id,
                    schedule_data_json=schedule_data_json,
                    schedule_hardware_data_json=schedule_hardware_data_json,
                    schedule_info=schedule_info,
                    comparison_data_json=comparison_data_json,
                )
                db.flush()
                print("Data saved for schedule_id:: ", schedule_id)
                await update_schedule_stats(db, schedule_id)
                db.flush()
                print("Stats updated for schedule_id:: ", schedule_id)
            # All schedules are processed, now we can mark the change order as completed
            # change
            co_info.current_status = "COMPLETED"
            co_info.has_applied = True
            log_entry = ChangeOrderStatusLogs(
                co_id=co_info.id,
                status="COMPLETED",
                created_by=created_by,
            )
            db.add(log_entry)
            return JSONResponse(
            status_code=200,
            content={
                "message": "Change Order changes applied successfully",
                "status":"success"
            }
        )

    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error fetching change order detail: {str(e)}")
    



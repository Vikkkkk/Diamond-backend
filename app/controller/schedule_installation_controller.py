from sqlalchemy.orm import Session
from loguru import logger
from collections import defaultdict
from datetime import datetime
from models.schedule_installation_mapping_component_data import ScheduleInstallationMappingComponentData
from repositories import schedule_installation_repositories
from repositories import work_order_repositories
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse
from models.members import Members
from models.schedule_installation_mapping import ScheduleInstallationMapping
from schemas.schedule_installation_opening_schema import ScheduleInstallationMappingSchema, ScheduleInstallationCommentBase
from models.schedule_installation_mapping_comments import ScheduleInstallationMappingComments
from models.project_installation_plan_docs import ProjectInstallationPlanDocs
from utils.common import delete_from_s3, get_aws_full_path
from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.schedule_installation_mapping_attachment import ScheduleInstallationMappingAttachment
from typing import Optional



async def get_installation_openings_data(db: Session, project_id: str, work_order_id: str):
    """
    Retrieves and structures installation schedule data for a given project,
    grouped by area. Each schedule includes all fields from the model.

    Args:
        db (Session): SQLAlchemy session.
        project_id (str): The ID of the project.

    Returns:
        dict: { area_name: [schedules] }
    """
    try:
        openings = await schedule_installation_repositories.get_installation_openings_info(db, project_id,work_order_id)

        if len(openings)==0:
            return JSONResponse(
                    status_code=200,
                    content={
                        "data":{},
                        "message": "No Opening Found to be Installed",
                    },
                )

        colour_mapping = {
            "PENDING": "ORANGE",
            "IN_PROGRESS": "BLUE",
            "FAILED": "RED",
            "SUCCESS": "GREEN",
        }
        grouped_data = defaultdict(list)
        for schedule,has_marker in openings:
            schedule_dict = schedule.to_dict
            schedule_dict["has_marker"] = has_marker
            schedule_dict["mapping_status"] = ",".join(elm.status.value for elm in schedule.installation_schedule_mappings)
            schedule_dict["mapping_colour_code"] = ",".join(colour_mapping[elm.status.value] for elm in schedule.installation_schedule_mappings)
            area_name = schedule.area or "Unknown Area"
            grouped_data[area_name].append(schedule_dict)

        # return dict(grouped_data)
        return JSONResponse(
                    status_code=200,
                    content={
                        "data":dict(grouped_data),
                        "message": "Data fetched successfully.",
                    },
                )

    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_installation_unassigned_openings_info(db: Session, project_id: str):
    """
    Retrieves and structures installation schedule data for a given project,
    grouped by area. Each schedule includes all fields from the model.

    Args:
        db (Session): SQLAlchemy session.
        project_id (str): The ID of the project.

    Returns:
        dict: { area_name: [schedules] }
    """
    try:
        openings = await schedule_installation_repositories.get_installation_unassigned_openings_info(db, project_id)

        if len(openings)==0:
            return JSONResponse(
                    status_code=200,
                    content={
                        "data":{},
                        "message": "No Opening Found to be Installed",
                    },
                )

        colour_mapping = {
            "PENDING": "ORANGE",
            "IN_PROGRESS": "BLUE",
            "FAILED": "RED",
            "SUCCESS": "GREEN",
        }
        grouped_data = defaultdict(list)
        for schedule,has_marker in openings:
            schedule_dict = schedule.to_dict
            schedule_dict["has_marker"] = has_marker
            schedule_dict["mapping_status"] = ",".join(elm.status.value for elm in schedule.installation_schedule_mappings)
            schedule_dict["mapping_colour_code"] = ",".join(colour_mapping[elm.status.value] for elm in schedule.installation_schedule_mappings)
            area_name = schedule.area or "Unknown Area"
            grouped_data[area_name].append(schedule_dict)

        # return dict(grouped_data)
        return JSONResponse(
                    status_code=200,
                    content={
                        "data":dict(grouped_data),
                        "message": "Data fetched successfully.",
                    },
                )

    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def upload_floor_plan_controller(db:Session, project_id: str, area: str, current_member: Members, file: UploadFile):
    """
    Handles the upload of a floor plan document for a specific project and area.

    This controller function processes the incoming file upload request, saves the 
    installation plan document via the repository layer, and returns a JSON response 
    indicating success or failure.

    Args:
        db (Session): Database session for performing DB operations.
        project_id (str): The identifier of the project to which the floor plan belongs.
        area (str): The specific area within the project the floor plan corresponds to.
        current_member (Members): The user/member uploading the floor plan.
        file (UploadFile): The uploaded file object containing the floor plan document.

    Returns:
        JSONResponse: HTTP 201 response with a JSON body containing:
            - doc_id (str): The identifier of the saved document.
            - message (str): Success message.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if any exception occurs during processing.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            data =  await schedule_installation_repositories.save_installation_plan_doc(
                db,
                project_id=project_id,
                area=area,
                current_member=current_member,
                file=file
            )

            return JSONResponse(
                        status_code=201,
                        content={
                            "doc_id":data,
                            "message": "Floor plan uploaded successfully.",
                        },
                    )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")



async def get_floor_plans_data(db: Session, project_id: str, area: str):
    """
    Retrieves floor plan documents and associated member information for a given project and area.

    This function queries the repository layer to fetch floor plan data related to the specified
    project and area. It formats the results by including the member's full name who uploaded each document.
    If no floor plans are found, it returns a 400 response indicating no data.

    Args:
        db (Session): Database session for performing DB operations.
        project_id (str): The identifier of the project to retrieve floor plans for.
        area (str): The specific area within the project to filter floor plans.

    Returns:
        JSONResponse: 
            - HTTP 200 with a JSON body containing:
                - data (list): List of floor plan documents with member names.
                - message (str): Success message.
            - HTTP 400 with a message indicating no floor plans found if none exist.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if any exception occurs during processing.
    """
    
    try:
        floor_plans = await schedule_installation_repositories.get_floor_plans_info(db, project_id,area)

        if len(floor_plans)==0:
            return JSONResponse(
                    status_code=200,
                    content={
                        "data":[],
                        "message": "No Floor Plan Found.",
                    }
                )


        data = []
        for doc, member in floor_plans:
            doc_dict = doc.to_dict
            doc_dict["member_name"] = f"{member.first_name} {member.last_name}"
            data.append(doc_dict)

        return JSONResponse(
            status_code=200,
            content={
                "data": data,
                "message": "Data fetched successfully.",
            },
        )

    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    


async def assign_opening_to_floor_plan(db:Session, project_id: str, request_data, current_member: Members):
    """
    Assigns an opening to a floor plan within a specified project.

    This function delegates the assignment process to the repository layer, passing along 
    the project ID, the request data containing assignment details, and the current member performing the action.
    Upon successful assignment, it returns the ID of the created mapping along with a success message.

    Args:
        db (Session): Database session for performing DB operations.
        project_id (str): The identifier of the project where the opening will be assigned.
        request_data (Any): Data payload containing details required to assign the opening.
        current_member (Members): The member performing the assignment operation.

    Returns:
        JSONResponse: HTTP 201 response containing:
            - schedule_installation_mapping_id (str/int): The ID of the created assignment mapping.
            - message (str): Success message.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if any exception occurs during processing.
    """
    try:
        cleaned_data = request_data.model_dump(exclude_unset=True)
        
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            mapping = await schedule_installation_repositories.check_schedule_installation_mapping(db,cleaned_data["schedule_id"])
            if mapping:
                return JSONResponse(
                            status_code=400,
                            content={
                                "message": "This opening is already assigned to other place"
                            }
                        )

            schedule_installation_mapping_id =  await schedule_installation_repositories.to_assign_opening_to_floor_plan(
                db,
                project_id=project_id,
                request_data=request_data,
                current_member=current_member,
            )
            
            schedule_info = db.query(Schedules).get(cleaned_data["schedule_id"])

            await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                db=db,
                schedule_installation_mapping_id=schedule_installation_mapping_id,
                activity_type="Created Opening Marker",
                created_by=current_member.id,
                details={"opening_number": schedule_info.opening_number}
            )
            return JSONResponse(
                        status_code=201,
                        content={
                            "schedule_installation_mapping_id":schedule_installation_mapping_id,
                            "message": "Opening assigned successfully."
                        },
                    )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")


async def delete_opening_from_floor_plan(db:Session, schedule_installation_mapping_id):
    """
    Deletes an assigned opening from a floor plan based on the mapping ID.

    This function removes the ScheduleInstallationMapping record identified by the given ID 
    from the database, then commits the transaction. It returns a success message upon completion.

    Args:
        db (Session): Database session for performing DB operations.
        schedule_installation_mapping_id (int or str): The ID of the mapping to be deleted.

    Returns:
        JSONResponse: HTTP 201 response with a success message indicating removal.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if any exception occurs during deletion.
    """
    try:
        data = db.query(ScheduleInstallationMapping).filter(ScheduleInstallationMapping.id==schedule_installation_mapping_id).delete()
        db.commit()
        return JSONResponse(
                    status_code=201,
                    content={
                        "message": "Opening removed successfully."
                    },
                )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")



async def delete_all_opening_from_floor_plan(db: Session, schedule_installation_plan_doc_id: str, deleted_schedule_ids: str):
    try:
        # Parse comma-separated IDs into a list of strings
        ids_to_delete = [id.strip() for id in deleted_schedule_ids.split(',') if id.strip()]

        # Perform delete operation
        deleted_count = db.query(ScheduleInstallationMapping).filter(
            ScheduleInstallationMapping.schedule_installation_plan_doc_id == schedule_installation_plan_doc_id,
            ScheduleInstallationMapping.schedule_id.in_(ids_to_delete)
        ).delete(synchronize_session=False)

        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "message": f"{deleted_count} opening(s) removed successfully."
            },
        )
    except Exception as error:
        logger.exception("Error deleting openings: %s", str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")




async def add_mapping_comment(db, project_id, schedule_installation_mapping_id, comment, attachments, current_member):
    """
    Adds a comment to a schedule installation mapping within a project.

    This function calls the repository layer to add a comment associated with the specified
    project and mapping, recording the current member as the comment author. It returns 
    the new comment's ID along with a success message.

    Args:
        db (Session): Database session for performing DB operations.
        project_id (str): The identifier of the project where the comment is being added.
        data (ScheduleInstallationCommentBase): The comment data to be added.
        current_member: The member adding the comment (should have an `id` attribute).

    Returns:
        JSONResponse: HTTP 201 response with:
            - comment_id (int): The ID of the newly added comment.
            - message (str): Success message.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if an error occurs during the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            comment = await schedule_installation_repositories.add_comment(db, project_id, schedule_installation_mapping_id, comment, attachments, current_member.id)
            # return comment.to_dict
            schedule_installation_mapping_data = db.query(ScheduleInstallationMapping).get(schedule_installation_mapping_id)
            attachment_count = len(attachments) if attachments else 0
            attachment_note = "No Attachment" if attachment_count == 0 else f"{attachment_count} Attachment{'s' if attachment_count > 1 else ''}"

            await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                db=db,
                schedule_installation_mapping_id=schedule_installation_mapping_id,
                activity_type="Add Opening Installation Comment",
                created_by=current_member.id,
                details={
                    "opening_number": schedule_installation_mapping_data.installation_schedule.opening_number,
                    "comment": comment,
                    "attachments": attachment_note,
                }
            )
            wo_id = await work_order_repositories.get_wo_id_from_schedule_id(db, schedule_installation_mapping_data.schedule_id)
            if wo_id:
                await work_order_repositories.log_work_order_assignee_time(db, wo_id, current_member.id)

            return JSONResponse(
                        status_code=201,
                        content={
                            "comment_id":comment.id,
                            "message": "Mapping comment added successfully."
                        },
                    )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_mapping_comment(db, comment_id, schedule_installation_mapping_id, comment, attachments, project_id, deleted_attachment_ids, current_member):
    """
    Updates an existing comment on a schedule installation mapping within a project.

    This function delegates the update operation to the repository layer. If the comment with the
    specified ID does not exist, it returns a 400 response indicating the comment was not found.
    Otherwise, it returns the updated comment's ID with a success message.

    Args:
        db (Session): Database session for performing DB operations.
        comment_id (str): The identifier of the comment to update.
        data (ScheduleInstallationCommentBase): The updated comment data.
        project_id (str): The identifier of the project the comment belongs to.

    Returns:
        JSONResponse:
            - HTTP 201 with:
                - comment_id (str): The ID of the updated comment.
                - message (str): Success message.
            - HTTP 400 if the comment is not found.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if an error occurs during the update.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            comment_data = db.query(ScheduleInstallationMappingComments).get(comment_id)
            previous_comment = comment_data.comment
            updated_comment = await schedule_installation_repositories.update_comment(db, comment_id, schedule_installation_mapping_id, comment, attachments, project_id, deleted_attachment_ids, current_member.id)
            schedule_installation_mapping_data = db.query(ScheduleInstallationMapping).get(schedule_installation_mapping_id)

            await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                db=db,
                schedule_installation_mapping_id=schedule_installation_mapping_id,
                activity_type="Update Opening Installation Comment",
                created_by=current_member.id,
                details={
                    "opening_number": schedule_installation_mapping_data.installation_schedule.opening_number,
                    "previous_comment": previous_comment,
                    "current_comment": comment,
                    "attachments": "No Attachment" if not attachments else f"{len(attachments)} Attachments",
                }
            )
            wo_id = await work_order_repositories.get_wo_id_from_schedule_id(db, schedule_installation_mapping_data.schedule_id)
            if wo_id:
                await work_order_repositories.log_work_order_assignee_time(db, wo_id, current_member.id)

            if updated_comment is None:
                return JSONResponse(
                            status_code=400,
                            content={
                                "message": "Comment Not Found.",
                            },
                        )
            return JSONResponse(
                            status_code=201,
                            content={
                                "comment_id":updated_comment.id,
                                "message": "Mapping comment updated successfully."
                            },
                        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")


async def delete_mapping_comments(db: Session, comment_id: str, current_member):
    """
    Deletes a mapping comment identified by its comment ID.

    This function removes the ScheduleInstallationMappingComments record from the database
    based on the provided comment ID and commits the transaction. Returns a success message
    upon completion.

    Args:
        db (Session): Database session for performing DB operations.
        comment_id (str): The identifier of the comment to be deleted.

    Returns:
        JSONResponse: HTTP 200 response with a success message confirming deletion.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if an error occurs during deletion.
    """
    try:
        
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            comment = db.query(ScheduleInstallationMappingComments).filter(ScheduleInstallationMappingComments.id==comment_id).first()
            if not comment:
                return JSONResponse(
                            status_code=400,
                            content={
                                "message": "Comment Not Found.",
                            },
                        )
            current_comment = comment.comment
            schedule_installation_mapping_id = comment.schedule_installation_mapping_id

            schedule_installation_mapping_data = db.query(ScheduleInstallationMapping).get(schedule_installation_mapping_id)
            attachments = db.query(ScheduleInstallationMappingAttachment).filter(ScheduleInstallationMappingAttachment.schedule_installation_mapping_comment_id == comment_id).all()
            if attachments:
                attachment_ids = []
                for attachment in attachments:
                    attachment_ids.append(attachment.id)
                    await delete_from_s3(attachment.file_path)
                
                db.query(ScheduleInstallationMappingAttachment).filter(ScheduleInstallationMappingAttachment.id.in_(attachment_ids)).delete()

            db.delete(comment)
            await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                db=db,
                schedule_installation_mapping_id=schedule_installation_mapping_id,
                activity_type="Delete Opening Installation Comment",
                created_by=current_member.id,
                details={
                    "opening_number": schedule_installation_mapping_data.installation_schedule.opening_number,
                    "comment": current_comment
                }
            )
            wo_id = await work_order_repositories.get_wo_id_from_schedule_id(db, schedule_installation_mapping_data.schedule_id)
            if wo_id:
                await work_order_repositories.log_work_order_assignee_time(db, wo_id, current_member.id)

            return JSONResponse(
                            status_code=200,
                            content={
                                "message": "Mapping Comments Deleted successfully."
                            },
                        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")


async def get_schedule_installation_mappings_info(db: Session, mapping_id: str):
    """
    Retrieves schedule installation mapping data for a given mapping ID.

    This function calls the repository layer to fetch all schedule installation mappings
    associated with the provided mapping ID. It converts the result to a dictionary and
    returns it in a JSON response.

    Args:
        db (Session): Database session for performing DB operations.
        mapping_id (str): The identifier for the schedule installation mapping to retrieve.

    Returns:
        JSONResponse: HTTP 200 response containing:
            - data (dict): A mapping record represented as a dictionary.
            - message (str): Success message.

    Raises:
        HTTPException: Raises HTTP 500 Internal Server Error if an error occurs during retrieval.
    """
    try:
        result = await schedule_installation_repositories.get_schedule_installation_mappings_data(db, mapping_id)
        
        if not result:
            return JSONResponse(
                status_code=200,
                content={"message": "Mapping not found.", "data": {}}
            )

        mapping, member = result[0]
        data = mapping.to_dict

        if data.get("comments"):
            # Build attachment dictionary grouped by comment ID
            attachments_by_comment = {}
            if hasattr(mapping, "schedule_installation_mapping_attachments"):
                for attachment in mapping.schedule_installation_mapping_attachments:
                    comment_id = attachment.schedule_installation_mapping_comment_id
                    if comment_id not in attachments_by_comment:
                        attachments_by_comment[comment_id] = []
                    attachment_data = attachment.to_dict
                    attachment_data["file_path"] = get_aws_full_path(attachment_data["file_path"]) if attachment_data["file_path"] is not None else None
                    attachments_by_comment[comment_id].append(attachment_data)

            # Add member info and attachments to each comment
            for comment in data["comments"]:
                comment["member_name"] = f"{member.first_name} {member.last_name}" if member else None
                comment["member_id"] = member.id if member else None
                comment_id = comment.get("id")
                comment["attachments"] = attachments_by_comment.get(comment_id, [])

        

        # Add prep_name to each prep_data entry
        if data.get("prep_data"):
            for prep in data["prep_data"]:
                schedule_data_id = prep.get("schedule_data_id")
                if schedule_data_id:
                    schedule_data = db.query(ScheduleData).filter(ScheduleData.id == schedule_data_id).first()
                    prep["prep_name"] = schedule_data.name if schedule_data else None
            data["prep_data"] = sorted(data["prep_data"], key=lambda x: (x["component"], x["name"]))


        return JSONResponse(
            status_code=200,
            content={
                "data": data,
                "message": "Data fetched successfully."
            },
        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")




async def update_installation_prep_status(db: Session, status: str, component_id: str, current_member):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            component_data = db.query(ScheduleInstallationMappingComponentData).get(component_id)
            previous_status = component_data.status if isinstance(component_data.status, str) else component_data.status.value
            current_status = status
            component_name = component_data.name
            component_type = component_data.component if isinstance(component_data.component, str) else component_data.component.value
            component_update_count = db.query(ScheduleInstallationMappingComponentData).filter(
                ScheduleInstallationMappingComponentData.id == component_id
            ).update(
                {ScheduleInstallationMappingComponentData.status: status}
            )

            opening_status = await schedule_installation_repositories.get_opening_status(db, schedule_installation_mapping_id=component_data.schedule_installation_mapping_id)
            
            # Update main mapping status
            mapping_data = db.query(ScheduleInstallationMapping).get(component_data.schedule_installation_mapping_id)
            mapping_previous_status = mapping_data.status if isinstance(mapping_data.status, str) else mapping_data.status.value
            mapping_update_count = db.query(ScheduleInstallationMapping).filter(
                ScheduleInstallationMapping.id == component_data.schedule_installation_mapping_id
            ).update(
                {ScheduleInstallationMapping.status: opening_status}
            )

            if component_update_count == 0 and mapping_update_count == 0:
                return JSONResponse(
                            status_code=400,
                            content={
                                "message": "Installation Prep Not Found.",
                            },
                        )

            # db.commit()
            schedule_info = db.query(Schedules).get(component_data.schedule_id)

            await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                db=db,
                schedule_installation_mapping_id=component_data.schedule_installation_mapping_id,
                activity_type="Update Opening Component Installation Status",
                created_by=current_member.id,
                details={
                    "opening_number": schedule_info.opening_number,
                    "previous_status": previous_status,
                    "current_status": current_status,
                    "component_name": component_name,
                    "component_type": component_type,
                }
            )
            if opening_status != mapping_previous_status:
                await schedule_installation_repositories.log_schedule_installation_mapping_activity(
                    db=db,
                    schedule_installation_mapping_id=component_data.schedule_installation_mapping_id,
                    activity_type="Update Opening Installation Status",
                    created_by=current_member.id,
                    details={
                        "opening_number": schedule_info.opening_number,
                        "previous_status": mapping_previous_status,
                        "current_status": opening_status,
                        "component_name": component_name,
                        "component_type": component_type,
                    }
                )
            
            wo_id = await work_order_repositories.get_wo_id_from_schedule_id(db, schedule_info.id)
            if wo_id:
                await work_order_repositories.log_work_order_assignee_time(db, wo_id, current_member.id)
 
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Installation Prep Status Updated successfully."
                },
            )

    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")



async def get_schedule_installation_mappings(db: Session, doc_id: str):
    """
    Fetch all schedule installation mappings for a given installation plan document.

    This function retrieves all `ScheduleInstallationMapping` records linked to the specified
    `doc_id` (installation plan document ID), and returns them as a JSON response. Each record 
    includes its details, such as coordinate data, status, preparation data, and comments.

    Args:
        db (Session): SQLAlchemy database session.
        doc_id (str): The ID of the installation plan document whose mappings are to be fetched.

    Returns:
        JSONResponse: A 200 response with a list of mapping records and a success message.

    Raises:
        HTTPException: Returns a 500 error if the data retrieval operation fails.
    """
    try:
        mappings = await schedule_installation_repositories.get_schedule_installation_mappings(db, doc_id)
        results = []
        colour_mapping = {
            "PENDING": "ORANGE",
            "IN_PROGRESS": "BLUE",
            "FAILED": "RED",
            "SUCCESS": "GREEN",
        }
        for mapping in mappings:
            data = mapping.to_dict
            # Add comment count
            data["comment_count"] = len(mapping.schedule_installation_comments)
            data.pop("comments", None)
            data.pop("prep_data", None)
            data["colour_code"] = colour_mapping[data["status"]]
            results.append(data)

        return JSONResponse(
            status_code=200,
            content={
                "data": results,
                "message": "Data fetched successfully."
            },
        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")




async def remove_floor_plan(db: Session, doc_id: str):
    """
    Checks whether any markers (schedule installation mappings) exist for a given installation document.
    If none exist, deletes the associated document from the database and S3 storage.

    Args:
        db (Session): SQLAlchemy database session.
        doc_id (str): The ID of the installation plan document.

    Returns:
        JSONResponse: 200 if the document was removed, 400 if markers exist, or 500 on error.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            mappings = await schedule_installation_repositories.get_schedule_installation_mappings(db, doc_id)

            if len(mappings) == 0:
                # Fetch the document from DB
                doc = db.query(ProjectInstallationPlanDocs).filter(ProjectInstallationPlanDocs.id == doc_id).first()

                if doc:
                    # Attempt to delete from S3
                    try:
                        await delete_from_s3(doc.file_path)
                    except Exception as s3_error:
                        logger.warning(f"Warning: Failed to delete from S3: {str(s3_error)}")

                    # Delete the document record from DB
                    db.delete(doc)

                    return JSONResponse(
                        status_code=200,
                        content={"message": "Installation plan document removed successfully."}
                    )
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"message": "Document not found."}
                    )

            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "This plan cannot be removed as there are markers existing in the doc. Please remove the markers to remove this doc."
                    }
                )

    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")



async def get_schedule_installation_mapping_activities(
        db: Session, 
        schedule_installation_mapping_id: str, 
        page: Optional[int] = None, 
        page_size: Optional[int] = None
):
    try:
        schedule_installation_activity_responses, page_count, total_activities = await schedule_installation_repositories.schedule_installation_mapping_activities_data(db, schedule_installation_mapping_id, page, page_size)
        if len(schedule_installation_activity_responses)==0:
            return JSONResponse(
                            status_code=200,
                            content={
                                "message": "Activities Not Found.",
                                "data":[],
                                "page_count":0,
                                "item_count":0
                            },
                        )
        return JSONResponse(
            status_code=200,
            content={
                "data": schedule_installation_activity_responses,
                "page_count":page_count,
                "item_count": total_activities,
                "message": "Data fetched successfully."
            },
        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")




async def delete_mapping_comment_attachment(db: Session, attachment_id: str, current_member):
    """
    Deletes a comment attachment from a schedule installation mapping.

    This function performs the following operations:
    1. Commits any active transaction to avoid nested transaction conflicts.
    2. Begins a new transaction to delete the specified attachment:
       - Retrieves the attachment record using the provided `attachment_id`.
       - Deletes the associated file from the S3 bucket.
       - Removes the attachment record from the database.
    3. Returns a success response upon successful deletion.

    Args:
        db (Session): SQLAlchemy database session used for querying and transactions.
        attachment_id (str): The unique identifier of the attachment to be deleted.
        current_member: The member making the delete request (used for logging, auditing, or permission validation if implemented).

    Returns:
        JSONResponse: A response indicating successful deletion of the attachment.

    Raises:
        HTTPException: If an exception occurs during the process, a 500 error is raised with the exception details.
    """
    try:
        
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            schedule_installation_mapping_id = None
            schedule_installation_mapping_attachment_data = db.query(ScheduleInstallationMappingAttachment).get(attachment_id)
            schedule_installation_mapping_id = schedule_installation_mapping_attachment_data.schedule_installation_mapping_id
            await delete_from_s3(schedule_installation_mapping_attachment_data.file_path)
                
            db.query(ScheduleInstallationMappingAttachment).filter(ScheduleInstallationMappingAttachment.id==attachment_id).delete()
            if schedule_installation_mapping_id:
                schedule_installation_mapping = db.query(ScheduleInstallationMapping).filter(ScheduleInstallationMapping.id==schedule_installation_mapping_id).first()
                if schedule_installation_mapping:
                    wo_id = await work_order_repositories.get_wo_id_from_schedule_id(db, schedule_installation_mapping.schedule_id)
                    if wo_id:
                        await work_order_repositories.log_work_order_assignee_time(db, wo_id, current_member.id)
            return JSONResponse(
                            status_code=200,
                            content={
                                "message": "Mapping Comment Attachment Deleted successfully."
                            },
                        )
    except Exception as error:
        logger.exception(str(error))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(error)}")

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
from repositories import work_order_repositories


from typing import Optional




async def create_work_order(db: Session, current_member, data: dict):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            wo_id, message = await work_order_repositories.create_work_order(
                db=db,
                data=data,
                created_by=current_member.id
            )
            if not wo_id:
                db.rollback()
                return JSONResponse(status_code=400, content={"message":message,"status":"failed"})

            return JSONResponse(
                status_code=201,
                content={
                    "work_order_id": wo_id,
                    "message": message
                }
            )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error creating work order: {str(e)}")



async def update_work_order(db: Session, current_member, work_order_id: str, data: dict):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            wo,message = await work_order_repositories.update_work_order(
                db=db,
                work_order_id=work_order_id,
                data=data,
                updated_by=current_member.id
            )

            if not wo:
                db.rollback()
                return JSONResponse(status_code=400, content={"message":message,"status":"failed"})

            return JSONResponse(
                status_code=200,
                content={"work_order_id":wo.id,"message": "Work order updated successfully.","status":"success"}
            )
    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error updating work order: {str(e)}")


async def get_work_order(db: Session, work_order_id: str):
    try:
        work_order = await work_order_repositories.get_work_order_by_id(db=db, work_order_id=work_order_id)

        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found.")

        return JSONResponse(
            status_code=200,
            content={
                "data": work_order,
                "status":"success"
            }
        )
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch work order: {str(e)}")



async def list_work_orders(db: Session,project_id:str,is_completed:bool,page: int, page_size: int, keyword: str):
    try:
        result_data,page_count,total_items = await work_order_repositories.get_all_work_orders(db,project_id,is_completed,page, page_size,keyword)


        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": result_data,
                "page_count": page_count,
                "item_count": total_items,
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list work orders: {str(e)}")


async def get_all_work_orders(db: Session,statuses:str,page: int, page_size: int, keyword: str,current_member):
    try:
        result_data,page_count,total_items = await work_order_repositories.list_all_work_orders(db,statuses,page, page_size,keyword,current_member)


        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": result_data,
                "page_count": page_count,
                "item_count": total_items,
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list work orders: {str(e)}")


async def delete_work_order(db: Session, work_order_id: str):
    try:
        deleted_wo, message = await work_order_repositories.delete_work_order_by_id(db=db, work_order_id=work_order_id)

        if not deleted_wo:
            return JSONResponse(status_code=400, content={"message":message,"status":"failed"})

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Work order {work_order_id} deleted successfully."
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete work order: {str(e)}")



async def start_or_end_installation(
    db: Session,
    work_order_id: str,
    member_id: str,
    has_started: bool,
    location_details: dict

):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            await work_order_repositories.start_or_end_installation(
                db=db,
                work_order_id=work_order_id,
                member_id=member_id,
                has_started=has_started,
                location_details=location_details
            )
            return JSONResponse(
                status_code=201,
                content={
                    "message": "Installation work has been started." if has_started else "Installation work has been ended."
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




async def get_assignee_logs(db, work_order_id: str, assignee_id: str = None):
    try:
        log_data =  await work_order_repositories.get_assignee_logs(
            db=db,
            work_order_id=work_order_id,
            assignee_id=assignee_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": log_data
            }
        )
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get assignee logs: {str(e)}")


async def get_all_assignee_logs(db, work_order_id: str,):
    try:
        log_data =  await work_order_repositories.get_all_assignee_logs(
            db=db,
            work_order_id=work_order_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": log_data
            }
        )
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get assignee logs: {str(e)}")


def update_assignee_time_log(db: Session, log_id: str, started_at: str, ended_at: str, current_member):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():

            log, message= work_order_repositories.update_time_log(db, log_id, started_at, ended_at,current_member)

            if not log:
                return JSONResponse(status_code=400, content={"message":message,"status":"failed"})

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "log_id": log.id,
                    "message": message
                }
            )

    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error updating work order: {str(e)}")


def add_assignee_time_log(db: Session, wo_id: str, started_at: str, ended_at: str, member_id, current_member):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():

            log, message= work_order_repositories.add_time_log(db, wo_id, started_at, ended_at, member_id, current_member)

            if not log:
                return JSONResponse(status_code=400, content={"message":message,"status":"failed"})

            return JSONResponse(
                status_code=201,
                content={
                    "status": "success",
                    "log_id": log.id,
                    "message": message
                }
            )

    except Exception as e:
        db.rollback()
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Error creating time log: {str(e)}")


def delete_assignee_time_log(db: Session, log_id: str, current_member):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            log, message = work_order_repositories.delete_time_log(db, log_id, current_member)

            if not log:
                return JSONResponse(status_code=400, content={"message": message, "status": "failed"})

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "log_id": log_id,
                    "message": message
                }
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


async def get_next_possible_work_order_number(db: Session):
    try:
        work_order_number = await work_order_repositories.get_next_possible_work_order_number(db=db)

        return JSONResponse(
            status_code=200,
            content={
                "data": work_order_number,
                "status":"success"
            }
        )
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to next possible work order number: {str(e)}")








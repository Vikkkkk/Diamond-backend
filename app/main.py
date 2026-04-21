"""
This Module is responsible for running
the python fast api application server
default port:: taken from the environment, if not there then it will default to port 8080
"""
import os
from fastapi import FastAPI, Request
from fastapi import status as fast_api_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
# from models import get_db
from router import initiate_routes
from utils.logger import setup_logger
from loguru import logger
from models import Base, engine
from models.seeder import Seeder
from fastapi.staticfiles import StaticFiles
load_dotenv()
from models import clients, members, modules, projects, status, roles, role_permissions, \
raw_materials, door_frame_raw_material_sections, \
material_description, \
sub_modules, tender_documents, project_members, project_status_logs, \
project_take_of_sheet_notes, project_take_off_sheet_charges, project_raw_material_manufacturer_quotes, quotation_revision, \
task_status, project_task, task_members, task_comments, task_attachments, task_activity
import uvicorn
import sys
# from middleware.user_auth_middleware import authenticate_user
from cron.jobs import scheduler
from setuptools._distutils.util import strtobool
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event: Run the scheduler and setup database
    scheduler.start()
    logger.info("Scheduler started.")

    # Base.metadata.create_all(bind=engine)
    # logger.info("database is set...")
    perform_seeding()

    yield
    # Shutdown event: Clean up resources
    scheduler.shutdown()
    logger.info("Application shutdown. Cleaning up resources.")

# Initiate the FastAPI
app = FastAPI(
    debug=True,
    title=os.getenv("PROJECT_NAME"),
    version=os.getenv("PROJECT_VERSION"),
    root_path=os.getenv("PROJECT_ROOT_PATH"),
    lifespan=lifespan  # Attach lifespan event handler here
)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR")
if os.path.exists(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

else:
    os.makedirs(UPLOAD_DIR, exist_ok = True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Configure CORS
origins = [
    "http://diamond-architecture-ui.s3-website.ca-central-1.amazonaws.com",
    "http://localhost",
    "http://localhost:3001",  # Add the domains you want to allow
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup the loguru logger
setup_logger()
# app.middleware("http")(authenticate_user)



def perform_seeding():
    """
    Performs seeding operations based on the SEEDING environment variable.

    If SEEDING is set to True, this function initializes a Seeder object and starts the seeding process.
    It logs information messages before and after seeding to indicate the start and completion of the process.

    """
    try:
        if strtobool(os.environ.get("SEEDING")):
            logger.info("Starting seed...")
            seeder_obj = Seeder()
            seeder_obj.start_seeding()
            logger.info("Seeding done...")
        else:
            logger.info("Skipping seeding...")
    except Exception as e:
        logger.exception(f"perform_seeding:: error - {str(e)}")


# Custom error handlers
@app.exception_handler(RequestValidationError)
@logger.catch
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """**Summary:**
    This method is responsible for validating all input data from all API requests.
    """
    try:
        # Get the original 'details' list of errors
        details = exc.errors()
        # Add the errors in the message field
        error_list = []
        for error in details:
            err_msg = error["msg"]
            if "loc" in error:
                locs = "->".join(str(item) for item in list(error["loc"]))
                err_msg += " at " + locs
            error_list.append(err_msg)
        error_list = sorted(list(set(error_list)))
        error_message = ",".join(elm for elm in error_list)
        return JSONResponse(
            status_code=fast_api_status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"message": error_message, "debug": details}),
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@app.exception_handler(ValidationError)
@logger.catch
async def validation_exception_handler(request: Request, exc: ValidationError):
    """**Summary:**
    This method is responsible for validating all response data from all API response.
    """
    try:
        # Get the original 'details' list of errors
        details = exc.errors()
        # Add the errors in the message field
        error_list = []
        for error in details:
            err_msg = error["msg"]
            if "loc" in error:
                locs = "->".join(str(item) for item in list(error["loc"]))
                err_msg += " at " + locs
            error_list.append(err_msg)
        error_list = sorted(list(set(error_list)))
        error_message = ",".join(elm for elm in error_list)
        return JSONResponse(
            status_code=fast_api_status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"message": error_message, "debug": details}),
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


initiate_routes.InitiateRouters(app)

if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        Seeder()
        logger.info("seeds are added...")
    
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT","8080")), reload=True)


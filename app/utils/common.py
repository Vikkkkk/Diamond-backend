"""
This module contains several commonly used utility functions
"""
from datetime import datetime, timezone, timedelta, date
import uuid
import random
import string
import re
from loguru import logger
import pytz
import os
from dotenv import load_dotenv
import shutil
from fastapi import UploadFile
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from typing import Literal, Optional
import asyncio
from difflib import SequenceMatcher

load_dotenv()
user_timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

# AWS Credentials (should have S3 permissions)
ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")


# Initialize the S3 client with credentials
s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


def extract_keywords(phrase):
    """**Summary:**
    Extract and return a list of keywords from the input phrase.

    **Args:**
        - phrase (String): input phrase to extract keywords from
    """
    try:
        cleaned_phrase = re.sub(r'[^\w\s]', '', phrase)  # Remove special characters
        keywords = [word.lower() for word in cleaned_phrase.split()]
        return keywords
    except Exception as error:
        logger.exception("extract_keywords:: error - " + str(error))
        raise error



def get_random_hex_code(length=4):
    """**Summary:**
    Generate and return a random HEX code of input length.

    **Args:**
        - length (String): length of the hex code to be generated
    """
    try:
        return ''.join(random.choices(string.hexdigits, k=length))
    except Exception as error:
        logger.exception("get_random_hex_code:: error - " + str(error))
        raise error


def generate_uuid():
    """**Summary:**
    Generate and return a UUID (Universally Unique Identifier).
    """
    try:
        return str(uuid.uuid4())
    except Exception as error:
        logger.exception("generate_uuid:: error - " + str(error))
        raise error


def generate_unique_filename(file_extension):
    """**Summary:**
    Generate and return a unique filename using UUID (Universally Unique Identifier).

    **Args:**
        - file_extension (String): file extenstion
    """
    try:
        return str(uuid.uuid4()) + file_extension
    except Exception as error:
        logger.exception("generate_unique_filename:: error - " + str(error))
        raise error


def get_utc_time(to_string=True):
    """**Summary:**
    Generate and return the current UTC datetime as a string.

    **Args:**
        - to_string (Boolean): if true then it will return datetime as string otherwise at dattime object
    """
    try:
        current_utc_time = datetime.now(timezone.utc)
        if to_string:
            formatted_utc_time = current_utc_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_utc_time = current_utc_time
        return formatted_utc_time
    except Exception as error:
        logger.exception("get_utc_time:: error - " + str(error))
        raise error

def convert_to_timezone(dt):
    """
    **Summary:**
    Ensures that a given datetime object is timezone-aware.

    **Args:**
    - `dt` (datetime): A naive or timezone-aware datetime object.

    **Returns:**
    - `datetime`: A timezone-aware datetime object. If the input `dt` was naive, the 
      returned datetime will be localized to UTC. If the input `dt` was already 
      timezone-aware, it is returned as-is.

    **Example:**
    ```python
    naive_dt = datetime(2024, 9, 24, 12, 0, 0)  # Naive datetime
    aware_dt = convert_to_timezone(naive_dt)  # Converts to UTC aware datetime

    aware_dt_already = datetime(2024, 9, 24, 12, 0, 0, tzinfo=pytz.UTC)
    result = convert_to_timezone(aware_dt_already)  # Returns the same datetime
    ```
    """
    try:
        if dt and dt.tzinfo is None:
            return pytz.UTC.localize(dt)
        return dt
    except Exception as error:
        logger.exception("get_user_time:: error - " + str(error))
        raise error


def get_user_time(to_string=True):
    """**Summary:**
    Generate and return the current User datetime as a string.

    **Args:**
        - to_string (Boolean): if true then it will return datetime as string otherwise at dattime object
    """
    try:
        current_user_time = datetime.now(user_timezone)
        if to_string:
            formatted_user_time = current_user_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_user_time = current_user_time
        return formatted_user_time
    except Exception as error:
        logger.exception("get_user_time:: error - " + str(error))
        raise error
    

def delete_file(file_path):
    """Delete a file from the file path directory."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True  # File deletion successful
        else:
            return False  # File does not exist
    except Exception as e:
        logger.exception(f"An error occurred while deleting the file: {e}")
        return False  # File deletion failed


async def save_uploaded_file(files):
    """**Summary:**
    This method is responsible for uploading documents for a project.

    Args:
        db (Session): db session referance
        project_id (str): Project Id, which will add along with the file data into the database
        file (file): File, selected and uploaded in to the system for a specific project
    """
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR")
    try:
        os.makedirs(UPLOAD_DIR, exist_ok = True)
        file_paths = []
        for file in files:
            filename = file.filename
            # Generate a unique filename based on the original filename and extension
            file_extension = os.path.splitext(filename)[-1]

            unique_filename = generate_unique_filename(file_extension)
            file_path = os.path.join(UPLOAD_DIR, unique_filename).replace("\\", "/")

            with open(file_path, "wb") as out_file:
                shutil.copyfileobj(file.file, out_file)
            file_paths.append((file_path,filename))
        return file_paths
    except Exception as e:
        # Handle exceptions appropriately
        logger.exception(f"save_uploaded_file:: error occurred: {e}")
        raise e
    
async def format_project_code(project_code = None):
    count = 0
    if project_code:
        count = int(''.join(char for char in project_code if char.isdigit()))

    return f'DIA_{count + 1:04d}'




def save_file(task_id: str, upload_file: UploadFile) -> str:
    """
    Save the uploaded file to the appropriate directory based on task_id.

    Args:
        task_id (str): The task ID for which the file is being uploaded.
        upload_file (UploadFile): The file to be uploaded.

    Returns:
        str: The path where the file is saved.
    """
    UPLOAD_DIRECTORY = os.environ.get("UPLOAD_ATTACH_DIR")
    os.makedirs(UPLOAD_DIRECTORY, exist_ok = True)
    task_dir = os.path.join(UPLOAD_DIRECTORY, task_id)

    os.makedirs(task_dir, exist_ok=True)

    file_path = os.path.join(task_dir, upload_file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())

    return file_path.replace("\\", "/")


async def upload_to_s3(file, upload_path, bucket_name = None):
    """Uploads a file to an S3 bucket.

    Args:
        file (UploadFile): The file to upload.
        upload_path (str): The S3 path where the file should be uploaded.
        bucket_name (Optional[str]): The S3 bucket name. Defaults to `BUCKET_NAME`.

    Returns:
        Optional[str]: The URL of the uploaded file, or `None` if upload failed.
    """
    bucket_name = bucket_name or BUCKET_NAME 
    try:
        file_key = f"{upload_path}/{file.filename}"
        # Reset cursor to the beginning of the file
        file.file.seek(0)
        
        await asyncio.to_thread(
            s3_client.upload_fileobj,
            file.file,  # The file object
            bucket_name,  # The bucket to upload to
            file_key,  # The key under which the file is saved
            ExtraArgs={
                "ACL": "public-read",  # Make the file publicly accessible
                "ContentType": file.content_type  # Set the correct MIME type
            }
        )
        return file_key
    
    except NoCredentialsError:
        print("Credentials not available.")
    except ClientError as e:
        print(f"Failed to upload {file_key}: {e}")


async def upload_path_to_s3(file_path, upload_path, bucket_name = None):
    """Uploads a file to an S3 bucket.

    Args:
        file_path : The path of the file to upload.
        upload_path (str): The S3 path where the file should be uploaded.
        bucket_name (Optional[str]): The S3 bucket name. Defaults to `BUCKET_NAME`.

    Returns:
        Optional[str]: The URL of the uploaded file, or `None` if upload failed.
    """
    bucket_name = bucket_name or BUCKET_NAME 
    try:
        # Extract the filename from the file_path
        file_name = os.path.basename(file_path)
        file_key = f"{upload_path}/{file_name}"

        with open(file_path, "rb") as file:
            await asyncio.to_thread(
                s3_client.upload_fileobj,
                file,  # File object opened in binary mode
                bucket_name,
                file_key,
                ExtraArgs={
                    "ACL": "public-read",  # Make the file publicly accessible
                    "ContentType": "application/pdf"  # Explicitly set ContentType
                }
            )
        
        return file_key
    
    except NoCredentialsError:
        print("Credentials not available.")
    except ClientError as e:
        print(f"Failed to upload {file_key}: {e}")


def download_from_s3(file_key: str, bucket_name: str = None):
    """
    Downloads a file from S3 and returns its content, content type, filename, and content length.

    Args:
    - file_key (str): The key of the file to download in the S3 bucket.
    - bucket_name (Optional[str]): The name of the S3 bucket. If None, defaults to `BUCKET_NAME`.

    Returns:
    - Tuple[bytes, str, str, int]: A tuple containing the file's content (stream), content type, filename, and content length.

    Raises:
    - HTTPException: Raises an HTTP exception with status code 404 if the file is not found.
    - HTTPException: Raises an HTTP exception with status code 500 for other client errors.
    """

    # Use the provided bucket name or the default one
    bucket_name = bucket_name or BUCKET_NAME
    try:
        logger.info(f"Attempting to download file '{file_key}' from bucket '{bucket_name}'")
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        
        # Extract relevant information from the S3 response
        file_content = s3_object['Body']  # File stream
        content_type = s3_object.get('ContentType', 'application/octet-stream')  # Fallback to a generic content type
        content_length = s3_object.get('ContentLength', 0)  # Default to 0 if not provided
        filename = file_key.split("/")[-1]  # Extract the filename from the file key
        
        logger.info(f"Successfully downloaded file '{file_key}' with content type '{content_type}' and length {content_length} bytes.")
        
        return file_content, content_type, filename
    
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", "")
        
        # Check if the error is due to a missing file
        if error_code == 'NoSuchKey':
            logger.error(f"File '{file_key}' not found in S3 bucket '{bucket_name}'. Error: {error_message}")
            raise HTTPException(status_code=404, detail=f"File '{file_key}' not found in S3 bucket '{bucket_name}'")
        
        # Log unexpected client errors
        logger.error(f"Unexpected error while downloading file '{file_key}' from S3. Error: {error_message}")
        raise HTTPException(status_code=500, detail=f"Error retrieving file from S3: {error_message}")


async def delete_from_s3(file_key: str, bucket_name: str = None):
    """
    Delete a file from S3.

    Args:
        file_key (str): The S3 key of the file to delete.
        bucket_name (str, optional): The S3 bucket name. Defaults to `BUCKET_NAME`.

    Raises:
        HTTPException: If the file does not exist or there's a server error.

    Returns:
        dict: A dictionary containing the response metadata or an error message.
    """
    bucket_name = bucket_name or BUCKET_NAME
    
    try:
        # Delete the file from S3
        response = s3_client.delete_object(Bucket=bucket_name, Key=file_key)

        # Check if the delete operation was successful
        if response['ResponseMetadata']['HTTPStatusCode'] == 204:
            # 204 No Content: Successful deletion
            logger.info(f"File {file_key} successfully deleted from {bucket_name}.")
        else:
            # If the status code is not 204, something went wrong
            logger.error(f"Failed to delete {file_key} from {bucket_name}: {response}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to delete {file_key} from {bucket_name}."
            )

    except ClientError as e:
        # Handle specific S3 errors
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"File {file_key} not found in {bucket_name}.")
            raise HTTPException(status_code=404, detail="File not found in S3")
        else:
            # Log and raise generic client errors
            logger.error(f"Error deleting {file_key} from {bucket_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    



def check_task_completion_status(start_date, due_date, completed_date=None):
    current_date = datetime.now()

    # Ensure due_date and start_date are valid
    if not start_date.date() or not due_date.date():
        raise ValueError("Start date and due date must be provided")

    if completed_date:
        # Task is completed
        if completed_date.date() > due_date.date():
            return {"pastdue": True, "is_near_due_date": False}
        else:
            return {"pastdue": False, "is_near_due_date": False}
    else:
        # Task is not completed
        if current_date > due_date:
            # Task is overdue and not completed
            return {"pastdue": True, "is_near_due_date": False}
        else:
            # Calculate the difference between due date and current date
            days_until_due = (due_date.date() - current_date.date()).days
            if days_until_due > 7:
                return {"pastdue": False, "is_near_due_date": False}
            else:
                return {"pastdue": False, "is_near_due_date": True}


def get_aws_full_path(file_path: str):
    BUCKET_NAME = os.environ.get("BUCKET_NAME")
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_path}"




async def find_best_match_dict(target_strings, dict_list, key):
    try:
        # # Calculate similarity scores for each dictionary
        # similarity_scores = [
        #     (d, SequenceMatcher(None, target_strings[0], d[key]).ratio())
        #     for d in dict_list if key in d
        # ]
        # print("similarity_scores:: ",similarity_scores)
        # # # Find the dictionary with the highest similarity score
        # best_match = max(similarity_scores, key=lambda x: x[1], default=(None, 0))
        
        # # Return the best match only if the similarity score is above a threshold
        # return best_match[0] if best_match[1] > 0.6 else None

        # Calculate cumulative similarity scores for each dictionary
        similarity_scores = []
        for d in dict_list:
            if key in d:
                # Calculate a cumulative score based on substring matches
                total_score = sum(
                    1.0 if target.lower() in d[key].lower() else 0.5 * SequenceMatcher(None, target.lower(), d[key].lower()).ratio()
                    for target in target_strings
                )
                # total_score = sum(
                #     SequenceMatcher(None, target, d[key]).ratio()
                #     for target in target_strings
                # )
                similarity_scores.append((d, total_score))
        
        # Find the dictionary with the highest cumulative similarity score
        best_match = max(similarity_scores, key=lambda x: x[1], default=(None, 0))
        
        # Return the dictionary with the highest score
        return best_match[0] if best_match[1] > 0.6 else None
    except Exception as e:
        # Handle exceptions appropriately
        logger.exception(f"find_best_match_dict:: error occurred: {e}")
        return None
    

def get_estimated_delivery_date(days: int) -> str:
    """Returns a future date after adding the given day interval."""
    future_date = datetime.now() + timedelta(days=days)
    return future_date.strftime("%Y-%m-%d")


def get_order_by_date(required_by_date: date, days: int) -> str:
    """Returns a future date after adding the given day interval."""
    required_by_date = datetime.strptime(required_by_date, "%Y-%m-%d").date()  # Convert string to date
    order_by_date = required_by_date - timedelta(days=days)
    return order_by_date.strftime("%Y-%m-%d") 


def get_max_date(dates: list) -> str:
    """Returns the maximum (latest) date from a list of date strings."""
    if not dates:
        return None  # Handle empty list case

    return max(dates, key=lambda date: datetime.strptime(date, "%Y-%m-%d"))


async def get_exact_breakup_amount(amount, decimal_value, value_type: Literal["PERCENTAGE", "MULTIPLIER"] = "PERCENTAGE"):
    try:
        if decimal_value is None:
            decimal_value = 0
        if value_type == "PERCENTAGE":
            return amount * decimal_value
        elif value_type == "MULTIPLIER":
            return amount * (1 - decimal_value)
        else:
            return 0
    except Exception as e:
        # Handle exceptions appropriately
        logger.exception(f"get_exact_breakup_amount:: error occurred: {e}")
        return None
    


async def set_all_priceing_breakdown(component_items: dict):
    try:
        for component, items in component_items.items():
            for item_code, item in items.items():
                if all (k in item for k in ("discount", "discount_type", "markup", "surcharge_type", "surcharge", "total_amount", "quantity")):
                    price_breakdown = await get_all_pricing_breakdown(
                        discount=item.get('discount', 0),
                        discount_type=item.get('discount_type', 'FLAT'),
                        markup=item.get('markup', 0),
                        surcharge_type=item.get('surcharge_type', 'FLAT'),
                        surcharge=item.get('surcharge', 0),
                        total_amount=item.get('total_amount', 0),
                        quantity=item.get('quantity', 1)
                    )
                    component_items[component][item_code] = {**item, **price_breakdown}
        return component_items
    except Exception as e:
        # Handle exceptions appropriately
        logger.exception(f"set_all_priceing_breakdown:: error occurred: {e}")
        return component_items
    

async def get_all_pricing_breakdown(discount, discount_type, markup, surcharge_type, surcharge, total_amount, quantity):
    """**Summary:**
    Calculate and return a detailed pricing breakdown based on various financial parameters.
    Args:
        - discount (float): The discount value to be applied.
        - discount_type (str): The type of discount ("FLAT", "PERCENTAGE", "MULTIPLIER").
        - markup (float): The markup percentage to be applied.
        - surcharge_type (str): The type of surcharge ("FLAT", "PERCENTAGE", "MULTIPLIER").
        - surcharge (float): The surcharge value to be applied.
        - total_amount (float): The base list price before any adjustments.
        - quantity (int): The quantity of items being priced.
    Returns:
        - dict: A dictionary containing the detailed pricing breakdown.
    """
    try:
        discount_type = discount_type.value if hasattr(discount_type, 'value') else discount_type
        # Calculate discounted amount
        if discount_type and discount_type == "FLAT":
            discounted_amount = discount if discount else 0

        elif discount_type and discount_type == "PERCENTAGE":
            discounted_amount = ((total_amount * discount)) if discount else 0
        elif discount_type and discount_type == "MULTIPLIER":
            discounted_amount = (total_amount * (1 - discount)) if discount else 0
        else:
            discounted_amount = 0  # Default or fallback if no valid discount_type
        # Calculate base amount (total_amount - discount amount)
        total_base_amount = total_amount - discounted_amount
        # Calculate Markup amount
        markup_amount = (total_base_amount * markup) if markup else 0

        # Calculate sell amount
        total_sell_amount = total_base_amount + markup_amount
    
        surcharge_type = surcharge_type.value if hasattr(surcharge_type, 'value') else surcharge_type

        # Calculate surcharge amount
        if surcharge_type and surcharge_type == "FLAT":
            surcharge_amount = surcharge if surcharge else 0
        elif surcharge_type and surcharge_type == "PERCENTAGE":
            surcharge_amount = (total_sell_amount * surcharge) if surcharge else 0
        elif surcharge_type and surcharge_type == "MULTIPLIER":
            surcharge_amount = (total_sell_amount * (1 - surcharge)) if surcharge else 0
        else:
            surcharge_amount = 0  # Default or fallback if no valid surcharge_type

        # Calculate extended sell amount
        total_extended_sell_amount = total_sell_amount + surcharge_amount

        price_breakdown = {
            "total_amount": round(total_amount, 3),
            "total_base_amount": round(total_base_amount, 3),
            "total_sell_amount": round(total_sell_amount, 3),
            "total_extended_sell_amount": round(total_extended_sell_amount, 3),
            "final_amount": round(total_amount * quantity, 3),
            "final_base_amount": round(total_base_amount * quantity, 3),
            "final_sell_amount": round(total_sell_amount * quantity, 3),
            "final_extended_sell_amount": round(total_extended_sell_amount * quantity, 3)
        }
        return price_breakdown
    except Exception as error:
        logger.exception("get_all_pricing_breakdown:: error - " + str(error))
        return {
            "total_amount": 0,
            "total_base_amount": 0,
            "total_sell_amount": 0,
            "total_extended_sell_amount": 0,
            "final_amount": 0,
            "final_base_amount": 0,
            "final_sell_amount": 0,
            "final_extended_sell_amount": 0
        }

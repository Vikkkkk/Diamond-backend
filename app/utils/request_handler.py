"""
This module contains several commonly used utility functions
"""
import asyncio
from fastapi import HTTPException
from datetime import timezone
from typing import Dict
from loguru import logger
from dotenv import load_dotenv
import os
import httpx

load_dotenv()
pricebook_url = os.getenv("PRICEBOOK_URL")


async def call_post_api(end_point: str, json_data: Dict = {}, params_data: Dict = {}):
    """**summary**
    This module is generic module for calling an external api with POST method

    **Args:**
        end_point (str): This will be the api end point to be called
        json_data (Dict): This is the json body data (if required)
        params_data (Dict): This is the params data (if required)
    """
    try:
        url = pricebook_url + "/" + end_point
        print("url", url)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params= params_data, json=json_data, timeout=60.0)
            response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 404, 500)
            return {"status_code": response.status_code, "response": response.json()}
    except httpx.RequestError as e:
        return {"status_code": 500, "response": f"Request error: {str(e)}"}
        # raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
    except httpx.HTTPStatusError as e:
        return {"status_code": e.response.status_code, "response": f"Request error: {str(e)}"}
        # raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")



async def call_get_api(end_point: str, params_data: Dict = {}):
    """**summary**
    This module is generic module for calling an external api with GET method

    **Args:**
        end_point (str): This will be the api end point to be called
        params_data (Dict): This is the params data (if required)
    """
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            url = pricebook_url + "/" + end_point
            print("url:: ", url)
            # print("params_data:: ", params_data)
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params= params_data, timeout=30.0)
                response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 404, 500)
                return {"status_code": response.status_code, "response": response.json()}
        except httpx.ReadTimeout as e:
            logger.info(f"Timeout error: {e}")
            retry_count += 1
            logger.info("Retry attempt:: " + str(retry_count))
            await asyncio.sleep(5) # Add 5 sec delay before the retry
        except httpx.RequestError as e:
            return {"status_code": 500, "response": f"Request error: {str(e)}"}
            # raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
        except httpx.HTTPStatusError as e:
            return {"status_code": e.response.status_code, "response": f"Request error: {str(e)}"}
            # raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    # If all retries fail, raise an exception
    raise HTTPException(status_code=500, detail="Maximum retry attempts reached.")


# async def send_transfer_opening_request(project_id: str, token: str):
#     url = f"http://localhost:8000/{project_id}/transfer-opening"
    
#     headers = {
#         "Authorization": f"Bearer {token}",  # if your `get_current_member` uses JWT auth
#         "Content-Type": "application/json"
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.post(url, headers=headers)

#     if response.status_code != 201:
#         raise Exception(f"Transfer failed: {response.text}")
    
#     return response.json()

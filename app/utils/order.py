"""
This module contains several commonly used utility functions
"""
from datetime import timezone
import uuid
import datetime
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
from typing import Optional
import asyncio
from difflib import SequenceMatcher
from collections import defaultdict


def get_part_waise_door_filtered_data(data):
    key_patterns = {
        "height": re.compile(r"(nominal|rebate)?[\s_]?height|^height$", re.IGNORECASE),
        "width": re.compile(r"(nominal|rebate)?[\s_]?width|^width$", re.IGNORECASE),
        "gauge": re.compile(r"gauge", re.IGNORECASE),
        "door_catalog": re.compile(r"^door_catalog$", re.IGNORECASE)
    }
    
    grouped_data = defaultdict(dict)
    
    for item in data:
        part_number = item.get("part_number")
        name = item.get("name", "")
        value = item.get("value", "")
        
        for key, pattern in key_patterns.items():
            if pattern.search(name):
                grouped_data[part_number][key] = value
    
    return dict(grouped_data)


def get_door_filtered_data(data):
    key_patterns = {
        "height": re.compile(r"(nominal|rebate)?[\s_]?height|^height$", re.IGNORECASE),
        "width": re.compile(r"(nominal|rebate)?[\s_]?width|^width$", re.IGNORECASE),
        "gauge": re.compile(r"gauge", re.IGNORECASE),
        "door_catalog": re.compile(r"door_catalog", re.IGNORECASE),
    }

    # Extract matching data
    filtered_data = [
        item for item in data if any(pattern.search(item["name"]) for pattern in key_patterns.values())
    ]

    # Transform data into key-value pairs
    transformed_data = {
        key: item["value"]
        for item in filtered_data
        for key, pattern in key_patterns.items()
        if pattern.search(item["name"])
    }
    return transformed_data



def get_frame_filtered_data(data):
    key_patterns = {
    "height": re.compile(r"(nominal|rebate)?[\s_]?height|^height$", re.IGNORECASE),
    "width": re.compile(r"(nominal|rebate)?[\s_]?width|^width$", re.IGNORECASE),
    "jamb_depth": re.compile(r"jamb[\s_]?depth", re.IGNORECASE),
    "frame_catalog": re.compile(r"frame_catalog", re.IGNORECASE),
    }

    # Extract matching data
    filtered_data = [
        item for item in data if any(pattern.search(item["name"]) for pattern in key_patterns.values())
    ]

    # Transform data into key-value pairs
    transformed_data = {
        key: item["value"]
        for item in filtered_data
        for key, pattern in key_patterns.items()
        if pattern.search(item["name"])
    }
    return transformed_data



def split_by_schedule_and_catalog(data):
    result = []
    grouped_entries = defaultdict(lambda: {"schedule_data": []})

    for entry in data:
        base_data = entry.copy()
        schedule_data = base_data.pop("schedule_data")  # Extract schedule_data
        
        for key, details in schedule_data.items():
            schedule_id = base_data["schedule_id"]
            # door_catalog = details["door_catalog"]

            # Unique key using schedule_id and door_catalog
            # unique_key = (schedule_id, door_catalog)
            unique_key = (schedule_id)

            if unique_key not in grouped_entries:
                grouped_entries[unique_key] = base_data.copy()
                grouped_entries[unique_key]["schedule_data"] = []

            # Convert schedule_data into a list with "part_number"
            details["part_number"] = int(key)  # Convert key to integer for part_number
            grouped_entries[unique_key]["schedule_data"].append(details)

    result = list(grouped_entries.values())
    return result



def extract_price_data(entries):
    price_dict = {}
    for item in entries:
        # Handle the base price for entries with is_adon_field == 0
        if item["is_adon_field"] == 0 and "base_price" not in price_dict and item["feature_data"] is not None:
            price_dict["base_price"] = item["amount"]
        
        # Handle adon prices for entries with is_adon_field == 1
        elif item["is_adon_field"] == 1:
            if "adon_price" not in price_dict:
                price_dict["adon_price"] = item["amount"]
            else:
                price_dict["adon_price"] += item["amount"]

    return price_dict

# Function to generate PO Number
def generate_po_number():
    return f"PO-{uuid.uuid4().hex[:8].upper()}"
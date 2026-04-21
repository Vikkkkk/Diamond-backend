

from models.opening_hardware_materials import OpeningHardwareMaterials
from utils.common import set_all_priceing_breakdown
from schemas.ordered_item_schema import COMPONENT_TYPE



async def build_schedule_hardware_dict(db, hardware_record_dict, schedule_id: str) -> dict:
    """Build dict for schedule_hardware_data with OpeningHardwareMaterials details."""

    new_version_dict = {}
    for ohm_id, qty in hardware_record_dict.items():
        print("ohm_id:: ", ohm_id, " qty:: ", qty)
        material = (
            db.query(OpeningHardwareMaterials)
            .filter(OpeningHardwareMaterials.id == ohm_id)
            .first()
        )
        if not material:
            continue
        # # Enriched payload
        print("material:: ", material.short_code)
        # print("type:: ", type(material))
        key = material.short_code
        hardware_data = {
            "id": str(material.id),
            "schedule_id": schedule_id,
            "quantity": qty,
            "short_code": material.short_code,
            "desc": material.desc,
            "feature_details": await get_hardware_feature_deatils({
                "base_feature": material.base_feature,
                "adon_feature": material.adon_feature,
                "quantity": material.quantity,
            }),
            "component": COMPONENT_TYPE.HARDWARE.value,
            "discount": material.discount,
            "discount_type": material.discount_type.value,
            "surcharge": material.surcharge,
            "surcharge_type": material.surcharge_type.value,
            "markup": material.markup,
            "margin": material.margin,
            "manufacturer_code": material.opening_hardware_manufacturer.code if material.opening_hardware_manufacturer else None,
            "opening_hardware_material_id": str(material.id),
            "total_amount": material.final_amount or 0,
            "total_sell_amount": material.final_sell_amount or 0,
            "total_base_amount": material.final_base_amount or 0,
            "total_extended_sell_amount": material.final_extended_sell_amount or 0,
            "final_amount": material.final_amount * qty,
            "final_sell_amount": material.final_sell_amount * qty,
            "final_base_amount": material.final_base_amount * qty,
            "final_extended_sell_amount": material.final_extended_sell_amount * qty,
            "hardware_material_data": material.to_dict,
        }
        new_version_dict[key] = hardware_data
    price_breakdown_enriched_data = await set_all_priceing_breakdown({"HARDWARE": new_version_dict})
    price_breakdown_enriched_data = price_breakdown_enriched_data["HARDWARE"]
    price_breakdown_enriched_data = await get_hardware_price_details(price_breakdown_enriched_data)

    # print("*********************************")
    # print("price_breakdown_enriched_data:: ", price_breakdown_enriched_data)
    # print("*********************************")
    return price_breakdown_enriched_data



async def get_hardware_feature_deatils(hardware_schedule_data: dict):
    try:
        quantity = hardware_schedule_data.get("quantity", 1)
        base_feature_data = hardware_schedule_data.get("base_feature", {})
        adon_feature_data = hardware_schedule_data.get("adon_feature", {})
        feature_details = {}
        for feature_key, feature_value in base_feature_data.items():
            base_feature = {}
            base_feature['name'] = feature_key
            base_feature['value'] = feature_value.get('optionCode', None)
            base_feature['is_adon_field'] = False
            base_feature['has_price_dependancy'] = True
            base_feature['quantity'] = quantity
            feature_details[feature_key] = base_feature
        if len(adon_feature_data) > 0:
            for adon_feature_key, adon_feature_value in adon_feature_data.items():
                adon_feature = {}
                feature_code = adon_feature_key
                optionCode = adon_feature_value.get('optionCode', None)
                adon_feature['name'] = feature_code
                adon_feature['value'] = optionCode
                adon_feature['is_adon_field'] = True
                adon_feature['has_price_dependancy'] = True
                adon_feature['quantity'] = quantity
                feature_details[feature_code] = adon_feature
        return feature_details
    except Exception as e:
        print(f"get_hardware_feature_deatils:: Error : {e}")
        feature_details = {}


async def get_hardware_price_details(hardware_schedule_data: dict):
    try:
        pricing_details = {}
        def safe_get(d, key):
            return float(d.get(key, 0) or 0)

        # --- Define calculated values first ---
        # Helper to calculate amounts for each key
        def calc_amounts(key):
            vals = [safe_get(v, key) for v in hardware_schedule_data.values()]
            return sum(vals)
            
        total_amount = calc_amounts("final_amount")
        total_sell_amount = calc_amounts("final_sell_amount")
        total_base_amount = calc_amounts("final_base_amount")
        total_extended_sell_amount = calc_amounts("final_extended_sell_amount")
        
        final_amount = total_amount 
        final_sell_amount = total_sell_amount
        final_base_amount = total_base_amount
        final_extended_sell_amount = total_extended_sell_amount

        pricing_details["fields"] = hardware_schedule_data
        pricing_details["price_details"] = {
            "total_amount": total_amount,
            "total_sell_amount": total_sell_amount,
            "total_base_amount": total_base_amount,
            "total_extended_sell_amount": total_extended_sell_amount,
            "final_amount": final_amount,
            "final_sell_amount": final_sell_amount,
            "final_base_amount": final_base_amount,
            "final_extended_sell_amount": final_extended_sell_amount
        }  
        return pricing_details
    except Exception as e:
        # Log the exception with a detailed error message
        print(f"get_hardware_price_details:: Error : {e}")
        raise e


async def compare_schedule_hardware_data(v0_schedule_hardware_data, current_schedule_hardware_data, project_id, schedule_id, opening_number):
    """
    Compares the take-off hardware data with the schedule hardware data for a given schedule,
    identifies differences, and delegates to `get_schedule_data_version_differences` for further processing.

    This function:
    - Retrieves the schedule from the database.
    - Extracts and structures the take-off hardware data.
    - Calls `prepare_hardware_data` to get the current hardware configuration.
    - Normalizes both datasets for comparison.
    - Passes the structured data to `get_schedule_data_version_differences` to find and record the differences.

    Args:
        db (Session): SQLAlchemy database session.
        current_member_id (User): The current user initiating the comparison, used for tracking changes.
        schedule_id (int): ID of the schedule to compare.

    Returns:
        Any: The result from the `get_schedule_data_version_differences` function, which typically records the differences 
        and may return a summary or confirmation of the changes applied.

    Raises:
        None explicitly, but may propagate exceptions from the database or `prepare_hardware_data`/`get_schedule_data_version_differences`.

    Notes:
        - This function assumes `initial_schedule_hardware_data` exists in the schedule.
        - Both take-off and schedule hardware data are normalized to a consistent format before comparison.
    """
    if not (v0_schedule_hardware_data and current_schedule_hardware_data):
        return {}
    # print("v0_schedule_hardware_data:: ", v0_schedule_hardware_data.keys())
    # print("current_schedule_hardware_data:: ", current_schedule_hardware_data.keys())
    v0_schedule_hardware_data_res = {}
    current_schedule_hardware_data_res = {}
    for key, v0_schedule_hardware_data_value in v0_schedule_hardware_data.items():
        short_code = key
        v0_schedule_hardware_data_res[short_code] = {
            'short_code': v0_schedule_hardware_data_value.get('short_code'),
            'feature_details': v0_schedule_hardware_data_value.get('feature_details', {}),
            'desc': v0_schedule_hardware_data_value.get('desc', ''),
            'markup': v0_schedule_hardware_data_value.get('markup', 0),
            'margin': v0_schedule_hardware_data_value.get('margin', 0),
            'discount_type': v0_schedule_hardware_data_value.get('discount_type', "PERCENTAGE"),
            'discount': v0_schedule_hardware_data_value.get('discount', 0),
            'surcharge_type': v0_schedule_hardware_data_value.get('surcharge_type', "PERCENTAGE"),
            'surcharge': v0_schedule_hardware_data_value.get('surcharge', 0),
            'quantity': v0_schedule_hardware_data_value.get('quantity', 0),
            "total_amount": v0_schedule_hardware_data_value.get("total_amount", 0),
            "total_sell_amount": v0_schedule_hardware_data_value.get("total_sell_amount", 0),
            "total_base_amount": v0_schedule_hardware_data_value.get("total_base_amount", 0),
            "total_extended_sell_amount": v0_schedule_hardware_data_value.get("total_extended_sell_amount", 0),
            "final_amount": v0_schedule_hardware_data_value.get("final_amount", 0),
            "final_sell_amount": v0_schedule_hardware_data_value.get("final_sell_amount", 0),
            "final_base_amount": v0_schedule_hardware_data_value.get("final_base_amount", 0),
            "final_extended_sell_amount": v0_schedule_hardware_data_value.get("final_extended_sell_amount", 0)
        }
    for key, current_schedule_hardware_data_value in current_schedule_hardware_data.items():
        short_code = key
        current_schedule_hardware_data_res[short_code] = {
            'short_code': current_schedule_hardware_data_value.get('short_code'),
            'feature_details': current_schedule_hardware_data_value.get('feature_details', {}),
            'desc': current_schedule_hardware_data_value.get('desc', ''),
            'markup': current_schedule_hardware_data_value.get('markup', 0),
            'margin': current_schedule_hardware_data_value.get('margin', 0),
            'discount_type': current_schedule_hardware_data_value.get('discount_type', "PERCENTAGE"),
            'discount': current_schedule_hardware_data_value.get('discount', 0),
            'surcharge_type': current_schedule_hardware_data_value.get('surcharge_type', "PERCENTAGE"),
            'surcharge': current_schedule_hardware_data_value.get('surcharge', 0),
            'quantity': current_schedule_hardware_data_value.get('quantity', 0),
            "total_amount": current_schedule_hardware_data_value.get("total_amount", 0),
            "total_sell_amount": current_schedule_hardware_data_value.get("total_sell_amount", 0),
            "total_base_amount": current_schedule_hardware_data_value.get("total_base_amount", 0),
            "total_extended_sell_amount": current_schedule_hardware_data_value.get("total_extended_sell_amount", 0),
            "final_amount": current_schedule_hardware_data_value.get("final_amount", 0),
            "final_sell_amount": current_schedule_hardware_data_value.get("final_sell_amount", 0),
            "final_base_amount": current_schedule_hardware_data_value.get("final_base_amount", 0),
            "final_extended_sell_amount": current_schedule_hardware_data_value.get("final_extended_sell_amount", 0)
        }
    if not v0_schedule_hardware_data_res and not current_schedule_hardware_data_res:
        return {}
    return await get_schedule_hardware_data_version_differences(project_id, schedule_id, opening_number, v0_schedule_hardware_data_res, current_schedule_hardware_data_res)



async def get_schedule_hardware_data_version_differences(project_id, schedule_id, opening_number, v0_schedule_hardware_data_res, current_schedule_hardware_data_res):
    """
    Compares take-off and schedule hardware data, identifies differences, and inserts them into the database.

    This function:
    - Merges all unique short codes (keys) from both take-off and schedule hardware data.
    - Prepares normalized hardware pricing data for both datasets using `prepare_schedule_hardware_price_data`.
    - Computes the differences between the two datasets using `get_hardware_diff`.
    - Persists the differences in the database using `insert_hardware_diff_to_db`.

    Args:
        db (Session): SQLAlchemy database session.
        current_member_id (User): The user performing the operation, used for auditing.
        project_id (int): ID of the project associated with the hardware data.
        schedule_id (int): ID of the schedule being compared.
        opening_number (str): The opening number linked to the schedule.
        v0_schedule_hardware_data_res (dict): Normalized dictionary of take-off hardware data.
        current_schedule_hardware_data_res (dict): Normalized dictionary of current schedule hardware data.

    Returns:
        Any: The response returned by `insert_hardware_diff_to_db`, typically a confirmation or status object.

    Raises:
        Exception: If an error occurs during processing or database operations, it is logged and re-raised.

    Notes:
        - This function assumes both `v0_schedule_hardware_data_res` and `current_schedule_hardware_data_res` are preprocessed and valid.
        - Exceptions are caught and logged using a standard logger before being re-raised.
    """
    try:
        all_keys = set(v0_schedule_hardware_data_res.keys()) | set(current_schedule_hardware_data_res.keys())
        # print("all_keys:: ", all_keys)
        # print("v0_schedule_hardware_data_res:: ", v0_schedule_hardware_data_res.keys())
        # print("current_schedule_hardware_data_res:: ", current_schedule_hardware_data_res.keys())
        v0_schedule_hardware_data = await prepare_schedule_hardware_price_data(all_keys, v0_schedule_hardware_data_res)
        # print("v0_schedule_hardware_data", v0_schedule_hardware_data)

        current_schedule_hardware_data = await prepare_schedule_hardware_price_data(all_keys, current_schedule_hardware_data_res)
        # print("current_schedule_hardware_data", current_schedule_hardware_data)

        diff_result = await get_schedule_hardware_differences(v0_schedule_hardware_data, current_schedule_hardware_data)
        # print("diff_result:: ", diff_result)

        response = await format_schedule_hardware_data_version_differences(diff_result, project_id, schedule_id, opening_number)
        # print("response:: ", response)
        return response
    except Exception as e:
        print(f"get_schedule_hardware_data_version_differences:: An unexpected error occurred: {e}")
        raise e
    

async def prepare_schedule_hardware_price_data(all_keys, hardware_data_res):
    """
    Processes and structures pricing data for both base and adon hardware features 
    using provided hardware metadata.

    For each short code in `all_keys`, the function extracts feature information 
    (base and adon), computes pricing using `get_all_pricing`, and constructs a 
    list of detailed feature dictionaries with pricing breakdowns.

    Args:
        all_keys (Iterable): A set or list of short codes representing unique hardware items.
        hardware_data_res (dict): A dictionary where keys are hardware short codes and values 
            contain feature and pricing metadata, such as:
            - feature_details
                - {
                    "featureCode": {
                        "name": featureCode,
                        "value": optionCode,
                        "is_adon_field": False/True,
                        "has_price_dependancy": True,
                        "quantity": quantity
                    }
                }
            - discount, discount_type
            - markup, margin
            - surcharge, surcharge_type
            - quantity,
            - total_amount, total_sell_amount, total_base_amount, total_extended_sell_amount
            - final_amount, final_sell_amount, final_base_amount, final_extended_sell_amount

    Returns:
        dict: A dictionary where each key is a hardware short code and the value is a list of
              dictionaries representing features (both base and adon), enriched with:
              - name, value
              - is_adon_field, has_price_dependancy
              - quantity
              - total_amount, total_base_amount, total_sell_amount, total_extended_sell_amount
              - discount

    Raises:
        Exception: Any exception during processing is logged and re-raised.

    Notes:
        - Base and adon features are separately processed and merged.
        - `get_all_pricing` is used to compute total amounts considering discount, markup, and surcharge.
        - Adon features are assigned a quantity of 1 by default.
    """
    try:
        result = {}
        def get_values(features):
            values = []
            for feature_code, feature_details in features.items():
                values.append(f"{feature_code} - {feature_details.get('value')}")
            return ", ".join(elm for elm in values)
        print("all_keys:: ", all_keys)
        print("hardware_data_res:: ", hardware_data_res.keys())
        for key in sorted(all_keys):
            if key in hardware_data_res:
                feature_details = hardware_data_res[key].get("feature_details", {})
                hardware_data = hardware_data_res[key]
                initial_schedule_feature_price = {
                    'short_code': hardware_data.get('short_code'),
                    'feature_details': feature_details,
                    "component": COMPONENT_TYPE.HARDWARE.value,
                    "desc": hardware_data.get('desc', ''),  # Added field
                    "name": key,
                    "value": get_values(feature_details),
                    "is_adon_field": False,
                    "has_price_dependancy": True,
                    'markup': hardware_data.get('markup', 0),
                    'margin': hardware_data.get('margin', 0),
                    'discount_type': hardware_data.get('discount_type'),
                    'discount': hardware_data.get('discount', 0),
                    'surcharge_type': hardware_data.get('surcharge_type', 0),
                    'surcharge': hardware_data.get('surcharge', 0),
                    'quantity': hardware_data.get('quantity', 0),
                    "total_amount": hardware_data.get("total_amount", 0),
                    "total_sell_amount": hardware_data.get("total_sell_amount", 0),
                    "total_base_amount": hardware_data.get("total_base_amount", 0),
                    "total_extended_sell_amount": hardware_data.get("total_extended_sell_amount", 0),
                    "final_amount": hardware_data.get("final_amount", 0),
                    "final_sell_amount": hardware_data.get("final_sell_amount", 0),
                    "final_base_amount": hardware_data.get("final_base_amount", 0),
                    "final_extended_sell_amount": hardware_data.get("final_extended_sell_amount", 0)
                }
                result[key] = initial_schedule_feature_price
        # print("----------------------------------")
        # print("all_keys", all_keys)
        # print("result", result)
        # print("----------------------------------")
        return result
    except Exception as e:
        print(f"prepare_schedule_hardware_price_data:: An unexpected error occurred: {e}")
        raise e
    

async def get_schedule_hardware_differences(v0_schedule_hardware_data, current_schedule_hardware_data):
    """
    Compares the hardware data from the take-off and schedule and returns the differences.

    This function processes and compares the hardware data from the take-off and the schedule. 
    For each hardware item (identified by short code), it collects and compares the associated 
    features, including quantity, price, discount, and other attributes. The function returns 
    a dictionary containing the differences between the two datasets, categorized by hardware short code.

    Args:
        v0_schedule_hardware_data (dict): A dictionary where each key is a hardware short code 
                                       and the value is a list of feature dictionaries 
                                       representing the hardware data from the take-off.
        current_schedule_hardware_data (dict): A dictionary where each key is a hardware short code 
                                       and the value is a list of feature dictionaries 
                                       representing the hardware data from the schedule.

    Returns:
        dict: A dictionary where each key is a hardware short code and the value is another 
              dictionary with the following structure:
            {
                "name":{
                    'short_code': hardware_data_res.get('short_code'),
                    'feature_details': feature_details,
                    "component": COMPONENT_TYPE.HARDWARE.value,
                    "desc": hardware_data_res.get('desc', ''),  # Added field
                    "name": key,
                    "value": get_values(feature_details),
                    "is_adon_field": False,
                    "has_price_dependancy": True,
                    'markup': hardware_data_res.get('markup', 0),
                    'margin': hardware_data_res.get('margin', 0),
                    'discount_type': hardware_data_res.get('discount_type'),
                    'discount': hardware_data_res.get('discount', 0),
                    'surcharge_type': hardware_data_res.get('surcharge_type', 0),
                    'surcharge': hardware_data_res.get('surcharge', 0),
                    'quantity': hardware_data_res.get('quantity', 0),
                    "total_amount": hardware_data_res.get("total_amount", 0),
                    "total_sell_amount": hardware_data_res.get("total_sell_amount", 0),
                    "total_base_amount": hardware_data_res.get("total_base_amount", 0),
                    "total_extended_sell_amount": hardware_data_res.get("total_extended_sell_amount", 0),
                    "final_amount": hardware_data_res.get("final_amount", 0),
                    "final_sell_amount": hardware_data_res.get("final_sell_amount", 0),
                    "final_base_amount": hardware_data_res.get("final_base_amount", 0),
                    "final_extended_sell_amount": hardware_data_res.get("final_extended_sell_amount", 0)
                }
            }
    Raises:
        None: The function doesn't raise any exceptions, but may return empty lists if no differences are found.
    Notes:
        - The function computes final amounts based on quantity for both take-off and schedule hardware data.
        - It considers various fields such as `is_adon_field`, `has_price_dependancy`, and `discount` while comparing.
        - This comparison focuses on price and quantity differences between the two datasets.
    """
    all_keys = set(v0_schedule_hardware_data.keys()) | set(current_schedule_hardware_data.keys())
    # common_keys = set(v0_schedule_hardware_data.keys()) & set(current_schedule_hardware_data.keys())
    # new_added_keys = set(current_schedule_hardware_data.keys()) - set(v0_schedule_hardware_data.keys())
    # removed_keys = set(v0_schedule_hardware_data.keys()) - set(current_schedule_hardware_data.keys())
    # print("v0_schedule_hardware_data:: ",v0_schedule_hardware_data.keys())
    # print("current_schedule_hardware_data:: ",current_schedule_hardware_data.keys())
    # print("common_keys:: ",common_keys)
    # print("new_added_keys:: ",new_added_keys)
    # print("removed_keys:: ",removed_keys)
    diff_result = {}
    for key in sorted(all_keys):
        item = {
            "v0_schedule_hardware_data": None,
            "current_schedule_hardware_data": None
        }
        # Process v0_schedule_hardware_data
        if key in v0_schedule_hardware_data:
            feature = v0_schedule_hardware_data[key]
            quantity = feature.get("quantity")
            item["v0_schedule_hardware_data"] = {
                "name": feature.get("name"),
                "value": feature.get("value"),
                "total_amount": feature.get("total_amount", 0),
                "total_base_amount": feature.get("total_base_amount", 0), 
                "total_sell_amount": feature.get("total_sell_amount", 0), 
                "total_extended_sell_amount": feature.get("total_extended_sell_amount", 0), 
                "quantity": quantity,
                "final_amount": feature.get("final_amount", feature.get("total_amount", 0)),
                "final_base_amount": feature.get("final_base_amount", feature.get("final_base_amount", 0)), 
                "final_sell_amount": feature.get("final_sell_amount", feature.get("final_sell_amount", 0)), 
                "final_extended_sell_amount": feature.get("final_sell_amount", feature.get("final_sell_amount", 0)), 
                "component": "HARDWARE",
                'short_code': key,
                "is_adon_field": feature.get("is_adon_field", False),
                "has_price_dependancy": feature.get("has_price_dependancy", False),
                "discount": feature.get('discount', 0),
                "discount_type": feature.get('discount_type', None),
                "surcharge": feature.get('surcharge', 0),
                "surcharge_type": feature.get('surcharge_type', None),
                "markup": feature.get('markup', 0),
                "margin": feature.get('margin', 0)
            }
        # Process schedule_hardware_data (if needed)
        if key in current_schedule_hardware_data:
            feature = current_schedule_hardware_data[key]
            quantity = feature.get("quantity")
            item["current_schedule_hardware_data"] = {
                "name": feature.get("name"),
                "value": feature.get("value"),
                "total_amount": feature.get("total_amount", 0),
                "total_base_amount": feature.get("total_base_amount", 0), 
                "total_sell_amount": feature.get("total_sell_amount", 0), 
                "total_extended_sell_amount": feature.get("total_extended_sell_amount", 0), 
                "quantity": quantity,
                "final_amount": feature.get("final_amount", feature.get("total_amount", 0)),
                "final_base_amount": feature.get("final_base_amount", feature.get("final_base_amount", 0)), 
                "final_sell_amount": feature.get("final_sell_amount", feature.get("final_sell_amount", 0)), 
                "final_extended_sell_amount": feature.get("final_sell_amount", feature.get("final_sell_amount", 0)), 
                "component": "HARDWARE",
                'short_code': key,
                "is_adon_field": feature.get("is_adon_field", False),
                "has_price_dependancy": feature.get("has_price_dependancy", False),
                "discount": feature.get('discount', 0),
                "discount_type": feature.get('discount_type', None),
                "surcharge": feature.get('surcharge', 0),
                "surcharge_type": feature.get('surcharge_type', None),
                "markup": feature.get('markup', 0),
                "margin": feature.get('margin', 0)
            }
        if (
            item["v0_schedule_hardware_data"] is None and item["current_schedule_hardware_data"] is not None
            or
            item["current_schedule_hardware_data"] is None and item["v0_schedule_hardware_data"] is not None
            or
            item["v0_schedule_hardware_data"]["value"] != item["current_schedule_hardware_data"]["value"]
            or
            item["v0_schedule_hardware_data"]["quantity"] != item["current_schedule_hardware_data"]["quantity"]
        ):
            diff_result[key] = item
    return diff_result



def get_value(data, key, default=None):
    """
    Safely retrieves a value from a dictionary, returning a default value if the key is not found.
    """
    return data.get(key) if data and key in data else default




async def format_schedule_hardware_data_version_differences(differences, project_id, schedule_id, opening_number):
    """
    Formats the differences between take-off data and schedule data into a structured list of entries.
    This function processes a dictionary of differences, extracting relevant fields from both
    the take-off data and the schedule data, and compiles them into a list of dictionaries
    with standardized keys.
    Args:
        differences (dict): A dictionary where each key is a field name and the value is another
                            dictionary containing 'initial_schedule_data' and 'opening_data'.
        project_id (str): The ID of the project associated with the schedule.
        schedule_id (str): The ID of the schedule being compared.
        opening_number (str): The opening number associated with the schedule.
    Returns:    
        list: A list of dictionaries, each representing a field with its associated data
              from both the take-off and the schedule, formatted with consistent keys.
    Raises:
        Exception: If any error occurs during the processing of the differences.
    """
    try:
        def extract(prefix, data):
            return {
                f"{prefix}_feature_code": get_value(data, "feature_code"),
                f"{prefix}_option_code": get_value(data, "option_code"),
                f"{prefix}_value": get_value(data, "value"),
                f"{prefix}_total_amount": get_value(data, "total_amount", 0),
                f"{prefix}_total_base_amount": get_value(data, "total_base_amount", 0),
                f"{prefix}_total_sell_amount": get_value(data, "total_sell_amount", 0),
                f"{prefix}_total_extended_sell_amount": get_value(data, "total_extended_sell_amount", 0),
                f"{prefix}_quantity": get_value(data, "quantity", 1),
                f"{prefix}_final_amount": get_value(data, "final_amount", 0),
                f"{prefix}_final_base_amount": get_value(data, "final_base_amount", 0),
                f"{prefix}_final_sell_amount": get_value(data, "final_sell_amount", 0),
                f"{prefix}_final_extended_sell_amount": get_value(data, "final_extended_sell_amount", 0),
                f"{prefix}_discount": get_value(data, "discount", 0),
                f"{prefix}_discount_type": get_value(data, "discount_type", None),
                f"{prefix}_surcharge": get_value(data, "surcharge", 0),
                f"{prefix}_surcharge_type": get_value(data, "surcharge_type", None),
                f"{prefix}_markup": get_value(data, "markup", 0),
                f"{prefix}_margin": get_value(data, "margin", 0),
            } if data else {
                f"{prefix}_feature_code": get_value(data, "feature_code"),
                f"{prefix}_option_code": get_value(data, "option_code"),
                f"{prefix}_value": get_value(data, "value"),
                f"{prefix}_total_amount": get_value(data, "total_amount", 0),
                f"{prefix}_total_base_amount": get_value(data, "total_base_amount", 0),
                f"{prefix}_total_sell_amount": get_value(data, "total_sell_amount", 0),
                f"{prefix}_total_extended_sell_amount": get_value(data, "total_extended_sell_amount", 0),
                f"{prefix}_quantity": get_value(data, "quantity", 1),
                f"{prefix}_final_amount": get_value(data, "final_amount", 0),
                f"{prefix}_final_base_amount": get_value(data, "final_base_amount", 0),
                f"{prefix}_final_sell_amount": get_value(data, "final_sell_amount", 0),
                f"{prefix}_final_extended_sell_amount": get_value(data, "final_extended_sell_amount", 0),
            }
        entries = []
        for field_name, field_data in differences.items():
            print("Field Name:", field_name)
            v0_schedule_hardware_data = field_data.get("v0_schedule_hardware_data")
            current_schedule_hardware_data = field_data.get("current_schedule_hardware_data")
            if not v0_schedule_hardware_data and not current_schedule_hardware_data:
                continue
            entry = {
                "project_id": project_id,
                "schedule_id": schedule_id,
                "opening_number": opening_number,
                "field_name": field_name,
                **extract("initial_schedule", v0_schedule_hardware_data),
                **extract("current_schedule", current_schedule_hardware_data),
                "component": get_value(v0_schedule_hardware_data, "component") or get_value(current_schedule_hardware_data, "component"),
                "is_manual": bool(get_value(v0_schedule_hardware_data, "is_manual", False) or get_value(current_schedule_hardware_data, "is_manual", False)),
                "is_adon_field": bool(get_value(v0_schedule_hardware_data, "is_adon_field", False) or get_value(current_schedule_hardware_data, "is_adon_field", False)),
                "has_price_dependancy": bool(get_value(v0_schedule_hardware_data, "has_price_dependancy", False) or get_value(current_schedule_hardware_data, "has_price_dependancy", False)),
                "part_number": get_value(v0_schedule_hardware_data, "part_number") or get_value(current_schedule_hardware_data, "part_number"),
            }
            entries.append(entry)
        return entries
    except Exception as e:
        print(str(e))

    """
    Inserts hardware difference data between take-off and schedule into the OpeningChangeStats table.

    This function compares hardware data from the take-off sheet and schedule, identifies discrepancies,
    and records them in the database. It removes any existing records for the same project, schedule, 
    and component ("HARDWARE") before inserting updated difference records.

    Args:
        db (Session): SQLAlchemy database session.
        diff_result (dict): Dictionary containing hardware data differences grouped by short_code.
        project_id (int): ID of the current project.
        schedule_id (int): ID of the schedule associated with the hardware.
        opening_number (str): The opening number this difference data belongs to.
        current_member_id (User): The user making the changes, used for tracking updates.

    Returns:
        list: A list of dictionaries representing the data inserted into OpeningChangeStats.

    Raises:
        None explicitly. Any exceptions during DB operations should be handled by the calling context.
    """
    response = []
    for key, item in differences.items():
        v0_schedule_hardware_data = {entry["name"]: entry for entry in item["v0_schedule_hardware_data"]}
        current_schedule_hardware_data = {entry["name"]: entry for entry in item["current_schedule_hardware_data"]}
        all_names = set(v0_schedule_hardware_data.keys()) | set(current_schedule_hardware_data.keys())
        for name in all_names:
            v0_schedule_hardware = v0_schedule_hardware_data.get(name)
            current_schedule_hardware = current_schedule_hardware_data.get(name)
            if v0_schedule_hardware != current_schedule_hardware:  # Insert only if there's a difference
                if isinstance(v0_schedule_hardware, dict) and 'is_adon_field' in v0_schedule_hardware:
                    is_adon_field = v0_schedule_hardware['is_adon_field']
                elif isinstance(current_schedule_hardware, dict) and 'is_adon_field' in current_schedule_hardware:
                    is_adon_field = current_schedule_hardware['is_adon_field']
                else:
                    is_adon_field = None
                if isinstance(v0_schedule_hardware, dict) and 'has_price_dependancy' in v0_schedule_hardware:
                    has_price_dependancy = v0_schedule_hardware['has_price_dependancy']
                elif isinstance(current_schedule_hardware, dict) and 'has_price_dependancy' in current_schedule_hardware:
                    has_price_dependancy = current_schedule_hardware['has_price_dependancy']
                else:
                    has_price_dependancy = None
                data = {
                    'project_id':  project_id,
                    'schedule_id': schedule_id,
                    'opening_number': opening_number,
                    'component': "HARDWARE",
                    'field_name': name,
                    'initial_schedule_feature_code': v0_schedule_hardware.get("feature_code") if v0_schedule_hardware else None,
                    'current_schedule_feature_code': current_schedule_hardware.get("feature_code") if current_schedule_hardware else None,
                    'initial_schedule_option_code': v0_schedule_hardware.get("option_code") if v0_schedule_hardware else None,
                    'initial_schedule_value': v0_schedule_hardware.get("value") if v0_schedule_hardware else None,
                    'initial_schedule_total_amount': v0_schedule_hardware.get("total_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_total_base_amount': v0_schedule_hardware.get("total_base_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_total_sell_amount': v0_schedule_hardware.get("total_sell_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_total_extended_sell_amount': v0_schedule_hardware.get("total_extended_sell_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_quantity': v0_schedule_hardware.get("quantity", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_final_amount': v0_schedule_hardware.get("final_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_final_base_amount': v0_schedule_hardware.get("final_base_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_final_sell_amount': v0_schedule_hardware.get("final_sell_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_final_extended_sell_amount': v0_schedule_hardware.get("final_extended_sell_amount", 0) if v0_schedule_hardware else 0,
                    'initial_schedule_discount': v0_schedule_hardware.get("discount") if v0_schedule_hardware else 0,
                    'initial_schedule_discount_type': v0_schedule_hardware.get("discount_type") if v0_schedule_hardware else None,
                    'initial_schedule_surcharge': v0_schedule_hardware.get("surcharge") if v0_schedule_hardware else 0,
                    'initial_schedule_surcharge_type': v0_schedule_hardware.get("surcharge_type") if v0_schedule_hardware else None,
                    'initial_schedule_margin': v0_schedule_hardware.get("margin") if v0_schedule_hardware else 0,
                    'initial_schedule_markup': v0_schedule_hardware.get("markup") if v0_schedule_hardware else 0,
                    'is_adon_field': is_adon_field,
                    'has_price_dependancy': has_price_dependancy,
                    'short_code': key,
                    'current_schedule_option_code': current_schedule_hardware.get("option_code") if current_schedule_hardware else None,
                    'current_schedule_value': current_schedule_hardware.get("value") if current_schedule_hardware else None,
                    'current_schedule_total_amount': current_schedule_hardware.get("total_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_total_base_amount': current_schedule_hardware.get("total_base_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_total_sell_amount': current_schedule_hardware.get("total_sell_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_total_extended_sell_amount': current_schedule_hardware.get("total_extended_sell_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_quantity': current_schedule_hardware.get("quantity", 0) if current_schedule_hardware else 0,
                    'current_schedule_final_amount': current_schedule_hardware.get("final_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_final_base_amount': current_schedule_hardware.get("final_base_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_final_sell_amount': current_schedule_hardware.get("final_sell_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_final_extended_sell_amount': current_schedule_hardware.get("final_extended_sell_amount", 0) if current_schedule_hardware else 0,
                    'current_schedule_discount': current_schedule_hardware.get("discount", 0) if current_schedule_hardware else 0,
                    'current_schedule_discount_type': current_schedule_hardware.get("discount_type", 0) if current_schedule_hardware else None,
                    'current_schedule_surcharge': current_schedule_hardware.get("surcharge", 0) if current_schedule_hardware else 0,
                    'current_schedule_surcharge_type': current_schedule_hardware.get("surcharge_type", 0) if current_schedule_hardware else None,
                    'current_schedule_margin': current_schedule_hardware.get("margin", 0) if current_schedule_hardware else None,
                    'current_schedule_markup': current_schedule_hardware.get("markup", 0) if current_schedule_hardware else None,
                }
                response.append(data)
    # print(response)
    return response
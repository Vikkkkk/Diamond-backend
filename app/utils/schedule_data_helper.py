

async def build_schedule_data_dict(schedule_data_records, quantity: int = 1) -> dict:
    """Build dict for schedule_data (by name or feature_code)."""
    data_dict = {}
    for sd in schedule_data_records:
        sd_dict = sd.to_dict
        key = sd.name or sd.feature_code or str(sd.id)
        component_key = f'{sd_dict["component"] or "GENERAL"} {sd_dict["part_number"] or ""}'.strip()
        if component_key not in data_dict:
            data_dict[component_key] = {}
        data_dict[component_key][key] = {
            "id": sd_dict["id"],
            "desc": sd_dict["desc"],
            "name": sd_dict["name"],
            "value": sd_dict["value"],
            "margin": sd_dict["margin"],
            "markup": sd_dict["markup"],
            "discount": sd_dict["discount"],
            "quantity": sd_dict["quantity"],
            "component": sd_dict["component"],
            "is_manual": sd_dict["is_manual"],
            "surcharge": sd_dict["surcharge"],
            "price_data": sd_dict["price_data"],
            "option_code": sd_dict["option_code"],
            "part_number": sd_dict["part_number"],
            "schedule_id": sd_dict["schedule_id"],
            "feature_code": sd_dict["feature_code"],
            "feature_data": sd_dict["feature_data"],
            "final_amount": sd_dict["final_amount"],
            "total_amount": sd_dict["total_amount"],
            "adon_field_id": sd_dict["adon_field_id"],
            "discount_type": sd_dict["discount_type"],
            "is_adon_field": sd_dict["is_adon_field"],
            "is_table_data": sd_dict["is_table_data"],
            "surcharge_type": sd_dict["surcharge_type"],
            "additional_data": sd_dict["additional_data"],
            "final_base_amount": sd_dict["final_base_amount"],
            "final_sell_amount": sd_dict["final_sell_amount"],
            "is_basic_discount": sd_dict["is_basic_discount"],
            "total_base_amount": sd_dict["total_base_amount"],
            "total_sell_amount": sd_dict["total_sell_amount"],
            "adon_field_option_id": sd_dict["adon_field_option_id"],
            "has_price_dependancy": sd_dict["has_price_dependancy"],
            "final_extended_sell_amount": sd_dict["final_extended_sell_amount"],
            "total_extended_sell_amount": sd_dict["total_extended_sell_amount"],
        }
    data_dict, price_details = await get_component_wise_price_details(data_dict, quantity)
    return data_dict, price_details


async def get_component_wise_price_details(component_wise_schedule_data: dict, quantity: int = 1):
    try:
        total_pricing = {
            "total_amount": 0,
            "total_sell_amount": 0,
            "total_base_amount": 0,
            "total_extended_sell_amount": 0,
            "final_amount": 0,
            "final_sell_amount": 0,
            "final_base_amount": 0,
            "final_extended_sell_amount": 0
        }
        pricing_details = {}
        for component, fields in component_wise_schedule_data.items():
            pricing_details[component] = {}
            new_version_dict = {
                field_name: field.dict(exclude_unset=True) if hasattr(field, "dict") else field
                for field_name, field in fields.items()
            }
            # Helper to safely fetch float values
            def safe_get(d, key):
                return float(d.get(key, 0) or 0)
            # --- Define calculated values first ---
            # Helper to calculate amounts for each key
            def calc_amounts(key):
                adon_vals = [safe_get(v, key) for v in new_version_dict.values() if v.get("is_adon_field")]
                non_adon_vals = [safe_get(v, key) for v in new_version_dict.values() if not v.get("is_adon_field")]
                return sum(adon_vals) + (max(non_adon_vals) if non_adon_vals else 0)
            total_amount = calc_amounts("final_amount")
            total_sell_amount = calc_amounts("final_sell_amount")
            total_base_amount = calc_amounts("final_base_amount")
            total_extended_sell_amount = calc_amounts("final_extended_sell_amount")
            # If quantity is set, derive final_amount = total_amount * quantity
            final_amount = total_amount * quantity if total_amount else None
            final_sell_amount = total_sell_amount * quantity if total_sell_amount else None
            final_base_amount = total_base_amount * quantity if total_base_amount else None
            final_extended_sell_amount = (
                total_extended_sell_amount * quantity if total_extended_sell_amount else None
            )
            pricing_details[component]["fields"] = new_version_dict
            pricing_details[component]["price_details"] = {
                "total_amount": total_amount,
                "total_sell_amount": total_sell_amount,
                "total_base_amount": total_base_amount,
                "total_extended_sell_amount": total_extended_sell_amount,
                "final_amount": final_amount,
                "final_sell_amount": final_sell_amount,
                "final_base_amount": final_base_amount,
                "final_extended_sell_amount": final_extended_sell_amount
            }  
            total_pricing["total_amount"] += total_amount or 0
            total_pricing["total_sell_amount"] += total_sell_amount or 0
            total_pricing["total_base_amount"] += total_base_amount or 0
            total_pricing["total_extended_sell_amount"] += total_extended_sell_amount or 0  
            total_pricing["final_amount"] += final_amount or 0
            total_pricing["final_sell_amount"] += final_sell_amount or 0
            total_pricing["final_base_amount"] += final_base_amount or 0
            total_pricing["final_extended_sell_amount"] += final_extended_sell_amount or 0
        return pricing_details, total_pricing
    except Exception as e:
        # Log the exception with a detailed error message
        print(f"get_component_wise_price_details:: Error : {e}")
        raise e


async def fill_missing_values_in_schedule_data(schedule_data_curr_version: dict, scedule_data_version_zero: dict) -> dict:
    try:
        possible_missing_keys = [
            "margin",
            "markup",
            "discount",
            "quantity",
            "surcharge",
            "discount_type",
            "is_table_data",
            "surcharge_type",
            "additional_data",
            "is_basic_discount"
        ]
        missing_price_keys = {
            "feature_code": None,
            "feature_data": {},
            "price_data": [],
            "option_code": None,
            "total_amount": 0,
            "total_sell_amount": 0,
            "total_base_amount": 0,
            "total_extended_sell_amount": 0,
            "final_amount": 0,
            "final_sell_amount": 0,
            "final_base_amount": 0,
            "final_extended_sell_amount": 0
        }
         # First, ensure all possible keys exist in version zero with default values if missing
        for component_key, fields in schedule_data_curr_version.items():
            if component_key in scedule_data_version_zero:
                scedule_data_version_zero_component_data = scedule_data_version_zero[component_key]["fields"]
                #get the first field in teh version zero data
                scedule_data_version_zero_component_data_first_field = list(scedule_data_version_zero_component_data.keys())[0]
                scedule_data_version_zero_component_data_first_field_data = scedule_data_version_zero_component_data[scedule_data_version_zero_component_data_first_field]
                possible_missing_key_values = {
                    "margin": scedule_data_version_zero_component_data_first_field_data.get("margin", 0),
                    "markup": scedule_data_version_zero_component_data_first_field_data.get("markup", 0),
                    "discount": scedule_data_version_zero_component_data_first_field_data.get("discount", 0),
                    "quantity": scedule_data_version_zero_component_data_first_field_data.get("quantity", 1),
                    "surcharge": scedule_data_version_zero_component_data_first_field_data.get("surcharge", 0),
                    "discount_type": scedule_data_version_zero_component_data_first_field_data.get("discount_type", "PERCENTAGE"),
                    "is_table_data": scedule_data_version_zero_component_data_first_field_data.get("is_table_data", False),
                    "surcharge_type": scedule_data_version_zero_component_data_first_field_data.get("surcharge_type", "PERCENTAGE"),
                    "additional_data": scedule_data_version_zero_component_data_first_field_data.get("additional_data", None),
                    "is_basic_discount": scedule_data_version_zero_component_data_first_field_data.get("is_basic_discount", False)
                }
                for field_name, field_value in fields.items():
                    for key in possible_missing_keys:
                        if key not in field_value:
                            # print("missing key:: ", key, " in field:: ", field_name, " for component:: ", component_key)
                            # Fill from version zero if missing
                            if key in possible_missing_key_values:
                                # print(f"Filling missing key '{key}' from field '{scedule_data_version_zero_component_data_first_field}' in component '{component_key}' from v0")
                                schedule_data_curr_version[component_key][field_name][key] = possible_missing_key_values[key]
                    for key in missing_price_keys:
                        if key not in field_value:
                            # print("missing key:: ", key, " in field:: ", field_name, " for component:: ", component_key)
                            schedule_data_curr_version[component_key][field_name][key] = missing_price_keys[key]
        return schedule_data_curr_version
    except Exception as e:
        # Log the exception with a detailed error message
        print(f"fill_missing_values_in_schedule_data:: Error : {e}")
        raise e


async def get_schedule_data_version_differences(v0_schedule_data, current_schedule_data):
    """
    Compares two versions of schedule data and identifies differences.
    This function takes two dictionaries representing different versions of schedule data
    and compares them to identify differences in their values. It returns a dictionary
    that highlights the differences between the two versions.
    Args:
        v0_schedule_data (dict): The first version of the schedule data to compare.
        current_schedule_data (dict): The second version of the schedule data to compare.
    Returns:
        dict: A dictionary containing the differences between the two versions of schedule data.
              Each key represents a field name, and the value is another dictionary with keys
              'v0_schedule_data' and 'current_schedule_data' showing the respective values.
    Raises:
        None explicitly, but may propagate exceptions from dictionary operations.
    """
    diff_result = {}
    for component_key, component_data in v0_schedule_data.items():
        component_v0_schedule_data = component_data.get("fields", {})
        component_current_schedule_data = current_schedule_data.get(component_key, {}).get("fields", {})
        all_keys = set(component_v0_schedule_data.keys()) | set(component_current_schedule_data.keys())
        print("all_keys:: ", all_keys)
        for key in sorted(all_keys):
            item = {
                "v0_schedule_data": None,
                "current_schedule_data": None
            }

            if key in component_v0_schedule_data:
                item["v0_schedule_data"] = {
                    "name": component_v0_schedule_data[key].get("name"),
                    "feature_code": component_v0_schedule_data[key].get("feature_code"),
                    "option_code": component_v0_schedule_data[key].get("option_code"),
                    "value": component_v0_schedule_data[key].get("value"),
                    "total_amount": component_v0_schedule_data[key].get("total_amount"),
                    "total_base_amount": component_v0_schedule_data[key].get("total_base_amount"),
                    "total_sell_amount": component_v0_schedule_data[key].get("total_sell_amount"),
                    "total_extended_sell_amount": component_v0_schedule_data[key].get("total_extended_sell_amount"),
                    "quantity": component_v0_schedule_data[key].get("quantity"),
                    "final_amount": component_v0_schedule_data[key].get("final_amount"),
                    "final_base_amount": component_v0_schedule_data[key].get("final_base_amount"),
                    "final_sell_amount": component_v0_schedule_data[key].get("final_sell_amount"),
                    "final_extended_sell_amount": component_v0_schedule_data[key].get("final_extended_sell_amount"),
                    "component": component_v0_schedule_data[key].get("component"),
                    "part_number": component_v0_schedule_data[key].get("part_number"),
                    "discount": component_v0_schedule_data[key].get("discount"),
                    "discount_type": component_v0_schedule_data[key].get("discount_type", "PERCENTAGE"),
                    "surcharge": component_v0_schedule_data[key].get("surcharge"),
                    "surcharge_type": component_v0_schedule_data[key].get("surcharge_type", "PERCENTAGE"),
                    "markup": component_v0_schedule_data[key].get("markup"),
                    "margin": component_v0_schedule_data[key].get("margin"),
                    "is_manual": component_v0_schedule_data[key].get("is_manual"),
                    "is_adon_field": component_v0_schedule_data[key].get("is_adon_field"),
                    "has_price_dependancy": component_v0_schedule_data[key].get("has_price_dependancy"),
                    "part_number": component_v0_schedule_data[key].get("part_number"),
                }

            if key in component_current_schedule_data:
                item["current_schedule_data"] = {
                    "name": component_current_schedule_data[key].get("name"),
                    "feature_code": component_current_schedule_data[key].get("feature_code"),
                    "option_code": component_current_schedule_data[key].get("option_code"),
                    "value": component_current_schedule_data[key].get("value"),
                    "total_amount": component_current_schedule_data[key].get("total_amount"),
                    "total_base_amount": component_current_schedule_data[key].get("total_base_amount"),
                    "total_sell_amount": component_current_schedule_data[key].get("total_sell_amount"),
                    "total_extended_sell_amount": component_current_schedule_data[key].get("total_extended_sell_amount"),
                    "quantity": component_current_schedule_data[key].get("quantity"),
                    "final_amount": component_current_schedule_data[key].get("final_amount"),
                    "final_base_amount": component_current_schedule_data[key].get("final_base_amount"),
                    "final_sell_amount": component_current_schedule_data[key].get("final_sell_amount"),
                    "final_extended_sell_amount": component_current_schedule_data[key].get("final_extended_sell_amount"),
                    "component": component_current_schedule_data[key].get("component"),
                    "part_number": component_current_schedule_data[key].get("part_number"),
                    "discount": component_current_schedule_data[key].get("discount"),
                    "discount_type": component_current_schedule_data[key].get("discount_type", "PERCENTAGE"),
                    "surcharge": component_current_schedule_data[key].get("surcharge"),
                    "surcharge_type": component_current_schedule_data[key].get("surcharge_type", "PERCENTAGE"),
                    "markup": component_current_schedule_data[key].get("markup"),
                    "margin": component_current_schedule_data[key].get("margin"),
                    "is_manual": component_current_schedule_data[key].get("is_manual"),
                    "is_adon_field": component_current_schedule_data[key].get("is_adon_field"),
                    "has_price_dependancy": component_current_schedule_data[key].get("has_price_dependancy"),
                    "part_number": component_current_schedule_data[key].get("part_number"),
                }
            if (
                item["v0_schedule_data"] is None and item["current_schedule_data"] is not None
                or
                item["current_schedule_data"] is None and item["v0_schedule_data"] is not None
                or
                item["v0_schedule_data"]["value"] != item["current_schedule_data"]["value"]
            ):
                # print("Difference found for key:", key)
                if component_key not in diff_result:
                    diff_result[component_key] = {}
                diff_result[component_key][key] = item
    return diff_result



def get_value(data, key, default=None):
    """
    Safely retrieves a value from a dictionary, returning a default value if the key is not found.
    """
    return data.get(key) if data and key in data else default



async def format_schedule_data_version_differences(differences, project_id, schedule_id, opening_number):
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
                f"{prefix}_discount_type": get_value(data, "discount_type", "PERCENTAGE"),
                f"{prefix}_surcharge": get_value(data, "surcharge", 0),
                f"{prefix}_surcharge_type": get_value(data, "surcharge_type", "PERCENTAGE"),
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
        for component_key, component_differences in differences.items():
            print("Component Key:", component_key)
            for field_name, field_data in component_differences.items():
                print("Field Name:", field_name)
                v0_schedule_data = field_data.get("v0_schedule_data")
                current_schedule_data = field_data.get("current_schedule_data")
                if not v0_schedule_data and not current_schedule_data:
                    continue
                entry = {
                    "project_id": project_id,
                    "schedule_id": schedule_id,
                    "opening_number": opening_number,
                    "field_name": field_name,
                    **extract("initial_schedule", v0_schedule_data),
                    **extract("current_schedule", current_schedule_data),
                    "component": get_value(v0_schedule_data, "component") or get_value(current_schedule_data, "component"),
                    "is_manual": bool(get_value(v0_schedule_data, "is_manual", False) or get_value(current_schedule_data, "is_manual", False)),
                    "is_adon_field": bool(get_value(v0_schedule_data, "is_adon_field", False) or get_value(current_schedule_data, "is_adon_field", False)),
                    "has_price_dependancy": bool(get_value(v0_schedule_data, "has_price_dependancy", False) or get_value(current_schedule_data, "has_price_dependancy", False)),
                    "part_number": get_value(v0_schedule_data, "part_number") or get_value(current_schedule_data, "part_number"),
                }
                entries.append(entry)
        return entries
    except Exception as e:
        print(str(e))



async def compare_schedule_data(v0_schedule_data, current_schedule_data, project_id, schedule_id, opening_number):
    """
    Compares two sets of schedule data (v0_schedule_data and current_schedule_data) for a specific component type
    and optionally a part number, and returns the differences between them.
    Args:
        v0_schedule_data (dict): The first version of the schedule data to compare.
        current_schedule_data (dict): The second version of the schedule data to compare.
        project_id (str): The ID of the project associated with the schedule.
        schedule_id (str): The ID of the schedule being compared.
        opening_number (str): The opening number associated with the schedule.
    Returns:
        dict: A dictionary containing the differences between the two versions of schedule data
              for the specified component type and part number. If either input data is None or empty, returns an empty dictionary.
    Raises:
        None explicitly, but may propagate exceptions from the filtering and comparison functions.
    """
    if not (v0_schedule_data and current_schedule_data):
        return {}
    differences = await get_schedule_data_version_differences(v0_schedule_data, current_schedule_data)
    formatted_differences = await format_schedule_data_version_differences(differences, project_id, schedule_id, opening_number)
    # print("formatted_differences:: ", formatted_differences)
    return formatted_differences


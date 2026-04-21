"""Utility module for generating product descriptions from feature specifications."""
import asyncio

async def preprocess_feature_selection(adon_opening_fields, section, series, base_feature, adon_feature):
    """Process and combine feature selections into a unified dictionary.
    
    Args:
        adon_opening_fields: Door opening addditional options
        section: Product section type
        series: Product series
        base_feature: Dictionary of base features and their options
        adon_feature: Dictionary of additional features
        
    Returns:
        Dictionary containing processed feature selections
    """
    try:
        feature_selection = {
            **adon_opening_fields,
            "section": section,
            "series": series
        }
        for feature, feature_option in base_feature["selectedFeatures"].items():
            if "optionCode" in feature_option:
                feature_selection[feature] = feature_option["optionCode"]
        for feature, feature_option in base_feature["inputFeatures"].items():
            feature_selection[feature] = [(str(feature_option["value"]) + " " + feature_option["unit"]).strip()]
        for feature, feature_option in adon_feature.items():
            if isinstance(feature_option, dict):
                feature_selection[feature] = list(feature_option.keys())
            else:
                for elm in feature_option:
                    feature_selection[elm["title"]] = [elm["desc"]]
        return feature_selection
    except Exception as error:
        print(error)
        raise error

async def check_if_exists(spec, keyword):
    """Check if keyword exists in specification dictionary keys.
    
    Args:
        spec: Specification dictionary
        keyword: Search term to look for
        
    Returns:
        Tuple of (key, value) if found, None if not found
    """
    try:
        words_set = set(keyword.lower().split())
        for key, value in spec.items():
            # Check if all words are in the dictionary key
            key_with_spaces = key.replace("_", " ").lower()
            if words_set.issubset(set(key_with_spaces.lower().split())):
                return key, value
            # # Check if all words are in the dictionary value (convert to string if needed)
            # if isinstance(value, list):
            #     value_strings = " ".join(map(str, value)).lower()
            #     if words_set.issubset(set(value_strings.split())):
            #         return key, value
            # elif isinstance(value, str):
            #     if words_set.issubset(set(value.lower().split())):
            #         return key, value
        # Return None if no match found
        return None
    except Exception as error:
        print(error)
        raise error

# async def generate_description(spec, formula):
#     """Generate product description from specifications using a template formula.
#     Args:
#         spec: Dictionary of specifications
#         formula: Template string with placeholders
#     Returns:
#         Formatted description string
#     """
#     try:
#         # Split the formula into parts based on ' x ' separator
#         found_spec = []
#         formula_parts = formula.split(" x ")
#         description_parts = []
#         for part in formula_parts:
#             # Find placeholders in the current formula part
#             start = part.find("{")
#             end = part.find("}")
#             if start != -1 and end != -1:
#                 key = part[start + 1:end]
#                 value = check_if_exists(spec, key)
#                 print("key:: ",key)
#                 print("value:: ",value)
#                 if value is not None:
#                     spec_key , value = value
#                     # Replace the placeholder with the value
#                     if isinstance(value, list):
#                         value = " x ".join(value)  # Join list values with " x "
#                     description_parts.append(part.replace(f"{{{key}}}", value))
#                     found_spec.append(spec_key)
#                 elif key == "ohp":
#                     description_parts.append(part)
#                 # Skip this part if no value exists
#             else:
#                 # If no placeholder, keep the part as is
#                 description_parts.append(part)
#         not_found_spec = list(set(list(spec.keys())) - set(found_spec))
#         OHP = []
#         for elm in not_found_spec:
#             if "prep" in elm.lower():
#                 val = spec[elm]
#                 if isinstance(val, list):
#                     val = ", ".join(val)
#                 OHP.append(elm + " - " + val)
#         ohp_indx = None
#         for indx, elm in enumerate(description_parts):
#             if "ohp" in elm.lower():
#                 ohp_indx = indx
#                 break
#         if len(OHP) > 0:
#             desc = " x ".join(OHP)
#             description_parts[ohp_indx] = description_parts[ohp_indx].replace("""{ohp}""", desc)
#         print("description_parts:: ",description_parts)
#         # Combine all valid parts into the final description
#         return " x ".join(part.strip() for part in description_parts if "{" not in part)
#     except Exception as error:
#         print(error)
#         raise error

async def generate_description(spec, formula):
    """Generate product description from specifications using a template formula.
    
    Args:
        spec: Dictionary of specifications
        formula: Template string with placeholders
        
    Returns:
        Formatted description string
    """
    try:
        found_spec = set()
        description_parts = []
        # Process each formula part
        # print("formula.split( x ):: ",formula.split(" x "))
        for part in formula.split(" x "):
            # Extract placeholder if exists
            placeholder = part[part.find("{")+1:part.find("}")] if "{" in part else None
            # print("placeholder:: ",placeholder)
            if not placeholder:
                description_parts.append(part)
                continue
            if placeholder == "ohp":
                description_parts.append(part)
                continue
            # Check for matching specification
            match = await check_if_exists(spec, placeholder)
            # print("match:: ",match)
            if match:
                spec_key, value = match
                value_str = " x ".join(value) if isinstance(value, list) else value
                if placeholder is not None and value_str is not None:
                    description_parts.append(part.replace(f"{{{placeholder}}}", value_str))
                    found_spec.add(spec_key)
        # Handle other hardware preps (OHP)
        not_found_specs = [
            f"{key} - {', '.join(spec[key]) if isinstance(spec[key], list) else spec[key]}"
            for key in set(spec.keys()) - found_spec
            if "prep" in key.lower()
        ]
        # Replace OHP placeholder if exists
        if not_found_specs:
            ohp_desc = " x ".join(not_found_specs)
            for i, part in enumerate(description_parts):
                if "ohp" in part.lower():
                    description_parts[i] = part.replace("{ohp}", ohp_desc)
                    break
        # Join valid parts and return
        # print("description_parts:: ",description_parts)
        return " x ".join(part.strip() for part in description_parts if "{" not in part)
    except Exception as error:
        print(error)
        raise error


async def get_door_description(adon_opening_fields, section, series, base_feature, adon_feature):
    """Generate complete door description from provided specifications.
    
    Args:
        adon_opening_fields: Door opening addditional options
        section: Door section type
        series: Door series
        base_feature: Dictionary of base features
        adon_feature: Dictionary of additional features
        
    Returns:
        Formatted door description string
    """
    try:
        door_formula = (
            "{section} x Door edge - {edge} x Swing - {hand} x "
            "series - {series} X Seam - {seam}) x Width - {width} x "
            "Height - {height} x Hinges - {hinges} x Lock prep - {lock preps} x "
            "Other hardware preps - [{ohp}] x Closer reinforcement - {closer} x "
            "Fire rating - {fire rating} x CORE - {core} x "
            "Elevation - {elevation} x TAG - {tag}"
        )
        spec = await preprocess_feature_selection(adon_opening_fields, section, series, base_feature, adon_feature)
        print("\n\nspec:: ",spec)
        desc = await generate_description(spec, door_formula)
        return desc
    except Exception as error:
        print(error)
        raise error


async def get_frame_description(adon_opening_fields, section, series, base_feature, adon_feature):
    """Generate complete frame description from provided specifications.
    
    Args:
        adon_opening_fields: Door opening addditional options
        section: Frame section type
        series: Frame series
        base_feature: Dictionary of base features
        adon_feature: Dictionary of additional features
        
    Returns:
        Formatted frame description string
    """
    try:
        frame_formula = (
            "{section} x Profile - {profile} x Swing - {hand} x "
            "series - {series} x Weld type - {weld} X Gauge - {gauge} x "
            "Jamb depth - {jamb depth} x Width - {width} x Height - {height} x "
            "Strike prep - {strike prep} x Other hardware preps - [{ohp}] x "
            "Closer reinforcment - {closer} x Anchor - {anchor} x "
            "Fire Rating - {fire rating} x Elevation - {elevation} x TAG - {tag}"
        )
        spec = await preprocess_feature_selection(adon_opening_fields, section, series, base_feature, adon_feature)
        print("\n\nspec:: ",spec)
        desc = await generate_description(spec, frame_formula)
        return desc
    except Exception as error:
        print(error)
        raise error


async def get_opening_frame_description(schedule_info, base_features, adon_features):
    try:
        frame_formula = (
            "{section} x Profile - {profile} x Swing - {swing} x "
            "series - {frame series} x Weld type - {welding} x Gauge - {gauge} x "
            "Jamb depth - {jamb depth} x Width - {width} x Height - {height} x "
            "Strike prep - {strike jamb} x Other hardware preps - [{ohp}] x "
            "Closer reinforcment - {closers} x Anchor - {anchor} x "
            "Fire Rating - {fire label} x Elevation - {elevation} x TAG - {tag}"
        )
        spec = {
            **base_features,
            **adon_features,
            "section": schedule_info["frame_material_code"],
        }
        spec["swing"] = schedule_info["swing"]
        # print("\n\nframe spec:: ",spec)
        desc = await generate_description(spec, frame_formula)
        # print("\n\desc:: ",desc)
        return desc
    except Exception as error:
        print(error)
        raise error
    




async def get_opening_door_description(schedule_info, base_features, adon_features):
    try:
        door_formula = (
            "{section} x Door edge - {door edge} x Swing - {swing} x "
            "series - {door series} x Seam - {seam}) x Gauge - {gauge} x Width - {width} x "
            "Height - {height} x Hinges - {hinges} x Lock prep - {lock preps} x "
            "Other hardware preps - [{ohp}] x Closer reinforcement - {closers} x "
            "Fire rating - {fire label} x CORE - {core} x "
            "Elevation - {elevation} x TAG - {tag}"
        )
        spec = {
            **base_features,
            **adon_features,
            "section": schedule_info["door_material_code"],
        }
        spec["swing"] = schedule_info["swing"]
        # print("\n\ndoor spec:: ",spec)
        desc = await generate_description(spec, door_formula)
        # print("\n\desc:: ",desc)
        return desc
    except Exception as error:
        print(error)
        raise error
    


async def get_hardware_description(series, base_feature, adon_feature):
    """
    Generate complete hardware description from provided specifications.
    
    Args:
        series: Hardware series
        base_feature: Dictionary of base features
        adon_feature: Dictionary of additional features
        
    Returns:
        Formatted hardware description string
    """
    try:
        # Start with the series
        desc_parts = [f"series - {str(series)}"]
        # Append base features
        for key, value in base_feature.items():
            desc_parts.append(f"{key} - {value['optionCode']}")

        # Append additional (addon) features
        for key, value in adon_feature.items():
            desc_parts.append(f"{key} - {value['optionCode']}")

        desc = " X ".join(desc_parts)

        return desc

    except Exception as error:
        print("get_hardware_description::", error)
        raise error

if __name__ == "__main__":
    x = {"base_feature":{"inputFeatures":{"width":{"unit":"mm","value":"543"},"height":{"unit":"mm","value":"786"}},"selectedFeatures":{"gauge":{"desc":"18ga","endInMM":None,"startInMM":None,"optionCode":"18ga","availabilityCriteria":[{"frame-type":"Masonry Frames","seriesCode":"M-Series Masonry Frames"},{"frame-type":"Drywall Frames for 1 3/4” Thick Doors","seriesCode":"DW-Sereies Drywall Frames"},{"seriesCode":"D-Series Doors"},{"seriesCode":"E-Series Doors"},{"seriesCode":"TRR-Series Doors"},{"seriesCode":"Panels"},{"frame-type":"Drywall Frames for 1 3/8” Thick Doors","seriesCode":"DW-Sereies Drywall Frames"}]},"width":{"desc":"34 inch to 36 inch","endInMM":914.4,"startInMM":863.6,"optionCode":"34 inch to 36 inch","availabilityCriteria":[{"elevation":"standard 6 panel","seriesCode":"E-Series Doors"},{"elevation":"1, 2 or 8 panel design","seriesCode":"E-Series Doors"}]},"height":{"desc":"80 inch to 84 inch","endInMM":2133.6,"startInMM":2032,"optionCode":"80 inch to 84 inch","availabilityCriteria":[{"elevation":"narrow panel","seriesCode":"E-Series Doors"},{"elevation":"standard 6 panel","seriesCode":"E-Series Doors"},{"elevation":"1, 2 or 8 panel design","seriesCode":"E-Series Doors"}]},"elevation":{"desc":"standard 6 panel","endInMM":None,"startInMM":None,"optionCode":"standard 6 panel","availabilityCriteria":[{"seriesCode":"E-Series Doors"}]}}},"adon_feature":{"Lock Preps":{"Deadlocks(DL)":{"option":{"desc":"Deadlocks(DL)","optionCode":"Deadlocks(DL)","availabilityCriteria":[{"seriesCode":"D-Series Doors"},{"seriesCode":"E-Series Doors"},{"seriesCode":"H-Series Steel Stiffened Doors"},{"seriesCode":"TRR-Series Doors"}]},"quantity":1}},"Panic Preps":{"Surface Vertical Rod(SVRP)":{"option":{"desc":"Surface Vertical Rod(SVRP)","optionCode":"Surface Vertical Rod(SVRP)","availabilityCriteria":[{"seriesCode":"D-Series Doors"},{"seriesCode":"E-Series Doors"},{"seriesCode":"H-Series Steel Stiffened Doors"},{"seriesCode":"TRR-Series Doors"}]},"quantity":1},"Concealed Vertical RodPanic (CVRP)":{"option":{"desc":"Concealed Vertical RodPanic (CVRP)","optionCode":"Concealed Vertical RodPanic (CVRP)","availabilityCriteria":[{"seriesCode":"E-Series Doors"},{"seriesCode":"TRR-Se ries Doors"}]},"quantity":1}}}}
    adon_opening_fields = {
        "hand": "LH-DA",
        "door_type": "single"
    }
    y = {"base_feature":{"inputFeatures":{"rebate_width":{"unit":"mm","value":"13"},"rebate_height":{"unit":"mm","value":"132"}},"selectedFeatures":{"door_type":{"desc":"SINGLE DOORS","endInMM":None,"startInMM":None,"optionCode":"SINGLE DOORS","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]},"jamb_depth":{"desc":"5.75 inches JAMB","endInMM":None,"startInMM":None,"optionCode":"5.75 inches JAMB","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"}]},"rebate_width":{"desc":"24 inches","endInMM":609.6,"startInMM":609.6,"optionCode":"24 inches","availabilityCriteria":[{"door_type":"SINGLE DOORS","seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"door_type":"SINGLE DOORS","seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"door_type":"SINGLE DOORS","seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"door_type":"SINGLE DOORS","seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]},"rebate_height":{"desc":"80 inches","endInMM":2032,"startInMM":2032,"optionCode":"80 inches","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]}}},"adon_feature":{"Hinge Preps":{"4 inches Templated Hinge Prep":{"option":{"desc":"4 inches Templated Hinge Prep","optionCode":"4 inches Templated Hinge Prep","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]},"quantity":1}},"Anchor Options":{"0.375 x 5 inches Steel Lag Bolts (8 Bolts)":{"option":{"desc":"0.375 x 5 inches Steel Lag Bolts (8 Bolts)","optionCode":"0.375 x 5 inches Steel Lag Bolts (8 Bolts)","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]},"quantity":1}},"Profile Options & Specialty Frames":{"Single Rabbeted Frame (Minimum Jamb Depth = 4 inches)":{"option":{"desc":"Single Rabbeted Frame (Minimum Jamb Depth = 4 inches)","optionCode":"Single Rabbeted Frame (Minimum Jamb Depth = 4 inches)","availabilityCriteria":[{"seriesCode":"16 (0.53) Gauge KD Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Standard frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge KD Engineered frames for 1.75 Doors"},{"seriesCode":"16 (0.53) Gauge DW Engineered frames for 1.75 Doors"}]},"quantity":1}}}}

    d = asyncio.run(get_door_description(adon_opening_fields, "HM DOOR", "E-Series Doors", x["base_feature"], x["adon_feature"]))
    print("\n\ndoor description:: ", d)
    f = asyncio.run(get_frame_description(adon_opening_fields, "HM FRAME", "16 (0.53) Gauge KD Standard frames for 1.75 Doors", y["base_feature"], y["adon_feature"]))
    print("\n\nframe description:: ", f)
    z = {}
    series = ""
    h = asyncio.run(get_hardware_description(series, z["baseFeature"], z["adonFeature"]))
    print("\n\n hardware description:: ", h)

"""
This Module is responsible for seeding all of the master data into the DB.
"""

from sqlalchemy.orm import Session
from models import engine
from models.status import Status
from models.modules import Modules
from models.sub_modules import SubModules
from models.members import Members
from models.sections import Sections
from models.raw_materials import RawMaterials
from models.manufacturers import Manufacturers
from models.brands import Brands

# from models.charges import Charges
from models.note_templates import NoteTemplates
from models.project_materials import ProjectMaterials
from models.hardware_groups import HardwareGroups
from models.hardware_group_materials import HardwareGroupMaterials
from models.opening_schedules import OpeningSchedules
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.project_raw_materials import ProjectRawMaterials
from models.section_raw_materials import SectionRawMaterials
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.hardware_product_category import HardwareProductCategory

# from models.raw_material_type import RawMaterialType
from models.adon_opening_fields import AdonOpeningFields
from models.roles import Roles
from models.role_permissions import RolePermissions
from models.member_role import MemberRole
from models.task_status import TaskStatus

from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.opening_hardware_materials import OpeningHardwareMaterials
from utils.common import generate_uuid, extract_keywords
from utils.auth import hash_password
from loguru import logger
from models.schedule_installation_mapping import ScheduleInstallationMapping
from models.schedule_installation_mapping_comments import ScheduleInstallationMappingComments
from models.schedule_installation_mapping_component_data import ScheduleInstallationMappingComponentData
from models.project_installation_plan_docs import ProjectInstallationPlanDocs
from models.schedule_installation_mapping_activity import ScheduleInstallationMappingActivity
from models.schedule_installation_mapping_attachment import ScheduleInstallationMappingAttachment
from models.wo_assignee import WoAssignee
from models.change_order import ChangeOrder
from models.co_change_stats import CoChangeStats
from models.co_schedules import CoSchedules
from models.work_order import WorkOrder
from models.wo_schedules import WoSchedules
from models.wo_assignee_time_log import WoAssigneeTimeLog
from models.change_order_status_logs import ChangeOrderStatusLogs
from models.change_order_docs import ChangeOrderDocs

# from app.database.models import Sheet, Role, User
# from app.helper.auth_helper import bcrypt
# from schemas import UserStatus


class Seeder:
    """**Summary:**
    This Class is responsible for seeding all of the master data into the DB.
    """

    # CONSTANTS
    MANUFACTURERS = [{"name": "Allegion", "code": "Allegion"}, {"name": "ASSA ABLOY", "code": "ASSA ABLOY"}, {"name": "Diamond", "code": "Diamond"}, {"name": "KNC", "code": "KNC"}]
    BRANDS = {
        "Allegion": [
            {
                "name": "GJ",
                "code": "GJ",
            },
            {
                "name": "LCN",
                "code": "LCN",
            },
            {
                "name": "Zero",
                "code": "Zero",
            },
        ],
        "ASSA ABLOY": [
            {
                "name": "Baron & Fleming",
                "code": "Baron & Fleming",
            }
        ]
    }
    STATUS_CATEGORIES = ["BID_STATUS", "PROJECT_STATUS"]
    STATUS = {
        "PROJECT_STATUS": ["Pending", "In Progress", "Done", "Failed", "Dropped"],
        "BID_STATUS": [
            "Await Bid",
            "Bid Success",
            "Bid Failed",
            "Sent",
            "Estimating",
            "Wait for approval",
        ],
    }
    MODULES = [
        {
            "name": "Permission Management",
            "label": "Permission Management",
            "sort_order": 1,
            "is_active": False,
        },
        {
            "name": "Task Management",
            "label": "Task Management",
            "sort_order": 2,
            "is_active": False,
        },
        {
            "name": "Member Management",
            "label": "Member Management",
            "sort_order": 3,
            "is_active": True
        },
        {
            "name": "Client Management",
            "label": "Client Management",
            "sort_order": 4,
            "is_active": True
        },
        {
            "name": "Project Management",
            "label": "Project Management",
            "sort_order": 5,
            "is_active": True
        },
        {
            "name": "Estimating Project Management",
            "label": "Estimating Project Management",
            "sort_order": 5,
            "is_active": True
        },
        {
            "name": "Finance Summary",
            "label": "Finance Summary",
            "sort_order": 6,
            "is_active": True,
        },
        {
            "name": "Order Management",
            "label": "Order Management",
            "sort_order": 7,
            "is_active": True,
        },
        {
            "name": "Installation Management",
            "label": "Installation Management",
            "sort_order": 8,
            "is_active": True,
        }
    ]
    SUB_MODULES = {
        "Permission Management": [
            {
                "name": "Role List",
                "label": "Role List",
                "sort_order": 1,
                "is_active": True,
            },
            {
                "name": "Module List",
                "label": "Module List",
                "sort_order": 2,
                "is_active": True,
            },
        ],
        "Task Management": [
            {
                "name": "Task List",
                "label": "Task List",
                "sort_order": 1,
                "is_active": True,
            }
        ],
        "Member Management": [
            {
                "name": "Member List",
                "label": "Member List",
                "sort_order": 1,
                "is_active": True,
            }
        ],
        "Client Management": [
            {
                "name": "Client List",
                "label": "Client List",
                "sort_order": 1,
                "is_active": True,
            },
            {
                "name": "Client Overview",
                "label": "Client Overview",
                "sort_order": 2,
                "is_active": True,
            },
        ],
        "Project Management": [
            {
                "name": "Project List",
                "label": "Projects",
                "sort_order": 1,
                "is_active": True,
            },
            {
                "name": "Project Overview",
                "label": "Project Overview",
                "sort_order": 2,
                "is_active": True,
            },
            {
                "name": "Tasks",
                "label": "Tasks",
                "sort_order": 3,
                "is_active": True
            },
            {
                "name": "Door & Frame List",
                "label": "Door & Frame List",
                "sort_order": 4,
                "is_active": True,
            },
            {
                "name": "Hardware Group",
                "label": "Hardware List",
                "sort_order": 5,
                "is_active": True,
            },
            {
                "name": "Opening Schedule",
                "label": "Opening Schedule",
                "sort_order": 6,
                "is_active": True,
            },
            {
                "name": "Hardware Schedule",
                "label": "Hardware Schedule",
                "sort_order": 7,
                "is_active": True,
            },
            {
                "name": "Finance Summary",
                "label": "Finance Summary",
                "sort_order": 8,
                "is_active": True,
            },
            {
                "name": "Order Management",
                "label": "Order Management",
                "sort_order": 9,
                "is_active": True,
            },
            {
                "name": "Installation Management",
                "label": "Installation Management",
                "sort_order": 10,
                "is_active": True,
            },
            {
                "name": "Change Order Management",
                "label": "Change Order Management",
                "sort_order": 11,
                "is_active": True,
            },
            {
                "name": "Request Management",
                "label": "Request Management",
                "sort_order": 12,
                "is_active": True,
            },
            {
                "name": "PO Management",
                "label": "PO Management",
                "sort_order": 13,
                "is_active": True,
            },
            {
                "name": "Shipping",
                "label": "Shipping",
                "sort_order": 14,
                "is_active": True,
            },
            {
                "name": "Financial Data",
                "label": "Financial Data",
                "sort_order": 15,
                "is_active": True,
            },
            {
                "name": "Files", 
                "label": "Files", 
                "sort_order": 16, 
                "is_active": True
            }
        ],
        "Estimating Project Management": [
            {
                "name": "Estimating Project List",
                "label": "Projects",
                "sort_order": 1,
                "is_active": True,
            },
            {
                "name": "Estimating Project Overview",
                "label": "Project Overview",
                "sort_order": 2,
                "is_active": True,
            },
            {
                "name": "Estimation Tasks",
                "label": "Tasks",
                "sort_order": 3,
                "is_active": True
            },
            {
                "name": "Estimation Door & Frame List",
                "label": "Door & Frame List",
                "sort_order": 4,
                "is_active": True,
            },
            {
                "name": "Estimation Hardware Group",
                "label": "Hardware List",
                "sort_order": 5,
                "is_active": True,
            },
            {
                "name": "Take off Sheet",
                "label": "Take off Sheet",
                "sort_order": 6,
                "is_active": True,
            },
            {
                "name": "Estimation",
                "label": "Estimation",
                "sort_order": 7,
                "is_active": True,
            },
            {
                "name": "Quotation",
                "label": "Quotation",
                "sort_order": 8,
                "is_active": True
            }
        ],
        "Order Management": [
            {
                "name": "Order List",
                "label": "Order List",
                "sort_order": 1,
                "is_active": True,
            }
        ],
        "Finance Summary": [
            {
                "name": "Finance Overview",
                "label": "Finance Overview",
                "sort_order": 1,
                "is_active": True,
            }
        ],
        "Installation Management": [
            {
                "name": "Installation List",
                "label": "Installation List",
                "sort_order": 1,
                "is_active": True,
            },
            {
                "name": "Installation Overview",
                "label": "Installation Overview",
                "sort_order": 2,
                "is_active": True,
            }
        ]
    }

    ROLE = [
        {
            "name": "Admin",
            "is_active": True
        },
        {
            "name": "Chief Estimator",
            "is_active": True
        },
        {
            "name": "Estimator",
            "is_active": True
        },
        {
            "name": "Chief Project Manager",
            "is_active": True
        },
        {
            "name": "Project Manager",
            "is_active": True
        },
        {
            "name": "Hardware Consultant",
            "is_active": True
        },
        {
            "name": "Door Consultant",
            "is_active": True
        },
        {
            "name": "Accountant",
            "is_active": True
        },
        {
            "name": "Purchase Manager",
            "is_active": True
        },
        {
            "name": "Receiving Personal",
            "is_active": True
        },
        {
            "name": "Shipping Personal",
            "is_active": True
        },
        {
            "name": "Installation Personal",
            "is_active": True
        }
    ]

    ROLE_PERMISSION = {
        "Admin": [
            {
                "sub_module": "Role List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Module List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },

            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Task List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Client List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Client Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Estimating Project List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Estimating Project Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Take off Sheet",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Estimation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Quotation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Estimation Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator", "Estimator"]
            },
            {
                "sub_module": "Hardware Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Estimation Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Estimation Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Opening Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Finance Summary",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Project Manager", "Accountant"]
            },
            {
                "sub_module": "Installation Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Project Manager", "Installation Personal"]
            },
            {
                "sub_module": "Change Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Request Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "PO Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Shipping",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Financial Data",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Files",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Admin", "Chief Project Manager", "Chief Estimator", "Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Estimator", "Receiving Personal", "Shipping Personal"]
            },
        ],
        "Chief Estimator":[
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Client List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": []
            },
            {
                "sub_module": "Client Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": []
            },
            {
                "sub_module": "Estimating Project List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Estimating Project Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Estimation Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator", "Estimator"]
            },
            {
                "sub_module": "Take off Sheet",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Estimation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Quotation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Estimation Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
            {
                "sub_module": "Estimation Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator","Estimator"]
            },
        ],
        "Estimator":[
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimating Project List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimating Project Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimation Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Estimator", "Estimator"]
            },
            {
                "sub_module": "Take off Sheet",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Quotation",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimation Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Estimator"]
            },
            {
                "sub_module": "Estimation Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Estimator"]
            },
        ],
        "Chief Project Manager":[
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Client List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": []
            },
            {
                "sub_module": "Client Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": []
            },
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Opening Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Finance Summary",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager", "Project Manager", "Accountant"]
            },
            {
                "sub_module": "Installation Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager", "Project Manager", "Installation Personal"]
            },
            {
                "sub_module": "Change Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Financial Data",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Files",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
        ],
        "Project Manager": [
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal", "Installation Personal"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Opening Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Finance Summary",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Accountant"]
            },
            {
                "sub_module": "Installation Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Installation Personal"]
            },
            {
                "sub_module": "Financial Data",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Files",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Project Manager", "Door Consultant", "Accountant", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            }
        ],
        "Door Consultant":[
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Schedule",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Hardware Group",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Opening Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Door Consultant"]
            },
            {
                "sub_module": "Files",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Door Consultant"]
            }
        ],
        "Hardware Consultant":[
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Hardware Schedule",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Hardware Group",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Door & Frame List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Opening Schedule",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Hardware Consultant"]
            },
            {
                "sub_module": "Files",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Hardware Consultant"]
            }
        ],
        "Accountant":[
            {
                "sub_module": "Member List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Accountant"]
            },
            {
                "sub_module": "Project List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Accountant"]
            },
            {
                "sub_module": "Project Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Accountant"]
            },
            {
                "sub_module": "Tasks",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Chief Project Manager","Door Consultant", "Accountant", "Project Manager", "Hardware Consultant", "Purchase Manager", "Receiving Personal", "Shipping Personal"]
            },
            {
                "sub_module": "Order Management",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Accountant"]
            },
            {
                "sub_module": "Finance Summary",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Accountant"]
            },
            {
                "sub_module": "Financial Data",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Accountant"]
            },
        ],
        "Purchase Manager":[
            {
                "sub_module": "Order List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Purchase Manager"]
            }
        ],
        "Receiving Personal":[
            {
                "sub_module": "Order List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Receiving Personal"]
            }
        ],
        "Shipping Personal":[
            {
                "sub_module": "Order List",
                "is_read": True,
                "is_write": True,
                "is_delete": True,
                "allowed_roles": ["Shipping Personal"]
            }
        ],
        "Installation Personal":[
            {
                "sub_module": "Installation List",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Installation Personal"]
            },
            {
                "sub_module": "Installation Overview",
                "is_read": True,
                "is_write": False,
                "is_delete": False,
                "allowed_roles": ["Installation Personal"]
            }
        ]
    }

    SUPER_ADMIN = {
        "first_name": "Alok",
        "last_name": "Das",
        "phone": "35646464",
        "email": "alan@ogmaconceptions.com",
        "password": hash_password("password"),
        "is_super_admin": True,
        "permission": "Admin",
    }

    SECTIONS = [
        {
            "name": "Hollow Metal",
            "code": "HM",
            "item_number": "001",
            "sort_order": 1,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
        {
            "name": "Wood",
            "code": "WD",
            "item_number": "002",
            "sort_order": 2,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
        {
            "name": "Stainless Steel",
            "code": "SS",
            "item_number": "003",
            "sort_order": 3,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
        {
            "name": "Sound Transmission",
            "code": "ST",
            "item_number": "004",
            "sort_order": 4,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
        {
            "name": "Blast",
            "code": "BD",
            "item_number": "005",
            "sort_order": 5,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": False,
        },
        {
            "name": "Mixed",
            "code": "MXD",
            "item_number": "006",
            "sort_order": 6,
            "is_door_frame": True,
            "is_hwd": False,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
        {
            "name": "Installation",
            "code": "INST",
            "item_number": "007",
            "sort_order": 7,
            "is_door_frame": False,
            "is_hwd": False,
            "is_installation": True,
            "default_section": False,
            "has_pricebook": False,
        },
        {
            "name": "Hardware",
            "code": "HWD",
            "item_number": "008",
            "sort_order": 8,
            "is_door_frame": False,
            "is_hwd": True,
            "is_installation": False,
            "default_section": False,
            "has_pricebook": True,
        },
    ]
    RAW_MATERILS = [
        {
            "item_number": "0010",
            "code": "HMD",
            "name": "Hollow Metal Door",
            "sort_order": 1,
        },
        {
            "item_number": "0011",
            "code": "HMF",
            "name": "Hollow Metal Frame",
            "sort_order": 2,
        },
        {
            "item_number": "0020",
            "code": "WDD",
            "name": "Wood Door",
            "sort_order": 3,
        },
        {
            "item_number": "0021",
            "code": "WDF",
            "name": "Wood Frame",
            "sort_order": 4,
        },
        {
            "item_number": "0030",
            "code": "SSD",
            "name": "Stainless Steel Door",
            "sort_order": 5,
        },
        {
            "item_number": "0031",
            "code": "SSF",
            "name": "Stainless Steel Frame",
            "sort_order": 6,
        },
        {
            "item_number": "0040",
            "code": "STD",
            "name": "Sound Transmission Door",
            "sort_order": 7,
        },
        {
            "item_number": "0041",
            "code": "STF",
            "name": "Sound Transmission Frame",
            "sort_order": 8,
        },
        {
            "item_number": "0051",
            "code": "BD",
            "name": "Blast Door",
            "sort_order": 9,
        },
        {
            "item_number": "0050",
            "code": "BF",
            "name": "Blast Frame",
            "sort_order": 10,
        },
        {
            "item_number": "0070",
            "code": "INST",
            "name": "Installation",
            "sort_order": 11
        },
        {
            "item_number": "0080",
            "code": "HWD",
            "name": "Hardware",
            "sort_order": 12
        }
    ]
    SECTION_RAW_MATERILS = {
        "HM": ["HMD","HMF"],
        "WD": ["WDD","WDF"],
        "SS": ["SSD","SSF"],
        "ST": ["STD","STF"],
        "MXD": ["HMD","HMF","WDD","WDF","SSD","SSF","STD","STF"],
        "INST": ["INST"],
        "HWD": ["HWD"],
        "BD": ["BD", "BF"]
    }

    
    NOTE_TEMPLATES = [
        {
            "name": "Quotation is valid for 30 days",
            "desc": "Quotation is valid for 30 days",
        },
        {
            "name": "Pricing is based on Door Schedule",
            "desc": "Pricing is based on Door Schedule and Dwg A2.1",
        },
        {"name": "No Returns", "desc": "No Returns will be accepted"},
        {"name": "All Estimations are final", "desc": "All Estimations are final"},
        {
            "name": "Please Contact us for any questions",
            "desc": "Please Contact us for any questions",
        },
        {"name": "Flexible Strip Doors", "desc": "Flexible Strip Doors"},
    ]

    ADON_FIELDS = [
        {
            "name": "door_type",
            "desc": "Door Type",
            "search_keywords": "door type",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "TAKE_OFF_SHEET,OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 3,
            "rule": None
        },
        {
            "name": "door_catalog",
            "desc": "Door Catalog",
            "search_keywords": "door catalog",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 1,
            "rule": None
        },
        {
            "name": "door_series",
            "desc": "Door Series",
            "search_keywords": "series",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 2,
            "rule": None
        },
        {
            "name": "frame_catalog",
            "desc": "Frame Catalog",
            "search_keywords": "frame catalog",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 1,
            "rule": None
        },
        {
            "name": "frame_series",
            "desc": "Frame Series",
            "search_keywords": "series",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 2,
            "rule": None
        },
        {
            "name": "swing",
            "desc": "Swing",
            "search_keywords": "swing,hand",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "TAKE_OFF_SHEET,OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "profile",
            "desc": "Profile",
            "search_keywords": "profile",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "jamb_depth",
            "desc": "Jamb Depth",
            "search_keywords": "jamb",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 4,
            "rule": None
        },
        {
            "name": "gauge",
            "desc": "Gauge",
            "search_keywords": "gauge",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": True,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 5,
            "rule": None
        },
        {
            "name": "material",
            "desc": "Material",
            "search_keywords": "material",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "welding",
            "desc": "Welding",
            "search_keywords": "welding",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "strike_jamb",
            "desc": "Strike Jamb",
            "search_keywords": "strike,jamb",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "hing_jamb",
            "desc": "Hing Jamb",
            "search_keywords": "hing,jamb",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "head_jamb",
            "desc": "Head Jamb",
            "search_keywords": "head,face,jamb",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "width",
            "desc": "Width",
            "search_keywords": "width",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": True,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 7,
            "rule": None
        },
        {
            "name": "height",
            "desc": "Height",
            "search_keywords": "height",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": False,
            "is_door_data": True,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 6,
            "rule": None
        },
        {
            "name": "door_thickness",
            "desc": "Door Thickness",
            "search_keywords": "thickness",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "anchor",
            "desc": "Anchor",
            "search_keywords": "anchor",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "fire_label",
            "desc": "Fire Label",
            "search_keywords": "fire,metal label,mylar label",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": True,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "core",
            "desc": "Core",
            "search_keywords": "core",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "door_finish",
            "desc": "Door Finish",
            "search_keywords": "finish",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "astragal",
            "desc": "Astragal",
            "search_keywords": "astragal",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "closers",
            "desc": "Closers",
            "search_keywords": "closer",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "door_louver",
            "desc": "Door Louver",
            "search_keywords": "louver",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "door_conduit",
            "desc": "Door Conduit",
            "search_keywords": "conduit",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "door_edge",
            "desc": "Door Edge",
            "search_keywords": "edge",
            "has_price_dependancy": True,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": True,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": False,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "hdwe_heading",
            "desc": "HDWE Heading",
            "search_keywords": "heading",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 1,
            "rule": None
        },
        {
            "name": "hinges",
            "desc": "Hinges",
            "search_keywords": "hinges",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 2,
            "rule": None
        },
        {
            "name": "lock",
            "desc": "Lock #",
            "search_keywords": "lock",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 3,
            "rule": None
        },
        {
            "name": "strike_type",
            "desc": "Strike Type",
            "search_keywords": "strike",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 4,
            "rule": None
        },
        {
            "name": "strike_location",
            "desc": "Strike Location",
            "search_keywords": "strike,strike_location,strike location",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 5,
            "rule": None
        },
        {
            "name": "rescue_hardware",
            "desc": "Rescue Hardware",
            "search_keywords": "rescue",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 6,
            "rule": None
        },
        {
            "name": "maglock_reinf",
            "desc": "Maglock Reinf",
            "search_keywords": "maglock",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 7,
            "rule": None
        },
        {
            "name": "coordinator_reinf",
            "desc": "Coordinator Reinf.",
            "search_keywords": "coordinator",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 8,
            "rule": None
        },
        {
            "name": "closer",
            "desc": "Closer",
            "search_keywords": "closer",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 9,
            "rule": None
        },
        {
            "name": "door_bolts_top",
            "desc": "Door Bolts Top",
            "search_keywords": "bolts top",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 10,
            "rule": None
        },
        {
            "name": "door_bolts_btm",
            "desc": "Door Bolts Btm.",
            "search_keywords": "bolts bottom",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 11,
            "rule": None
        },
        {
            "name": "dr_position_switch",
            "desc": "DR Position Switch",
            "search_keywords": "position switch",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 12,
            "rule": None
        },
        {
            "name": "conc_oh_stop",
            "desc": "Conc. OH Stop",
            "search_keywords": "overhead stop",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 13,
            "rule": None
        },
        {
            "name": "fr_guard_dr_edge",
            "desc": "FR Guard / DR Edge",
            "search_keywords": "guard edge",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 14,
            "rule": None
        },
        {
            "name": "concealed_door_btm",
            "desc": "Concealed Door Btm",
            "search_keywords": "concealed bottom",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 15,
            "rule": None
        },
        {
            "name": "power_transfer",
            "desc": "Power Transfer",
            "search_keywords": "power transfer",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 16,
            "rule": None
        },
        {
            "name": "hinge_location_on_frame",
            "desc": "Hinge Location on Frame",
            "search_keywords": "hinge location",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 17,
            "rule": None
        },
        {
            "name": "access_cut_out",
            "desc": "Access Cut Out",
            "search_keywords": "cut out",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 18,
            "rule": None
        },
        {
            "name": "run_conduit",
            "desc": "Run Conduit",
            "search_keywords": "conduit",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 19,
            "rule": None
        },
        {
            "name": "electrical_back_boxes",
            "desc": "Electrical Back Boxes",
            "search_keywords": "back boxes",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 20,
            "rule": None
        },
        {
            "name": "misc",
            "desc": "Misc",
            "search_keywords": "miscellaneous",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 21,
            "rule": None
        },
        {
            "name": "extra",
            "desc": "Extra",
            "search_keywords": "extra",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "DROPDOWN",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 22,
            "rule": None
        },
         {
            "name": "hardware_machining_sheets",
            "desc": "Hardware Machining Sheets",
            "search_keywords": "Hardware Machining Sheets",
            "has_price_dependancy": False,
            "is_active": True,
            "field_type": "FILE_UPLOAD",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": True,
            "is_opening_data": False,
            "sort_order": 23,
            "rule": None
        },
        {
            "name": "partition_type",
            "desc": "Partition Type",
            "search_keywords": "Partition Type",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": True,
            "sort_order": 9999,
            "rule": None
        },
        {
            "name": "partition_const",
            "desc": "Partition Constant",
            "search_keywords": "Partition Constant",
            "has_price_dependancy": False,
            "is_active": False,
            "field_type": "TEXT",
            "field_category": "OPENING_SCHEDULE",
            "is_adon_field": True,
            "is_door_data": False,
            "is_frame_data": False,
            "is_hw_data": False,
            "is_opening_data": True,
            "sort_order": 9999,
            "rule": None
        },
    ]
    
    ADON_FIELD_OPTIONS = {
        "door_type": [
            {
                "name": "single",
                "desc": "Single door",
                "search_keywords": "single",
                "is_default": False,
                "rule": {"door_width": {"delimiter": ",", "count": 0}},
            },
            {
                "name": "double",
                "desc": "double door",
                "search_keywords": "double",
                "is_default": False,
                "rule": {"door_width": {"delimiter": ",", "count": 1}},
            },
            {
                "name": "multi",
                "desc": "mutli door",
                "search_keywords": "mutli",
                "is_default": False,
                "rule": {"door_width": {"delimiter": ",", "count": 2}},
            },
        ],
        "swing": [
            {"name": "LH", "desc": "Left Hand", "rule": {"door_type": "single"}},
            {"name": "RH", "desc": "Right Hand", "rule": {"door_type": "single"}},
            {
                "name": "LHR",
                "desc": "Left Hand Reverse",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RHR",
                "desc": "Right Hand Reverse",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LH-DA",
                "desc": "Left Hand Double Acting",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RH-DA",
                "desc": "Right Hand Double Acting",
                "rule": {"door_type": "single"},
            },
            {"name": "CO", "desc": "Cased Open", "rule": {"door_type": "single"}},
            {
                "name": "LH-POCKET",
                "desc": "Left Hand, Pocket",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RH-POCKET",
                "desc": "Right Hand, Pocket",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LH-SLIDE",
                "desc": "Left Hand, Sliding",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RH-SLIDE",
                "desc": "Right Hand, Sliding",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LH-BIFOLD",
                "desc": "Left Hand, Bifold",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RH-BIFOLD",
                "desc": "Right Hand, Bifold",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LH/LH-COMM",
                "desc": "LH/LH, Communicating",
                "rule": {"door_type": "single"},
            },
            {
                "name": "RH/RH-COMM",
                "desc": "RH/RH, Communicating",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LH/RH-COMM",
                "desc": "LH/RH, Communicating",
                "rule": {"door_type": "single"},
            },
            {
                "name": "LHA/RH",
                "desc": "Left Hand Active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "LH/RHA",
                "desc": "Right Hand Active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "BHA",
                "desc": "Both Hands active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "LHRA/RHR",
                "desc": "Left Hand Reverse Active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "LHR/RHRA",
                "desc": "Right Hand Reverse Active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "BHRA",
                "desc": "Both Hands Reverse active",
                "rule": {"door_type": "double"},
            },
            {
                "name": "LHA-DA",
                "desc": "Left Hand Active, Double Acting",
                "rule": {"door_type": "double"},
            },
            {
                "name": "RHA-DA",
                "desc": "Right Hand Active, Double Acting",
                "rule": {"door_type": "double"},
            },
            {
                "name": "BHA-DA",
                "desc": "Both Hands Active, Double Acting",
                "rule": {"door_type": "double"},
            },
            {
                "name": "L-LHR",
                "desc": "Right Hand, Double Egress",
                "rule": {"door_type": "double"},
            },
            {
                "name": "R-RHR",
                "desc": "Left Hand, Double Egress",
                "rule": {"door_type": "double"},
            },
            {"name": "POCKET", "desc": "Pocket", "rule": {"door_type": "double"}},
            {"name": "BYPASS", "desc": "Bypass", "rule": {"door_type": "double"}},
            {"name": "BIFOLD", "desc": "Bifold", "rule": {"door_type": "double"}},
        ],
        "material": [
            {
                "name": "a40",
                "desc": "A40",
                "is_default": True,
                "search_keywords": "a40",
                "rule": {},
            },
            {
                "name": "g90",
                "desc": "G90",
                "is_default": False,
                "search_keywords": "g90",
                "rule": {},
            }
        ],
        "door_finish": [
            {
                "name": "ptbo",
                "desc": "Paint by Others",
                "search_keywords": "ptbo,Paint by Others",
                "is_default": True,
                "rule": {},
            },
            {
                "name": "plam",
                "desc": "PLAM",
                "search_keywords": "plam",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "veneer",
                "desc": "VENEER",
                "search_keywords": "veneer",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "stainless_steel",
                "desc": "Stainless Steel",
                "search_keywords": "stainless steel",
                "is_default": False,
                "rule": {},
            }
        ],
        "astragal": [
            {
                "name": "flat",
                "desc": "Flat Affixed",
                "search_keywords": "flat welded",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "flat_welded",
                "desc": "Flat Welded",
                "search_keywords": "flat welded",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "z",
                "desc": "Z Affixed",
                "search_keywords": "z Affixed",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "z_welded",
                "desc": "Z Welded",
                "search_keywords": "z welded",
                "is_default": False,
                "rule": {},
            }
        ],
        "extra": [
            {
                "name": "yes",
                "desc": "Yes",
                "search_keywords": "yes",
                "is_default": False,
                "rule": {},
            },
            {
                "name": "no",
                "desc": "No",
                "search_keywords": "no",
                "is_default": False,
                "rule": {},
            }
        ]
    }

    TASK_STATUS = ["To Do", "In Progress", "Completed"]

    CATALOG_MAPPING = {
        "Allegion": [
            {
                "GJ": ["HWD"],
                "discount": [0.3],
                "has_data": [True]
            },
            {
                "Zero": ["HWD"],
                "discount": [0.3],
                "has_data": [False]
            },
            {
                "LCN": ["HWD"],
                "discount": [0.3],
                "has_data": [True]
            }
        ],
        "ASSA ABLOY":[
            {
                "Baron & Fleming": ["HMD","HMF"],
                "discount": [0.3,0.3],
                "has_data": [True,True]
            }
        ],
        "Diamond":[
            {
                "NA": ["HMD","HMF"],
                "discount": [0.3,0.3],
                "has_data": [True, True]
            }
        ],
        "KNC":[
            {
                "NA": ["HWD"],
                "discount": [0.3],
                "has_data": [True]
            }
        ]
    }
    #########################################################
    ####        OPENING SCHEDULE SEEDER DATA             ####
    #########################################################
    # OPENING_SCHEDULE_FIELDS = [
    #     "Opening Number(s)",
    #     "Qty",
    #     "Type",
    #     "Elevation",
    #     "Nominal Width",
    #     "Nominal Height",
    #     "Label",
    #     "Hand",
    #     "Degree of Opening",
    #     "Remarks",
    #     "To-From",
    #     "Loc-T/F-Loc",
    #     "Doors",
    #     "Frames",
    #     "Hardware",
    #     "Costing",
    #     "Package SKU",
    #     "Item Status",
    #     "Item Stage",
    #     "Item Hold",
    #     "Material List"
    # ]

    # OPENING_SCHEDULE_FIELD_MAPPING = { 
    #     "Doors": [
    #             "Door Catalog",
    #             "Door Type",
    #             "Lite Kit",
    #             "Louver",
    #             "Door Mat1",
    #             "Door Gauge",
    #             "Door Label",
    #             "Door Core",
    #             "Door Edge",
    #             "Door Top",
    #             "Door Bottom",
    #             "Door Finish",
    #             "Door Thickness",
    #             "Door Undercut",
    #             "Door Elev.",
    #             "Door Remarks",
    #             "Door Nomenclature"
    #         ],
    #     "Frames":[
    #             "Frame Catalog",
    #             "Frame Mat1",
    #             "Frame Mat2",
    #             "Frame Gauge",
    #             "Frame Label",
    #             "Frame Profile",
    #             "Frame Trim",
    #             "Frame Trim Mat1",
    #             "Frame Trim Mat2",
    #             "Frame Construction",
    #             "Frame Finish",
    #             "Frame Lining",
    #             "Facing (Jamb, Hd)",
    #             "Jamb Depth",
    #             "Anchor Type",
    #             "Anchor Qty",
    #             "Frame Remarks",
    #             "Section Num"
    #         ],
    #     "Hardware": [
    #         "Hardware Group",
    #         "Heading Num",
    #         "Key Set",
    #         "Bitting Num",
    #         "Horizontal Sched"
    #     ]
    # }
    HARDWARE_PRODUCT_CATEGORY_DATA = [
        "Hanging Device",
        "Standard Hinge",
        "Continuous Hinge",
        "Anchor Hinge",
        "Pivot",
        "Floor Closer",
        "Track / Hanger",
        "Roller Catch",
        "Securing Device",
        "Flush Bolt",
        "Surface Bolt",
        "Removable Mullion",
        "Lockset",
        "Latchset",
        "Dead Lock",
        "Exit Device",
        "Dummy tam",
        "Two Point Lock",
        "Three Point Lock",
        "Cylinder",
        "Keying",
        "Electric Strike",
        "Electronic Locking Device",
        "Cremone Lock",
        "Dutch Door Bolt",
        "Roller Latch",
        "Operating Trim",
        "Door Pull",
        "Push Plate",
        "Push Bar",
        "Pull Bar",
        "Pair Accessory",
        "Coordinator",
        "Carry Bar",
        "Astragal",
        "Closing Device",
        "Surface Closer",
        "Concealed Closer",
        "Mounting Bracket",
        "Electronic Closer",
        "Pneumatic Closer",
        "Protecive Flate",
        "Mop Plate",
        "Kick Plate",
        "Stretcher Plates",
        "Armor Plate",
        "Door Edge",
        "Lock Protector",
        "Stop / Holder",
        "Overhead Door Stop",
        "Overhead Door Holder",
        "Floor Door Stop",
        "Wall Door Stop",
        "Floor Door Holder",
        "Wall Door Holder",
        "Electro-Magnetic Holder",
        "Accessory",
        "Threshold",
        "Wetherstripping",
        "Gasketing",
        "Miscellaneous Item",
        "Door Silencer",
        "Room Number",
        "Room Name Plate",
        "Door Knocker",
        "Card Holder",
        "Letter Box Plate",
        "Smoke/Fire Detection Device",
        "Miscellaneous Hardware",
        "Lite Kit",
        "Louver Kit",
        "Other charge",
        "Labor",
    ]

    def start_seeding(self):
        """**Summary:**
        This will instantiate the object of the seeder class
        """
        try:
            # Create DB session
            db = Session(engine)

            # Call all seeding methods
            self.create_status(db)
            self.create_modules(db)
            self.create_roles(db)
            self.create_super_admin(db)
            self.create_manufacturers(db)
            self.create_sections(db)
            self.create_raw_materials(db)
            self.create_note_templates(db)
            self.create_adon_opening_fileds(db)
            self.create_task_status(db)
            self.create_catalog_mapping(db)
            self.create_master_categories(db)
            # Close the db connection
            db.close()
        except Exception as error:
            logger.exception("Seeder:: error - " + str(error))
            raise error

    def create_status(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of different status,
        along with its respective category.

        **Args:**
            db (Session): db session referance
        """
        try:
            for status_category in self.STATUS_CATEGORIES:
                current_category_status = self.STATUS[status_category]
                for current_status in current_category_status:
                    # Check if the same data already exists in the table
                    if (
                        not db.query(Status)
                        .filter_by(type=current_status, category=status_category)
                        .first()
                    ):
                        # Create a new status object and add it to the db
                        new_status = Status(
                            id=generate_uuid(),
                            type=current_status,
                            category=status_category,
                        )
                        db.add(new_status)
            # Commit the changes to the database
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_status:: error - " + str(error))
            raise error

    def create_role_permission(self, db: Session, role_name, role_id):
        """**Summary:**
        This method is responsible for inserting the master data of different sub modules.

        **Args:**
            db (Session):  db session referance
            module_name (String): module name for which we want to insert sub modules
            module_id (String): module Id for which we want to insert sub modules
        """
        print("Creating Member permission::::")
        try:
            if role_name in self.ROLE_PERMISSION:
                current_role_permission = self.ROLE_PERMISSION[role_name]
                for role_sub_module in current_role_permission:

                    # Check if the same data already exists in the table
                    sub_module_data = (
                        db.query(SubModules)
                        .filter_by(name=role_sub_module["sub_module"])
                        .first()
                    )

                    if sub_module_data:
                        role_perm_data = (
                            db.query(RolePermissions)
                            .filter_by(
                                role_id=role_id, sub_module_id=sub_module_data.id
                            )
                            .first()
                        )
                        if (
                            not role_perm_data
                        ):
                            # Create a new sub module object and add it to the db
                            new_role_permission_id = generate_uuid()
                            role_sub_module["id"] = new_role_permission_id
                            role_sub_module["role_id"] = role_id
                            role_sub_module["sub_module_id"] = sub_module_data.id
                            del role_sub_module["sub_module"]

                            new_role_permision = RolePermissions(
                                **role_sub_module
                            )
                            db.add(new_role_permision)
                        else:
                            del role_sub_module["sub_module"]
                            for key, value in role_sub_module.items():
                                setattr(role_perm_data, key, value)
                        # Commit the changes to the database
                        db.commit()
        except Exception as error:
            logger.exception("Seeder.create_role_permission:: error - " + str(error))
            raise error

    def create_roles(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of different sub modules.

        **Args:**
            db (Session):  db session referance
            module_name (String): module name for which we want to insert sub modules
            module_id (String): module Id for which we want to insert sub modules
        """
        try:
            for role_data in self.ROLE:
                print(role_data["name"])
                # Check if the same data already exists in the table
                existing_role_data = (
                    db.query(Roles).filter_by(name=role_data["name"]).first()
                )
                if not existing_role_data:

                    # Create a new sub module object and add it to the db
                    new__role_id = generate_uuid()
                    role_data["id"] = new__role_id
                    print("role_data:: ", role_data)
                    new_role = Roles(**role_data)
                    db.add(new_role)
                    db.flush()
                    role_id = new_role.id
                else:
                    role_id = existing_role_data.id
                    for key, value in role_data.items():
                        setattr(existing_role_data, key, value)
                # Commit the changes to the database
                db.commit()
                self.create_role_permission(
                    db, role_name=role_data["name"], role_id=role_id
                )
        except Exception as error:
            logger.exception("Seeder.create_roles:: error - " + str(error))
            raise error

    def create_sub_modules(self, db: Session, module_name, module_id):
        """**Summary:**
        This method is responsible for inserting the master data of different sub modules.

        **Args:**
            db (Session):  db session referance
            module_name (String): module name for which we want to insert sub modules
            module_id (String): module Id for which we want to insert sub modules
        """
        try:
            current_sub_modules = self.SUB_MODULES[module_name]

            for current_sub_module in current_sub_modules:
                # Check if the same data already exists in the table
                submodule_exists = db.query(SubModules).filter_by(name=current_sub_module["name"], module_id=module_id).first()
                if (
                    not submodule_exists
                ):
                    # Create a new sub module object and add it to the db
                    new__sub_module_id = generate_uuid()
                    current_sub_module["id"] = new__sub_module_id
                    current_sub_module["module_id"] = module_id

                    new_sub_module = SubModules(
                        **current_sub_module
                    )
                    db.add(new_sub_module)
                else:
                    for key, value in current_sub_module.items():
                        if hasattr(submodule_exists, key):
                            setattr(submodule_exists, key, value)
                db.commit()
        except Exception as error:
            logger.exception("Seeder.create_sub_modules:: error - " + str(error))
            raise error

    def create_modules(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of different modules,
        along with its respective submodules.

        **Args:**
            db (Session): db session referance
        """
        try:
            for module_data in self.MODULES:
                # Check if the same data already exists in the table
                module_exists = db.query(Modules).filter_by(name=module_data["name"]).first()
                if not module_exists:
                    # Create a new module object and add it to the db
                    new_module_id = generate_uuid()
                    module_data["id"] = new_module_id
                    new_module = Modules(**module_data)
                    db.add(new_module)
                    # create submodules for the current module
                    self.create_sub_modules(db, module_data["name"], new_module_id)
                    # Commit the changes to the database
                    db.commit()
                else:
                    # create submodules for the current module
                    self.create_sub_modules(db, module_data["name"], module_exists.id)
                    # Commit the changes to the database
                    db.commit()
        except Exception as error:
            logger.exception("Seeder.create_modules:: error - " + str(error))
            raise error

    def create_member_permission(self, db: Session, member_id, permission):
        """**Summary:**
        This method is responsible for inserting the master data of different member permissions.

        **Args:**
            db (Session): db session referance
            member_id (String): member Id for which we want to add the member permissions
            permission (String): module name for which we want to give access the current member
        """
        try:
            role_data = db.query(Roles).filter_by(name=permission).first()
            if role_data:
                # Check if the same data already exists in the table
                if (
                    not db.query(MemberRole)
                    .filter_by(
                        member_id=member_id,
                        role_id=role_data.id,
                    )
                    .first()
                ):
                    # Create a new member permission object and add it to the db
                    new_permission_id = generate_uuid()
                    new_member_permission = MemberRole(
                        id=new_permission_id,
                        member_id=member_id,
                        role_id=role_data.id,
                        active_role=True,
                    )
                    db.add(new_member_permission)
        except Exception as error:
            logger.exception("Seeder.create_member_permission:: error - " + str(error))
            raise error

    def create_super_admin(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of super admin,
        along with its respective member permissions.

        **Args:**
            db (Session): db session referance
        """
        try:
            new_user = self.SUPER_ADMIN.copy()
            permission = None
            if "permission" in new_user:
                permission = new_user["permission"]
                del new_user["permission"]
            # Check if the same data already exists in the table
            if not db.query(Members).filter_by(email=new_user["email"]).first():
                # Create a new member object and add it to the db
                new_member_id = generate_uuid()
                new_member = Members(
                    id=new_member_id,
                    first_name=new_user["first_name"],
                    last_name=new_user["last_name"],
                    email=new_user["email"],
                    phone=new_user["phone"],
                    password=new_user["password"],
                    is_super_admin=new_user["is_super_admin"],
                )
                db.add(new_member)
                if permission is not None:
                    # Add permission to the currnet user
                    self.create_member_permission(db, new_member_id, permission)
            # Commit the changes to the database
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_super_admin:: error - " + str(error))
            raise error

    def create_manufacturers(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all Manufaturers,
        along with its respective brands.

        **Args:**
            db (Session): db session referance
        """
        try:
            for manufacturer in self.MANUFACTURERS:
                current_manufacturer_id = None
                existing_manu = (
                    db.query(Manufacturers)
                    .filter(
                        Manufacturers.code == manufacturer["code"],
                        Manufacturers.is_deleted == False,
                    )
                    .first()
                )
                if not existing_manu:
                    new_manufeacturer = Manufacturers()
                    for key, value in manufacturer.items():
                        setattr(new_manufeacturer, key, value)
                    db.add(new_manufeacturer)
                    db.flush()
                    db.commit()
                    current_manufacturer_id = str(new_manufeacturer.id)
                else:
                    current_manufacturer_id = str(existing_manu.id)
                if manufacturer["name"] in self.BRANDS:
                    for brand in self.BRANDS[manufacturer["name"]]:
                        if (
                            not db.query(Brands)
                            .filter(
                                Brands.code == brand["code"], Brands.is_deleted == False
                            )
                            .first()
                        ):
                            new_brand = Brands()
                            for key, value in brand.items():
                                setattr(new_brand, key, value)
                            new_brand.manufacturer_id = current_manufacturer_id
                            db.add(new_brand)
                        db.commit()
        except Exception as error:
            logger.exception("Seeder.create_manufacturers:: error - " + str(error))
            raise error

    def create_sections(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all Sections,

        **Args:**
            db (Session): db session referance
        """
        try:
            for section in self.SECTIONS:
                existing_section = (
                    db.query(Sections)
                    .filter(
                        Sections.name == section["name"], Sections.is_deleted == False
                    )
                    .first()
                )
                if (
                    not existing_section
                ):
                    new_section_id = generate_uuid()
                    section["id"] = new_section_id
                    new_section = Sections(**section)
                    db.add(new_section)
                else:
                    # Update the attributes of the existing client with the values from the client_data dictionary.
                    for key, value in section.items():
                        setattr(existing_section, key, value)
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_sections:: error - " + str(error))
            raise error

    def create_raw_materials(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all raw material,

        **Args:**
            db (Session): db session referance
        """
        try:
            for raw_material in self.RAW_MATERILS:
                existing_raw_material = (
                    db.query(RawMaterials)
                    .filter(RawMaterials.code == raw_material["code"])
                    .first()
                )
                if (
                    not existing_raw_material
                ):
                    new_raw_material_id = generate_uuid()
                    raw_material["id"] = new_raw_material_id
                    new_material = RawMaterials(**raw_material)
                    db.add(new_material)
                else:
                    for key, value in raw_material.items():
                        setattr(existing_raw_material, key, value)
            db.commit()
            for Sec_rw_mat in self.SECTION_RAW_MATERILS:
                section = (
                    db.query(Sections)
                    .filter(
                        Sections.code == Sec_rw_mat, Sections.is_deleted == False
                    )
                    .first()
                )
                # delete existing mappings
                (
                    db.query(SectionRawMaterials).filter(
                        SectionRawMaterials.section_id == section.id
                    )
                    .delete()
                )
                # collect acceptable mapping
                acceptable_mapping = (
                    db.query(RawMaterials).filter(
                        RawMaterials.code.in_(self.SECTION_RAW_MATERILS[Sec_rw_mat])
                    )
                    .all()
                )
                for mapping in acceptable_mapping:
                    map_data = {
                        "section_id": section.id,
                        "raw_material_id": mapping.id,
                    }
                    new_mapping_data = SectionRawMaterials(**map_data)
                    db.add(new_mapping_data)
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_raw_materials:: error - " + str(error))
            raise error

    def create_note_templates(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all Note Templates,

        **Args:**
            db (Session): db session referance
        """
        try:
            for note_template in self.NOTE_TEMPLATES:
                template_exists = (
                    db.query(NoteTemplates)
                    .filter(
                        NoteTemplates.name == note_template["name"],
                        NoteTemplates.is_deleted == False,
                    )
                    .first()
                )
                if not template_exists:
                    new_note_template = NoteTemplates(**note_template)
                    db.add(new_note_template)
                else:
                    template_exists.desc = note_template["desc"]
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_note_templates:: error - " + str(error))
            raise error

    def create_adon_opening_filed_options(self, adon_filed_id, field_name, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all adon opening filed options,

        **Args:**
            field_name(str): field name for which we want to insert options
            adon_filed_id(str): field id for which we want to insert options
            db (Session): db session referance
        """
        try:
            if field_name in self.ADON_FIELD_OPTIONS:
                for adon_filed_options in self.ADON_FIELD_OPTIONS[field_name]:
                    adon_filed_options["adon_opening_field_id"] = adon_filed_id
                    filed_option_exists = (
                        db.query(AdonOpeningFieldOptions)
                        .filter(
                            AdonOpeningFieldOptions.name == adon_filed_options["name"],
                            AdonOpeningFieldOptions.adon_opening_field_id == adon_filed_id,
                        )
                        .first()
                    )
                    if not filed_option_exists:
                        new_adon_filed_option = AdonOpeningFieldOptions(
                            **adon_filed_options
                        )
                        db.add(new_adon_filed_option)
                    else:
                        # filed_option_exists.desc = adon_filed_options["desc"]
                        # filed_option_exists.rule = adon_filed_options["rule"]
                        if "search_keywords" not in adon_filed_options:
                            adon_filed_options["search_keywords"] = adon_filed_options["desc"]
                        for key, value in adon_filed_options.items():
                            setattr(filed_option_exists, key, value)
                db.commit()
        except Exception as error:
            logger.exception(
                "Seeder.create_adon_opening_filed_options:: error - " + str(error)
            )
            raise error

    def create_adon_opening_fileds(self, db: Session):
        """**Summary:**
        This method is responsible for inserting the master data of all adon opening filed options,

        **Args:**
            db (Session): db session referance
        """
        try:
            for adon_fileds in self.ADON_FIELDS:
                filed_exists = (
                    db.query(AdonOpeningFields)
                    .filter(AdonOpeningFields.name == adon_fileds["name"])
                    .first()
                )
                if not filed_exists:
                    new_adon_filed = AdonOpeningFields(**adon_fileds)
                    db.add(new_adon_filed)
                    db.commit()
                    self.create_adon_opening_filed_options(
                        new_adon_filed.id, adon_fileds["name"], db
                    )
                else:
                    # filed_exists.desc = adon_fileds["desc"]
                    # filed_exists.search_keywords = adon_fileds["search_keywords"]
                    for key, value in adon_fileds.items():
                        setattr(filed_exists, key, value)
                    db.commit()
                    self.create_adon_opening_filed_options(
                        filed_exists.id, adon_fileds["name"], db
                    )
        except Exception as error:
            logger.exception(
                "Seeder.create_adon_opening_fileds:: error - " + str(error)
            )
            raise error

    def create_task_status(self, db: Session):
        try:
            # Add seed data to the session if not already present
            for status in self.TASK_STATUS:
                # Check if the status already exists
                if not db.query(TaskStatus).filter(TaskStatus.status == status).first():
                    task_status = TaskStatus(status=status)
                    db.add(task_status)
            # Commit the session to the database
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_task_status:: error - " + str(error))
        finally:
            # Close the session
            db.close()


            
    def create_catalog_mapping(self, db: Session):
        try:
            # Add seed data to the session if not already present
            for manufact in self.CATALOG_MAPPING.keys():
                manufact_data = (
                    db.query(Manufacturers).filter(Manufacturers.code == manufact).first()
                )
                if manufact_data:
                    for brnd in self.CATALOG_MAPPING[manufact]:
                        brnd_code = list(brnd.keys())[0]
                        if brnd_code == "NA":
                            acceptable_mapping = (
                                db.query(RawMaterials).filter(
                                    RawMaterials.code.in_(brnd[brnd_code])
                                )
                                .all()
                            )
                            for mapping in acceptable_mapping:
                                
                                old_mappings = (
                                    db.query(RawMaterialCatalogMapping).filter(
                                            RawMaterialCatalogMapping.raw_material_id == mapping.id,
                                            RawMaterialCatalogMapping.manufacturer_id == manufact_data.id,
                                            RawMaterialCatalogMapping.brand_id.is_(None)
                                        )
                                        .first()
                                )
                                if not old_mappings:
                                    map_data = {
                                        "manufacturer_id": manufact_data.id,
                                        "brand_id": None,
                                        "raw_material_id": mapping.id,
                                        "discount_percentage": brnd["discount"][brnd[brnd_code].index(mapping.code)],
                                        "has_data": brnd["has_data"][brnd[brnd_code].index(mapping.code)],
                                    }
                                    new_mapping_data = RawMaterialCatalogMapping(**map_data)
                                    db.add(new_mapping_data)
                                else:
                                    map_update_data = {
                                        "discount_percentage": brnd["discount"][brnd[brnd_code].index(mapping.code)],
                                        "has_data": brnd["has_data"][brnd[brnd_code].index(mapping.code)],
                                    }
                                    (
                                        db.query(RawMaterialCatalogMapping).filter(
                                            RawMaterialCatalogMapping.id == old_mappings.id
                                        )
                                        .update(map_update_data, synchronize_session=False)
                                    )
                        else:
                            brand_data = (
                                db.query(Brands).filter(Brands.code == brnd_code).first()
                            )
                            if brand_data:
                                # delete existing mappings
                                # (
                                #     db.query(RawMaterialCatalogMapping).filter(
                                #         RawMaterialCatalogMapping.manufacturer_id == manufact_data.id,
                                #         RawMaterialCatalogMapping.brand_id == brand_data.id
                                #     )
                                #     .delete()
                                # )

                                acceptable_mapping = (
                                    db.query(RawMaterials).filter(
                                        RawMaterials.code.in_(brnd[brnd_code])
                                    )
                                    .all()
                                )
                                
                                for mapping in acceptable_mapping:
                                    old_mappings = (
                                        db.query(RawMaterialCatalogMapping).filter(
                                                RawMaterialCatalogMapping.raw_material_id == mapping.id,
                                                RawMaterialCatalogMapping.manufacturer_id == manufact_data.id,
                                                RawMaterialCatalogMapping.brand_id == brand_data.id
                                            )
                                            .first()
                                    )
                                    if not old_mappings:
                                        map_data = {
                                            "manufacturer_id": manufact_data.id,
                                            "brand_id": brand_data.id,
                                            "raw_material_id": mapping.id,
                                            "discount_percentage": brnd["discount"][brnd[brnd_code].index(mapping.code)],
                                            "has_data": brnd["has_data"][brnd[brnd_code].index(mapping.code)],
                                        }
                                        new_mapping_data = RawMaterialCatalogMapping(**map_data)
                                        db.add(new_mapping_data)
                                    else:
                                        map_update_data = {
                                            "discount_percentage": brnd["discount"][brnd[brnd_code].index(mapping.code)],
                                            "has_data": brnd["has_data"][brnd[brnd_code].index(mapping.code)],
                                        }
                                        (
                                            db.query(RawMaterialCatalogMapping).filter(
                                                RawMaterialCatalogMapping.id == old_mappings.id
                                            )
                                            .update(map_update_data, synchronize_session=False)
                                        )
            # Commit the session to the database
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_catalog_mapping:: error - " + str(error))
        finally:
            # Close the session
            db.close()


    def create_master_categories(self, db: Session):
        """**Summary:**
        This method is responsible for creating master categories and their subcategories in the database.

        **Args:**
            db (Session): The database session reference.
        """
        try:
            # Add seed data to the session if not already present
            for category in self.HARDWARE_PRODUCT_CATEGORY_DATA:
                # Check if the status already exists
                existing_category = db.query(HardwareProductCategory).filter(HardwareProductCategory.name == category).first()
                if not existing_category:
                    new_category_data = {
                        "name": category,
                        "search_keywords": ",".join(elm for elm in extract_keywords(category))
                    }
                    new_category_data = HardwareProductCategory(**new_category_data)
                    db.add(new_category_data)
                    db.flush()
                
            # Commit the session to the database
            db.commit()
        except Exception as error:
            logger.exception("Seeder.create_master_categories:: error - " + str(error))
        finally:
            # Close the session
            db.close()

            

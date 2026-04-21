"""
This module containes all routes infos in a single place so that,
it will be easy to instansiate all the routes at once.
"""
from router import client_route
from router import project_route
from router import upload_tender_documents
from router import module_route
from router import sub_module_route
from router import member_route
from router import permission_route
from router import auth_route
from router import section_route
from router import take_off_sheet_route
from router import take_off_sheet_item_route
from router import charges_route
from router import take_off_sheet_estimation_route
from router import notes_route
from router import materials_route
from router import hardware_group_route
from router import manufacture_route
from router import brand_route
from router import quotation_route
from router import role_route
from router import task_route
from router import schedule_route
from router import opening_hardware_material_route
from router import opening_hardware_group_material_route
from router import opening_door_frame_materials_route
from router import  order_route
from router import shipping_route
from router import transfer_opening_route
from router import schedule_summary_route
from router import schedule_installation_route
from router import work_order_route
from router import change_order_route

class InitiateRouters:
    """
    This Class is responsible for initiating all avalables routes.
    """
    def __init__(self, app):
        """
        This method is responsible for initiating all avalables routes.
        """
        app.include_router(auth_route.router)
        app.include_router(client_route.router)
        app.include_router(project_route.router)
        app.include_router(upload_tender_documents.router)
        app.include_router(module_route.router)
        app.include_router(sub_module_route.router)
        app.include_router(member_route.router)
        app.include_router(permission_route.router)
        app.include_router(section_route.router)
        app.include_router(take_off_sheet_route.router)
        app.include_router(take_off_sheet_item_route.router)
        app.include_router(charges_route.router)
        app.include_router(take_off_sheet_estimation_route.router)
        app.include_router(notes_route.router)
        app.include_router(materials_route.router)
        app.include_router(hardware_group_route.router)
        app.include_router(manufacture_route.router)
        app.include_router(brand_route.router)
        app.include_router(quotation_route.router)
        app.include_router(role_route.router)
        app.include_router(task_route.router)
        app.include_router(schedule_route.router)
        app.include_router(opening_hardware_material_route.router)
        app.include_router(opening_hardware_group_material_route.router)
        app.include_router(opening_door_frame_materials_route.router)
        app.include_router(order_route.router)
        app.include_router(shipping_route.router)
        app.include_router(transfer_opening_route.router)
        app.include_router(schedule_summary_route.router)
        app.include_router(schedule_installation_route.router)
        app.include_router(work_order_route.router)
        app.include_router(change_order_route.router)
        

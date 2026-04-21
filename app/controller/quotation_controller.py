"""
This file contains all operations related to quotation.
"""
from jinja2 import Template
import os
from loguru import logger
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.members import Members
from models.project_raw_materials import ProjectRawMaterials
from models.quotation_revision import QuotationRevision
from repositories.common_repositories import get_total_adon_price
from sqlalchemy.orm import Session
from controller.take_off_sheet_estimation_controller import material_type_wise_estimated_price
from datetime import datetime
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.exc import SQLAlchemyError
import subprocess
from fastapi import HTTPException
from schemas.project_raw_material_schema import ProjectRawMaterial
from repositories.quotation_repositories import get_project_info, update_project, get_user_details, add_revision, generate_quotation_number, get_client_details, get_general_notes, check_for_empty_opening
from utils.common import upload_to_s3, delete_from_s3, download_from_s3, upload_path_to_s3, get_aws_full_path
from fastapi import UploadFile
import io
from typing import List, Optional
import math


def get_attr(obj, attr, default=""):
    return getattr(obj, attr, default) if obj and getattr(obj, attr) is not None else default


async def generate_quotation(db: Session, project_id: str, client_id: str, current_member: str):
    """
    Generate a quotation PDF for a project.
    """
    try:
        TAX_PERCENTAGE = os.environ.get("TAX")
        # File paths
        current_directory = os.path.dirname(os.path.abspath(__file__))
        root_directory = os.path.dirname(current_directory)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"quote_{timestamp}.pdf"
        file_path = os.path.join(root_directory, "generate", file_name)
        html_file_path = os.path.join(root_directory, "quotation/template", "quote_template.html")
        logo_file_path = os.path.join(root_directory, "quotation/template", "logo.png")

        # Cehck if the project has any empty opening
        empty_opening_openings = await check_for_empty_opening(db, project_id)
        if len(empty_opening_openings) > 0:
            # return response
            return JSONResponse(
                content={"message": f"Can't proceed with empty openings: ({','.join(elm['opening_number'] for elm in empty_opening_openings)})"},
                status_code=400
            )
        else:
            # Fetch project information
            project_info = await get_project_info(db, project_id)

            # Fetch user information
            member_info = await get_user_details(db, current_member.id)
            
            quotation_number = project_info.quotation_number
            if project_info.has_quotation == False:
                quotation_number = await generate_quotation_number(db, project_id)
                # Update Project table
                new_data = {"has_quotation": 1, "quotation_number": quotation_number}
                await update_project(db, project_id, new_data)
            
            # Add Revision
            generated_revision_number, quotation_revision_id = await add_revision(db, project_id, current_member)

            # Fetch client information
            client_info = await get_client_details(db, client_id)

            # Prepare rendering information
            rendering_info = {
                'project_id': get_attr(project_info, 'id', ""),
                'project_name': get_attr(project_info, 'project_name', ""),
                'project_code': get_attr(project_info, 'project_code', ""),
                'project_location': get_attr(project_info, 'project_location', ""),
                'member_name': get_attr(member_info, 'full_name', ""),
                'member_email': get_attr(member_info, 'email', ""),
                'member_phone': get_attr(member_info, 'phone', ""),
                'current_date': datetime.now().strftime("%d-%b-%Y"),
                'REV': generated_revision_number if generated_revision_number is not None else "",
                'quotation_number': quotation_number if quotation_number is not None else "",
                'client_name': get_attr(client_info, 'name', ""),
                'client_phone': get_attr(client_info, 'phone', ""),
                'client_contact_name': get_attr(client_info, 'contact_name', ""),
                'client_fax': get_attr(client_info, 'fax', "")
            }

            # Fetch general template information
            general_notes = await get_general_notes(db, project_id)
            rendering_info['general_notes'] = general_notes

            # Fetch estimation information
            response = await material_type_wise_estimated_price(db, project_id)

            rendering_info['estimation_info'] = response['data'] if response else []
            
            final_amount = 0
            final_base_amount = 0
            final_sell_amount = 0
            final_extended_sell_amount = 0
            if response:
                for data in response['data']:
                    final_amount = final_amount + data['final_amount']
                    final_base_amount = final_base_amount + data['final_base_amount']
                    final_sell_amount = final_sell_amount + data['final_sell_amount']
                    final_extended_sell_amount = final_extended_sell_amount + data['final_extended_sell_amount']

            total_estimation_info = {
                "final_amount": round(final_amount, 2), 
                "final_base_amount": round(final_base_amount, 2), 
                "final_sell_amount": round(final_sell_amount, 2),
                "final_extended_sell_amount": round(final_extended_sell_amount, 2)
                }
            
            project_take_off_sheet = db.query(ProjectTakeOffSheets.id).filter(ProjectTakeOffSheets.project_id == project_id).first()
            miscellaneous_price = await get_total_adon_price(db, project_take_off_sheet.id)
            
            rendering_info['estimated_item_count'] = 0 if response['data'] is None else len(response['data'])
            rendering_info['total_estimation_info'] = total_estimation_info
            rendering_info['logo_file_path'] = logo_file_path

            tax_amount = round((total_estimation_info['final_extended_sell_amount'] * float(TAX_PERCENTAGE)), 2)
            rendering_info['tax_amount'] = tax_amount
            rendering_info['miscellaneous_price'] = round(miscellaneous_price, 2)
            rendering_info['grand_total_amount'] = round(final_extended_sell_amount + tax_amount + miscellaneous_price, 2)

            # Fetch HTML template content
            with open(html_file_path, "r") as html_file:
                html_content = html_file.read()
            
            # Render HTML template with data
            template = Template(html_content)
            rendered_html = template.render(data=rendering_info)
            
            generate_directory = os.path.dirname(file_path)
            if not os.path.exists(generate_directory):
                os.makedirs(generate_directory, exist_ok=True)
            
            # Save the rendered HTML to a temporary file
            temp_html_path = os.path.join(generate_directory, f"temp_{timestamp}.html")
            with open(temp_html_path, "w") as temp_html_file:
                temp_html_file.write(rendered_html)
            
            # Generate PDF from HTML using WeasyPrint with --presentational-hint
            subprocess.run(["weasyprint", "--presentational-hint", temp_html_path, file_path], check=True)

            upload_path = f"generated_quotations/{project_id}"
            s3_file_path = await upload_path_to_s3(file_path, upload_path)

            # Query the database to find the QuotationRevision object with the specified ID
            quotation_revision = db.query(QuotationRevision).filter(QuotationRevision.id == quotation_revision_id).first()
            if quotation_revision:
                quotation_revision.file_path = s3_file_path
                db.commit()

            quotation_revision_dict = quotation_revision.to_dict
            quotation_revision_dict['file_path'] = get_aws_full_path(quotation_revision.file_path)
            
            # Check if the specified file exists, and if so, delete it to free up space or avoid conflicts
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Check if the temporary HTML file exists, and if so, delete it to clean up temporary files
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)

            # return response
            return JSONResponse(
                content={"data": quotation_revision_dict, "status": "success"}
            )

    except Exception as e:
        # Handle exceptions
        logger.exception(f"Error generating quotation: {e}")
        raise



async def update_project_raw_material(
    db: Session, 
    project_id: str, 
    project_raw_material_id: str, 
    request_data: ProjectRawMaterial, 
    current_member: Members
):
    try:
        request_data = request_data.model_dump(exclude_unset=True)
        # Fetch the existing raw material types for the specified project
        existing_project_raw_materials = (db.query(ProjectRawMaterials)
                    .filter(ProjectRawMaterials.project_id == project_id, 
                            ProjectRawMaterials.id == project_raw_material_id)
                    .all())
        
        if not existing_project_raw_materials:
            raise HTTPException(status_code=404, detail="Raw material type not found for the specified project.")
        
        # Update the fields for each raw material
        for material in existing_project_raw_materials:
            for key, value in request_data.items():
                if value is not None:
                    setattr(material, key, value)

        return {"message": "Data updated successfully.", "status": "success"}
    
    except HTTPException as e:
        db.rollback()
        logger.warning(f"HTTP error updating project raw material: {e.detail}")
        raise
    
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error updating project raw material: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the project raw material.")
    finally:
        # Commit the transaction
        db.commit()




async def get_project_quotations(
    db: Session, 
    project_id: str,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
):
    try:
        # Fetch all revisions for the given project_id
        query = (
            db.query(QuotationRevision)
            .filter(QuotationRevision.project_id == project_id)
            .order_by(QuotationRevision.revision_number.asc())
        )

        item_count = query.count()

        print("page", page)
        print("page_size", page_size)

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = item_count if item_count else 1
            page = 1

        revisions = query.all()

        # Calculate the total number of pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        # Convert revisions to a list of dictionaries
        response = []
        for revision in revisions:
            data = revision.to_dict 
            data['file_path'] = get_aws_full_path(revision.file_path)
            response.append(data)

        content = {
            "data": response,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

        # Return the response as a JSONResponse
        return JSONResponse(content=content)

    except SQLAlchemyError as e:
        # Log the exception
        logger.exception(f"Error fetching project quotations for project_id={project_id}: {e}")

        # Return an error response
        return JSONResponse(
            content={"error": "Failed to fetch project quotations.", "status": "failure"},
            status_code=500,
        )

    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error in get_project_quotations: {e}")

        # Return a generic error response
        return JSONResponse(
            content={"error": "An unexpected error occurred.", "status": "failure"},
            status_code=500,
        )

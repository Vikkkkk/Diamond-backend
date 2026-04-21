from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import Base
from utils.common import generate_uuid
import enum


class WorkOrderStatusEnum(enum.Enum):
    PENDING = 'PENDING'
    DISPATCHED = 'DISPATCHED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class WorkOrder(Base):
    __tablename__ = 'work_order'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_no = Column(String(100), unique=True)
    project_id = Column(String(36),default=None)
    wo_number = Column(String(100),default=None)
    wo_date = Column(DateTime)
    wo_status = Column(Enum(WorkOrderStatusEnum), default=WorkOrderStatusEnum.PENDING)
    site_name = Column(String(255),default=None)
    client_id = Column(String(36),default=None)
    site_address = Column(String(255),default=None)
    site_location = Column(JSON, default=None)
    site_city = Column(String(100),default=None)
    bill_to_name = Column(String(255),default=None)
    cutomer_email = Column(String(255),default=None)
    customer_contact_name = Column(String(255),default=None)
    customer_phone = Column(String(50),default=None)
    customer_fax = Column(String(50),default=None)
    customer_po = Column(String(100),default=None)
    job_number = Column(String(100),default=None)
    job_desc = Column(String(255),default=None)
    completion_date = Column(DateTime)
    priority = Column(Integer, default=1)
    due_date = Column(DateTime)
    estimated_hours = Column(Integer)
    scheduled_arrival = Column(DateTime)
    dispatched_date = Column(DateTime)
    dispatcher = Column(String(100),default=None)
    work_requested = Column(Text,default=None)
    dispatch_note = Column(Text,default=None)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))


    wo_assignees = relationship("WoAssignee", back_populates="work_order")
    wo_schedules = relationship("WoSchedules", back_populates="work_order")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the work order.
        """
        return {
            "id": str(self.id),
            "request_no": self.request_no,
            "client_id": self.client_id,
            "wo_number": self.wo_number,
            "project_id": self.project_id,
            "wo_date": self.wo_date.strftime("%Y-%m-%d %H:%M:%S") if self.wo_date else None,
            "wo_status": self.wo_status.name if self.wo_status else None,
            "site_name": self.site_name,
            "site_address": self.site_address,
            "site_location": self.site_location,
            "site_city": self.site_city,
            "bill_to_name": self.bill_to_name,
            "cutomer_email": self.cutomer_email,
            "customer_contact_name": self.customer_contact_name,
            "customer_phone": self.customer_phone,
            "customer_fax": self.customer_fax,
            "customer_po": self.customer_po,
            "job_number": self.job_number,
            "job_desc": self.job_desc,
            "completion_date": self.completion_date.strftime("%Y-%m-%d %H:%M:%S") if self.completion_date else None,
            "priority": self.priority,
            "due_date": self.due_date.strftime("%Y-%m-%d %H:%M:%S") if self.due_date else None,
            "estimated_hours": self.estimated_hours,
            "scheduled_arrival": self.scheduled_arrival.strftime("%Y-%m-%d %H:%M:%S") if self.scheduled_arrival else None,
            "dispatched_date": self.dispatched_date.strftime("%Y-%m-%d %H:%M:%S") if self.dispatched_date else None,
            "dispatcher": self.dispatcher,
            "work_requested": self.work_requested,
            "dispatch_note": self.dispatch_note,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "updated_by": self.updated_by,
        }
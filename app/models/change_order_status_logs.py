"""
This module Represents the table structure/Schema of change_order_status_logs Table
"""
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    func,
    Enum
)
from sqlalchemy.orm import relationship
from utils.common import generate_uuid
from models import Base
from models.change_order import ChangeOrderStatusEnum
from dotenv import load_dotenv
load_dotenv()


class ChangeOrderStatusLogs(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of change_order_status_logs Table
    """
    __tablename__ = 'change_order_status_logs'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    status = Column(Enum(ChangeOrderStatusEnum), default=ChangeOrderStatusEnum.PENDING)
    co_id = Column(String(36), ForeignKey("change_order.id"))

    # Relations/associations
    change_order = relationship("ChangeOrder", back_populates="change_order_status_logs")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "created_by": str(self.created_by) if self.created_by else None,
            "status": self.status,
            "co_id": self.co_id,
        }
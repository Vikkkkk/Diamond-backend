from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from models import Base
from utils.common import generate_uuid




# Table: change_order_docs
class ChangeOrderDocs(Base):
    __tablename__ = 'change_order_docs'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    co_id = Column(String(36), ForeignKey("change_order.id"))
    doc_type = Column(String(255),default=None)
    file_name = Column(String(255),default=None)
    file_path = Column(String(255),default=None)
    file_type = Column(String(255),default=None)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())


    change_order = relationship("ChangeOrder", back_populates="change_order_docs")
    


    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the change order document.
        """
        return {
            "id": str(self.id),
            "co_id": self.co_id,
            "doc_type": self.doc_type,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
"""
AI Recommendation model - AI建议表.
Stores AI agent outputs with traceable source data.
"""

import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AIRecommendation(Base):
    """AI建议表 - stores AI agent recommendations.

    agent_type values:
    - Sales Agent
    - Inventory Agent
    - Procurement Agent
    - Finance Agent
    - Operation Agent
    - CEO Agent

    priority values: High / Medium / Low
    """

    __tablename__ = "ai_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False, index=True, comment="Agent类型")
    target_type = Column(String(50), nullable=True, comment="对象类型: store/product/order")
    target_id = Column(UUID(as_uuid=True), nullable=True, comment="对象ID")
    recommendation = Column(Text, nullable=False, comment="建议内容")
    priority = Column(String(20), nullable=False, default="Medium", comment="优先级: High/Medium/Low")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

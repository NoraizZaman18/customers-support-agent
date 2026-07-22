from typing import Optional, Literal
from pydantic import BaseModel


class AgentResponse(BaseModel):
    thought: str
    tool: Optional[
        Literal[
            "check_order_status",
            "calculate_refund",
            "search_faq",
            "create_ticket",
            "escalate_to_human",
            "check_return_policy"
        ]
    ] = None
    parameters: Optional[dict] = None
    final_answer: Optional[str] = None
    escalate: bool = False





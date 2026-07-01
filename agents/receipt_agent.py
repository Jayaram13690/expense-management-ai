"""
ReceiptAgent for handling receipt document management.

This module implements the ReceiptAgent that inherits from BaseAgent and
is responsible for receipt upload and status tracking operations.

The ReceiptAgent uses ONLY the following Strands tools:
- upload_receipt: Upload receipt documents
- get_receipt_status: Retrieve receipt processing status

Design Principles:
------------------
- Inherits from BaseAgent (no direct Strands Agent usage)
- Uses only specified tools (no service/repository access)
- Contains no business logic
- Contains no domain-specific knowledge
- Pure delegation to tools
- Clear separation of concerns
"""

from agents.base_agent import BaseAgent
from prompts.receipt_prompt import RECEIPT_AGENT_SYSTEM_PROMPT
from tools.receipt_tools import get_receipt_status, upload_receipt


class ReceiptAgent(BaseAgent):
    """
    ReceiptAgent for handling receipt document management.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for receipt upload and status tracking.

    Responsibilities:
        - Upload receipt documents and associate with claims
        - Retrieve receipt processing status and details
        - Provide receipt tracking information
        - Handle receipt document metadata

    Tools:
        - upload_receipt: Upload receipt documents
        - get_receipt_status: Retrieve receipt status

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the ReceiptAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=RECEIPT_AGENT_SYSTEM_PROMPT,
            tools=[upload_receipt, get_receipt_status],
            name="ReceiptAgent",
            description="Handles receipt operations.",
        )

import sys
sys.path.insert(0, ".")

import logging
logging.basicConfig(level=logging.DEBUG)

# Let's inspect tools/expense_tools.py directly
import tools.expense_tools as et
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.dto.expense_item import ExpenseItem
from datetime import date
from decimal import Decimal

# Let's construct a sample request dictionary mimicking what the LLM passes
req_dict = {
    "employee_id": "EMP0006",
    "trip_name": "Client Meeting Hyderabad",
    "business_purpose": "Attended customer meetings and project discussions with the client.",
    "destination": "Hyderabad",
    "trip_start_date": "2026-06-20",
    "trip_end_date": "2026-06-22",
    "expense_items": [
        {
            "category_code": "HOTEL",
            "description": "Hotel",
            "expense_date": "2026-06-20",
            "requested_amount": 6000
        },
        {
            "category_code": "TRANSPORT",
            "description": "Taxi",
            "expense_date": "2026-06-21",
            "requested_amount": 900
        }
    ]
}

# Let's try to validate it with Pydantic
try:
    req_obj = SubmitExpenseClaimRequest.model_validate(req_dict)
    print("Pydantic validation SUCCESS:", req_obj)
except Exception as e:
    import traceback
    print("Pydantic validation FAILED:")
    traceback.print_exc()

# Let's try calling the service preview_claim with the dictionary and the object
try:
    print("\nCalling service.preview_claim with object:")
    res = et.expense_claim_service.preview_claim(req_obj)
    print("SUCCESS:", res)
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    print("\nCalling service.preview_claim with dictionary:")
    res = et.expense_claim_service.preview_claim(req_dict)
    print("SUCCESS:", res)
except Exception as e:
    import traceback
    traceback.print_exc()

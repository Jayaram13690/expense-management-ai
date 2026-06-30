"""
Master seed data.

Contains all reference/master data required by the application.

This module intentionally contains only data.
No repository or database logic belongs here.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from models.employee import Employee, EmploymentType
from models.expense_category import ExpenseCategory
from models.expense_policy import ExpensePolicy

###############################################################################
# Employees
###############################################################################

EMPLOYEES: list[Employee] = [
    Employee(
        employee_id="EMP0001",
        first_name="Rajesh",
        last_name="Sharma",
        email="rajesh.sharma@acmetech.com",
        department="Executive",
        designation="Chief Executive Officer",
        grade="G11",
        manager_id=None,
        cost_center="EXEC001",
        location="Bengaluru",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0002",
        first_name="Priya",
        last_name="Nair",
        email="priya.nair@acmetech.com",
        department="Engineering",
        designation="Vice President Engineering",
        grade="G9",
        manager_id="EMP0001",
        cost_center="ENG001",
        location="Bengaluru",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0003",
        first_name="Amit",
        last_name="Verma",
        email="amit.verma@acmetech.com",
        department="Finance",
        designation="Vice President Finance",
        grade="G9",
        manager_id="EMP0001",
        cost_center="FIN001",
        location="Mumbai",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0004",
        first_name="Sneha",
        last_name="Reddy",
        email="sneha.reddy@acmetech.com",
        department="Engineering",
        designation="Engineering Manager",
        grade="G7",
        manager_id="EMP0002",
        cost_center="ENG002",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0005",
        first_name="Karthik",
        last_name="Iyer",
        email="karthik.iyer@acmetech.com",
        department="Finance",
        designation="Finance Manager",
        grade="G7",
        manager_id="EMP0003",
        cost_center="FIN002",
        location="Mumbai",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0006",
        first_name="Ananya",
        last_name="Rao",
        email="ananya.rao@acmetech.com",
        department="Engineering",
        designation="Lead Software Engineer",
        grade="G5",
        manager_id="EMP0004",
        cost_center="ENG003",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0007",
        first_name="Rohan",
        last_name="Gupta",
        email="rohan.gupta@acmetech.com",
        department="Engineering",
        designation="Lead Software Engineer",
        grade="G5",
        manager_id="EMP0004",
        cost_center="ENG003",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0008",
        first_name="Meera",
        last_name="Joshi",
        email="meera.joshi@acmetech.com",
        department="Engineering",
        designation="Senior Software Engineer",
        grade="G5",
        manager_id="EMP0006",
        cost_center="ENG004",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0009",
        first_name="Arjun",
        last_name="Patel",
        email="arjun.patel@acmetech.com",
        department="Engineering",
        designation="Software Engineer",
        grade="G3",
        manager_id="EMP0006",
        cost_center="ENG004",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0010",
        first_name="Neha",
        last_name="Singh",
        email="neha.singh@acmetech.com",
        department="Engineering",
        designation="Software Engineer",
        grade="G3",
        manager_id="EMP0007",
        cost_center="ENG004",
        location="Hyderabad",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0011",
        first_name="Rahul",
        last_name="Kulkarni",
        email="rahul.kulkarni@acmetech.com",
        department="Finance",
        designation="Senior Financial Analyst",
        grade="G5",
        manager_id="EMP0005",
        cost_center="FIN003",
        location="Mumbai",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0012",
        first_name="Divya",
        last_name="Menon",
        email="divya.menon@acmetech.com",
        department="Finance",
        designation="Financial Analyst",
        grade="G3",
        manager_id="EMP0011",
        cost_center="FIN003",
        location="Mumbai",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0013",
        first_name="Vikram",
        last_name="Desai",
        email="vikram.desai@acmetech.com",
        department="Human Resources",
        designation="HR Business Partner",
        grade="G5",
        manager_id="EMP0001",
        cost_center="HR001",
        location="Bengaluru",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0014",
        first_name="Pooja",
        last_name="Kapoor",
        email="pooja.kapoor@acmetech.com",
        department="Sales",
        designation="Regional Sales Manager",
        grade="G7",
        manager_id="EMP0001",
        cost_center="SAL001",
        location="Delhi",
        employment_type=EmploymentType.FULL_TIME,
    ),
    Employee(
        employee_id="EMP0015",
        first_name="Aditya",
        last_name="Malhotra",
        email="aditya.malhotra@acmetech.com",
        department="Operations",
        designation="Operations Executive",
        grade="G3",
        manager_id="EMP0001",
        cost_center="OPS001",
        location="Pune",
        employment_type=EmploymentType.FULL_TIME,
    ),
]

###############################################################################
# Expense Categories
###############################################################################

EXPENSE_CATEGORIES: list[ExpenseCategory] = [
    ExpenseCategory(
        category_id="CAT0001",
        category_code="HOTEL",
        category_name="Hotel Accommodation",
        description="Accommodation expenses incurred during approved business travel.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=1,
    ),
    ExpenseCategory(
        category_id="CAT0002",
        category_code="AIR",
        category_name="Air Travel",
        description="Domestic and international airfare for approved business trips.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=2,
    ),
    ExpenseCategory(
        category_id="CAT0003",
        category_code="TRAIN",
        category_name="Rail Travel",
        description="Railway travel expenses for official business purposes.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=3,
    ),
    ExpenseCategory(
        category_id="CAT0004",
        category_code="TAXI",
        category_name="Taxi & Ride Share",
        description="Taxi, cab, ride-share and airport transfer expenses.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=False,
        display_order=4,
    ),
    ExpenseCategory(
        category_id="CAT0005",
        category_code="MEALS",
        category_name="Meals & Entertainment",
        description="Business meals and approved client entertainment expenses.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=5,
    ),
    ExpenseCategory(
        category_id="CAT0006",
        category_code="PARK",
        category_name="Parking",
        description="Parking fees incurred during official travel.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=False,
        display_order=6,
    ),
    ExpenseCategory(
        category_id="CAT0007",
        category_code="FUEL",
        category_name="Fuel",
        description="Fuel reimbursement for approved personal vehicle usage.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=7,
    ),
    ExpenseCategory(
        category_id="CAT0008",
        category_code="OFFICE",
        category_name="Office Supplies",
        description="Business office supplies purchased with prior approval.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=True,
        display_order=8,
    ),
    ExpenseCategory(
        category_id="CAT0009",
        category_code="INTERNET",
        category_name="Internet Charges",
        description="Business internet connectivity charges during travel.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=False,
        display_order=9,
    ),
    ExpenseCategory(
        category_id="CAT0010",
        category_code="MOBILE",
        category_name="Mobile Charges",
        description="Official mobile communication expenses.",
        reimbursement_required=True,
        receipt_required=True,
        approval_required=False,
        display_order=10,
    ),
]

###############################################################################
# Policy Configuration
###############################################################################

EMPLOYEE_GRADES = [
    "G3",
    "G5",
    "G7",
    "G9",
    "G11",
]


POLICY_LIMITS: dict[str, dict[str, tuple[int, int]]] = {
    "G3": {
        "HOTEL": (5000, 60000),
        "AIR": (20000, 120000),
        "TRAIN": (4000, 30000),
        "TAXI": (1500, 15000),
        "MEALS": (1000, 20000),
        "PARK": (500, 5000),
        "FUEL": (2000, 15000),
        "OFFICE": (3000, 25000),
        "INTERNET": (500, 3000),
        "MOBILE": (500, 3000),
    },
    "G5": {
        "HOTEL": (8000, 90000),
        "AIR": (35000, 180000),
        "TRAIN": (6000, 40000),
        "TAXI": (2000, 20000),
        "MEALS": (1500, 30000),
        "PARK": (700, 7000),
        "FUEL": (2500, 18000),
        "OFFICE": (5000, 35000),
        "INTERNET": (750, 5000),
        "MOBILE": (750, 5000),
    },
    "G7": {
        "HOTEL": (12000, 120000),
        "AIR": (50000, 250000),
        "TRAIN": (8000, 50000),
        "TAXI": (3000, 30000),
        "MEALS": (2500, 45000),
        "PARK": (1000, 10000),
        "FUEL": (3500, 25000),
        "OFFICE": (7000, 50000),
        "INTERNET": (1000, 7000),
        "MOBILE": (1000, 7000),
    },
    "G9": {
        "HOTEL": (18000, 180000),
        "AIR": (80000, 400000),
        "TRAIN": (12000, 70000),
        "TAXI": (4000, 45000),
        "MEALS": (4000, 70000),
        "PARK": (1500, 15000),
        "FUEL": (5000, 35000),
        "OFFICE": (10000, 70000),
        "INTERNET": (1500, 10000),
        "MOBILE": (1500, 10000),
    },
    "G11": {
        "HOTEL": (25000, 250000),
        "AIR": (150000, 600000),
        "TRAIN": (15000, 90000),
        "TAXI": (5000, 60000),
        "MEALS": (6000, 100000),
        "PARK": (2000, 20000),
        "FUEL": (7000, 50000),
        "OFFICE": (15000, 100000),
        "INTERNET": (2000, 15000),
        "MOBILE": (2000, 15000),
    },
}

###############################################################################
# Expense Policies
###############################################################################

EXPENSE_POLICIES: list[ExpensePolicy] = []

for grade in EMPLOYEE_GRADES:
    for category in EXPENSE_CATEGORIES:
        daily_limit, monthly_limit = POLICY_LIMITS[grade][category.category_code]

        EXPENSE_POLICIES.append(
            ExpensePolicy(
                policy_id=f"POL{len(EXPENSE_POLICIES) + 1:04d}",
                category_id=category.category_id,
                employee_grade=grade,
                daily_limit=Decimal(str(daily_limit)),
                monthly_limit=Decimal(str(monthly_limit)),
                receipt_required=category.receipt_required,
                approval_required=category.approval_required,
                currency="INR",
                effective_from=date(2025, 1, 1),
                effective_to=date(2035, 12, 31),
                description=(f"{grade} reimbursement policy for {category.category_name}"),
            )
        )

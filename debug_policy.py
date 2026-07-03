# # debug_policy.py

# from repositories.expense_category_repository import ExpenseCategoryRepository
# from repositories.expense_policy_repository import ExpensePolicyRepository

# cat_repo = ExpenseCategoryRepository()
# policy_repo = ExpensePolicyRepository()

# cat = cat_repo.get_by_category_code("HOTEL")
# print("CATEGORY =", cat)

# if cat:
#     policy = policy_repo.get_policy(
#         category_id=cat.category_id,
#         employee_grade="G5",
#     )

#     print("POLICY =", policy)

from services.expense_policy_service import ExpensePolicyService

service = ExpensePolicyService()

policy = service.get_policy_by_identifier(
    category_identifier="HOTEL",
    employee_grade="G5",
)

print(policy)
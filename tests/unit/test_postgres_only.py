from app.domain.postgres_only import is_postgres_only_question


def test_plan_and_csm_is_postgres_only():
    assert is_postgres_only_question("What plan am I on and who is my CSM?")


def test_cancellation_with_plan_is_not_postgres_only():
    assert not is_postgres_only_question("cancellation policy for my plan")


def test_order_status_is_not_postgres_only_by_keyword_guard():
    # status questions use postgres but don't hit account keywords — guard is for search_documents misuse
    assert not is_postgres_only_question("what is the status of ORD-1001")

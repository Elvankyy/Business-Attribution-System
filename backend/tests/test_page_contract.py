from scripts.check_page_contract import check_contract


def test_page_contract_has_no_missing_endpoints():
    summary = check_contract()

    assert summary["missing"] == []
    assert summary["total"] > 0

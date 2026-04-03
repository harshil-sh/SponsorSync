from sponsor_sync.utilities import (
    expand_title_synonyms,
    normalize_contract_type,
    normalize_title,
    parse_salary_to_annual_gbp,
)


def test_parse_salary_to_annual_gbp_for_common_uk_formats() -> None:
    annual = parse_salary_to_annual_gbp("£55,000 per annum")
    assert annual.minimum_gbp == 55000
    assert annual.maximum_gbp == 55000

    daily = parse_salary_to_annual_gbp("£350 - £450 per day")
    assert daily.minimum_gbp == 91000
    assert daily.maximum_gbp == 117000

    monthly = parse_salary_to_annual_gbp("GBP 4,500 per month")
    assert monthly.minimum_gbp == 54000
    assert monthly.maximum_gbp == 54000

    shorthand = parse_salary_to_annual_gbp("£45k - £60k")
    assert shorthand.minimum_gbp == 45000
    assert shorthand.maximum_gbp == 60000


def test_parse_salary_to_annual_gbp_handles_non_salary_inputs() -> None:
    non_numeric = parse_salary_to_annual_gbp("Competitive salary")
    assert non_numeric.minimum_gbp is None
    assert non_numeric.maximum_gbp is None

    non_gbp = parse_salary_to_annual_gbp("$120,000")
    assert non_gbp.minimum_gbp is None
    assert non_gbp.maximum_gbp is None


def test_normalize_contract_type() -> None:
    assert normalize_contract_type("Full-time permanent") == "permanent"
    assert normalize_contract_type("6 month contract") == "contract"
    assert normalize_contract_type("Part time") == "part_time"
    assert normalize_contract_type(None) == "unknown"


def test_title_normalization_and_synonym_expansion() -> None:
    assert (
        normalize_title("  Senior Software Engineer (Python) ")
        == "senior software engineer python"
    )

    expanded = expand_title_synonyms("Technical Lead")
    assert "tech lead" in expanded
    assert "technical lead" in expanded

    unknown = expand_title_synonyms("Platform Architect")
    assert unknown == {"platform architect"}

from SecurityScorecard import Client, securityscorecard_portfolios_list_command, securityscorecard_portfolio_list_companies_command, securityscorecard_company_factor_score_get_command,  securityscorecard_company_history_score_get_command,  securityscorecard_company_services_get_command,  securityscorecard_company_score_get_command,  securityscorecard_company_history_factor_score_get_command,  securityscorecard_alert_grade_change_create_command, securityscorecard_alert_score_threshold_create_command, securityscorecard_alerts_list_command, is_valid_domain, is_email_valid, incidents_to_import, is_date_valid
import requests_mock
import json
import io

MOCK_URL = "http://securityscorecard-mock-url"

client = Client(
    base_url=MOCK_URL,
    verify=False,
    proxy=False
)

def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())

def test_is_valid_domain():
    assert is_valid_domain("google.com")
    assert not is_valid_domain("sometestdomain")

def test_is_email_valid():
    assert is_email_valid("someuser@somedomain.com")
    assert not is_email_valid("someuser.com")

def test_is_date_valid():
    assert is_date_valid("2021-12-31")
    assert not is_date_valid("2021-13-31")
    assert not is_date_valid("202-12-31")

def test_securityscorecard_portfolios_list(mocker):

    raw_response = util_load_json("./test_data/portfolios.json")
    mocker.patch.object(client, "get_portfolios", return_value=raw_response)

    response = client.get_portfolios()

    assert response.get('entries')

    entries = response.get('entries')

    assert len(entries) == 3
    first_entry = entries[0]
    assert first_entry.get('id') == '1'
    assert first_entry.get('name') == 'portfolio_1'
    assert first_entry.get('privacy') == 'private'
    assert first_entry.get('read_only') == 'true'

    return entries


# def test_securityscorecard_portfolio_list_companies(mocker):

#     """
#         Checks cases where the portfolio exists and doesn't exist
#     """

#     portfolios = test_securityscorecard_portfolios_list(mocker)

#     # 1. Check with portfolio that exists
#     portfolio_exists = portfolios[0]

#     raw_response = util_load_json("./test_data/companies.json")
#     mocker.patch.object(client, "get_companies_in_portfolio", return_value=raw_response)
#     response_portfolio = client.get_companies_in_portfolio(portfolio_exists)
#     # print(response_portfolio)

#     assert response_portfolio.get("entries")

#     companies = response_portfolio.get("entries")

#     assert len(companies) == 3

#     # 2. Check with portfolio that doesn't exist
#     portfolio_not_exists = "portfolio4"
#     response_portfolio_not_exist = client.get_companies_in_portfolio(portfolio_not_exists)

#     print(response_portfolio_not_exist)

#     # asset 


# def test_securityscorecard_company_factor_score_get():

# def test_securityscorecard_company_history_score_get():

# def test_securityscorecard_alert_grade_change_create():

# def test_securityscorecard_alert_score_threshold_create():

# def test_securityscorecard_alerts_list():

# def test_securityscorecard_company_services_get():

# def test_securityscorecard_company_score_get():

# def test_securityscorecard_company_history_factor_score_get():

def main() -> None:
    pass


if __name__ == "builtins":
    main()
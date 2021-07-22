import json

import pytest

from AzureADIdentityProtection import (AADClient,
                                       azure_ad_identity_protection_risk_detection_list_command,
                                       azure_ad_identity_protection_risky_users_list_command,
                                       azure_ad_identity_protection_risky_users_history_list_command,
                                       azure_ad_identity_protection_risky_users_confirm_compromised_command,
                                       azure_ad_identity_protection_risky_users_dismiss_command)

dummy_user_id = 'dummy_id'


@pytest.fixture()
def client(mocker):
    mocker.patch('AzureADIdentityProtection.MicrosoftClient.get_access_token', return_value='token')
    return AADClient('dummy_app_id', 'dummy_subscription_id', 'dummy_resource_group_name', verify=False, proxy=False)


@pytest.mark.parametrize('command,test_data_file,url_suffix,next_link_description,kwargs',
                         ((azure_ad_identity_protection_risk_detection_list_command,
                           'test_data/risk_detections_response.json',
                           'riskDetections',
                           'risk_detection_list',
                           {}),
                          (azure_ad_identity_protection_risky_users_list_command,
                           'test_data/risky_users_response.json',
                           'RiskyUsers',
                           'risky_user_list',
                           {}),
                          (azure_ad_identity_protection_risky_users_history_list_command,
                           'test_data/risky_user_history_response.json',
                           f'RiskyUsers/{dummy_user_id}/history',
                           'risky_users_history_list',
                           {'user_id': dummy_user_id})
                          ))
def test_list_commands(client, requests_mock, command, test_data_file, url_suffix, next_link_description, kwargs):
    """
    Given:
        - AAD Client
    When:
        - Listing (risks, risky users, user history)
    Then:
        - Verify API request sent as expected
        - Verify command outputs
    """
    with open(test_data_file) as f:
        api_response = json.load(f)

    requests_mock.get(f'{client.ms_client._base_url}/{url_suffix}?$top=50', json=api_response)
    result = command(client, limit=50, **kwargs)

    expected_values = api_response.get('value')
    actual_values = result.outputs.get('AAD_Identity_Protection.values(val.id === obj.id)')
    assert actual_values == expected_values

    expected_next_link = api_response.get('@odata.nextLink')
    if expected_next_link:  # risky_users_history_list does not have next link
        actual_next_url = result.outputs.get(f'AAD_Identity_Protection.NextLink(val.Description === '
                                             f'"{next_link_description}")', {}).get('URL')
        assert actual_next_url == expected_next_link


@pytest.mark.parametrize('method,expected_output,url_suffix,kwargs', (
        (
                azure_ad_identity_protection_risky_users_confirm_compromised_command,
                '✅ Confirmed successfully.',
                'riskyUsers/confirmCompromised',
                {'user_ids': [dummy_user_id]}
        ),
        (
                azure_ad_identity_protection_risky_users_dismiss_command,
                '✅ Dismissed successfully.',
                'riskyUsers/dismiss',
                {'user_ids': [dummy_user_id]}
        )
)
                         )
def test_status_update_commands(client, requests_mock, method, expected_output, url_suffix, kwargs):
    """
    Given:
        - AAD Client
        - User name whose status we want to update

    When:
        - Calling a user-status-changing method (dismiss, confirm compromised)

    Then:
        - Verify API request sent as expected
        - Verify command outputs
    """

    requests_mock.post(f'{client.ms_client._base_url}/{url_suffix}', status_code=204)
    result = method(client, **kwargs)
    assert requests_mock.request_history[0].json() == {'userIds': [dummy_user_id]}
    assert result == expected_output

from CommonServerPython import *

""" IMPORTS """
import demistomock as demisto

""" CONSTANTS """
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
AUTH_URL = "securitymanager/api/authentication/login"
WORKFLOW_URL = "/policyplanner/api/domain/{0}/workflow/version/latest/all"
CREATE_PP_TICKET_URL = "/policyplanner/api/domain/{0}/workflow/{1}/packet"
PCA_URL_SUFFIX = "/orchestration/api/domain/{}/change/device/{}/pca"
RULE_REC_URL = "orchestration/api/domain/{}/change/rulerec"

create_pp_payload = {
    "sources": [
        ""
    ],
    "destinations": [
        ""
    ],
    "action": "",
    "services": [
        ""
    ],
    "requirementType": "RULE",
    "childKey": "add_access",
    "variables": {}
}


def get_rule_rec_request_payload():
    return {
        "apps": [],
        "destinations": [
            ""
        ],
        "services": [
            ""
        ],
        "sources": [
            ""
        ],
        "users": [],
        "requirementType": "RULE",
        "childKey": "add_access",
        "variables": {
            "expiration": "null",
            "review": "null"
        },
        "action": ""
    }


def get_create_pp_ticket_payload():
    return {
        "variables": {
            "summary": "Request Test06",
            "businessNeed": "",
            "priority": "LOW",
            "dueDate": "2021-05-29 13:44:58",
            "applicationName": "",
            "customer": "",
            "externalTicketId": "",
            "notes": "",
            "requesterName": "System Administrator",
            "requesterEmail": "",
            "applicationOwner": "",
            "integrationRecord": "",
            "carbonCopy": [
                ""
            ]
        },
        "policyPlanRequirements": []
    }


class Client(BaseClient):
    def authenticate_user(self):
        username = demisto.params().get('credentials').get('identifier')
        password = demisto.params().get('credentials').get('password')

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        api_response = self._http_request(method='POST',
                                          url_suffix=AUTH_URL,
                                          json_data={'username': username, 'password': password},
                                          headers=headers
                                          )
        return api_response

    def get_all_workflow(self, auth_token, domain_id, parameters):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-FM-Auth-Token': auth_token
        }
        workflow_url = WORKFLOW_URL.format(domain_id)
        api_response = self._http_request(method='GET',
                                          url_suffix=workflow_url,
                                          params=parameters,
                                          headers=headers
                                          )
        list_of_workflow = []
        for workflow in api_response.get('results'):
            if workflow['workflow']['pluginArtifactId'] == "access-request":
                workflow_name = workflow['workflow']['name']
                list_of_workflow.append(workflow_name)

        return list_of_workflow

    def get_list_of_workflow(self, auth_token, domain_id, parameters):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-FM-Auth-Token': auth_token
        }
        workflow_url = WORKFLOW_URL.format(domain_id)
        api_response = self._http_request(method='GET',
                                          url_suffix=workflow_url,
                                          params=parameters,
                                          headers=headers
                                          )

        return api_response

    def get_workflow_id_by_workflow_name(self, domain_id, workflow_name, auth_token, parameters):

        list_of_workflow = self.get_list_of_workflow(auth_token, domain_id, parameters)
        count_of_workflow = list_of_workflow.get('total')

        if count_of_workflow > 10:
            parameters = {'includeDisabled': False, 'pageSize': count_of_workflow}
            list_of_workflow = self.get_list_of_workflow(auth_token, domain_id, parameters)

        for workflow in list_of_workflow.get('results'):
            if ((workflow['workflow']['pluginArtifactId'] == "access-request") and
                    (workflow['workflow']['name'] == workflow_name)):
                workflow_id = workflow['workflow']['id']
                return workflow_id

    def create_pp_ticket(self, auth_token, payload):
        parameters = {'includeDisabled': False, 'pageSize': 10}
        workflow_id = self.get_workflow_id_by_workflow_name(payload["domainId"], payload["workflowName"], auth_token,
                                                            parameters)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-FM-Auth-Token': auth_token
        }
        data = get_create_pp_ticket_payload()
        data["variables"]["priority"] = payload["priority"]
        data["variables"]["dueDate"] = payload["due_date"].replace('T', ' ')[:-6]
        list_of_requirements = payload["requirements"]
        for i in range(len(list_of_requirements)):
            req_payload = list_of_requirements[i]
            input_data = create_pp_payload
            input_data["sources"] = list(req_payload["sources"].split(","))
            input_data["destinations"] = list(req_payload["destinations"].split(","))
            input_data["services"] = list(req_payload["services"].split(","))
            input_data["action"] = req_payload["action"]
            data["policyPlanRequirements"].append(dict(input_data))

        create_pp_ticket_url = CREATE_PP_TICKET_URL.format(payload["domainId"], workflow_id)
        api_response = self._http_request(method='POST',
                                          url_suffix=create_pp_ticket_url,
                                          headers=headers,
                                          json_data=data
                                          )
        return api_response

    def validate_pca_change(self, payload_pca, pca_url_suffix, headers):
        api_response = self._http_request(method='POST',
                                          url_suffix=pca_url_suffix,
                                          json_data=payload_pca,
                                          headers=headers,
                                          params=None,
                                          timeout=20)
        return api_response

    def rule_rec_api(self, auth_token, payload):
        """ Calling orchestration rulerec api by passing json data as request body, headers, params and domainId
                which returns you list of rule recommendations for given input as response"""

        parameters = {'deviceGroupId': payload["deviceGroupId"], 'addressMatchingStrategy': 'INTERSECTS',
                      'modifyBehavior': 'MODIFY', 'strategy': None}
        data = get_rule_rec_request_payload()

        data["destinations"] = payload["destinations"]
        data["sources"] = payload["sources"]
        data["services"] = payload["services"]
        data["action"] = payload["action"]
        rule_rec_api_response = self._http_request(
            method='POST',
            url_suffix=RULE_REC_URL.format(payload["domainId"]),
            json_data=data,
            params=parameters,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-FM-Auth-Token': auth_token,
            }
        )
        return rule_rec_api_response

    def rule_rec_output(self, auth_token, payload):
        """ Calling orchestration rulerec api by passing json data as request body, headers, params and domainId
                which returns you list of rule recommendations for given input as response"""

        parameters = {'deviceId': payload["deviceId"], 'addressMatchingStrategy': 'INTERSECTS',
                      'modifyBehavior': 'MODIFY', 'strategy': None}
        data = get_rule_rec_request_payload()

        data["destinations"] = payload["destinations"]
        data["sources"] = payload["sources"]
        data["services"] = payload["services"]
        data["action"] = payload["action"]
        rule_rec_api_response = self._http_request(
            method='POST',
            url_suffix=RULE_REC_URL.format(payload["domainId"]),
            json_data=data,
            params=parameters,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-FM-Auth-Token': auth_token,
            }
        )
        return rule_rec_api_response


def test_module(client):
    response = client.authenticate_user()
    if response.get('authorized'):
        return "ok"
    else:
        return "Error in API call in FireMonSecurityManager Integrations"


def authenticate_command(client):
    return client.authenticate_user().get('token')


def create_pp_ticket_command(client, args):
    auth_token = authenticate_command(client)

    payload = dict(domainId=args.get('domain_id'), workflowName=args.get('workflow_name'),
                   requirements=args.get("requirement"), priority=args.get("priority"),
                   due_date=args.get("due_date"))
    result = client.create_pp_ticket(auth_token, payload)
    return result


def pca_command(client, args):
    auth_token = authenticate_command(client)
    payload = dict(sources=list(args.get("sources").split(",")),
                   destinations=list(args.get('destinations').split(",")),
                   services=list(args.get('services').split(",")),
                   action=args.get('action'), domainId=args.get('domain_id'), deviceGroupId=args.get('device_group_id'))
    payload_rule_rec = client.rule_rec_api(auth_token, payload)
    result = {}
    list_of_device_changes = payload_rule_rec['deviceChanges']
    for i in range(len(list_of_device_changes)):
        filtered_rules = []
        list_of_rule_changes = list_of_device_changes[i]["ruleChanges"]
        device_id = list_of_device_changes[i]["deviceId"]
        headers = {'Content-Type': 'application/json',
                   'accept': 'application/json',
                   'X-FM-Auth-Token': auth_token}

        for j in range(len(list_of_rule_changes)):
            if list_of_rule_changes[j]['action'] != 'NONE':
                filtered_rules.append(list_of_rule_changes[j])

        if filtered_rules is None:
            return "No Rules Needs to be changed!"

        result[i] = client.validate_pca_change(filtered_rules,
                                               PCA_URL_SUFFIX.format(args.get('domain_id'), device_id),
                                               headers)
        del result[i]['requestId']
        del result[i]['pcaResult']['startDate']
        del result[i]['pcaResult']['endDate']
        del result[i]['pcaResult']['device']['parents']
        del result[i]['pcaResult']['device']['children']
        del result[i]['pcaResult']['device']['gpcDirtyDate']
        del result[i]['pcaResult']['device']['gpcComputeDate']
        del result[i]['pcaResult']['device']['gpcImplementDate']
        del result[i]['pcaResult']['device']['state']
        del result[i]['pcaResult']['device']['managedType']
        del result[i]['pcaResult']['device']['gpcStatus']
        del result[i]['pcaResult']['device']['updateMemberRuleDoc']
        del result[i]['pcaResult']['device']['devicePack']
        del result[i]['pcaResult']['affectedRules']

    return result


def main():
    verify_certificate = not demisto.params().get('insecure', False)
    base_url = urljoin(demisto.params()['url'])
    proxy = demisto.params().get('proxy', False)
    try:
        client = Client(
            base_url=base_url,
            verify=verify_certificate,
            proxy=proxy)
        if demisto.command() == 'test-module':
            result = test_module(client)
            demisto.results(result)
        elif demisto.command() == 'user-authentication':
            return_results(authenticate_command(client))
        elif demisto.command() == 'create-pp-ticket':
            return_results(create_pp_ticket_command(client, demisto.args()))
        elif demisto.command() == 'pca':
            return_results(pca_command(client, demisto.args()))
    except Exception as e:
        return_error(f'Failed to execute {demisto.command()} command. Error: {str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()

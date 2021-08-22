import demistomock as demisto
from CommonServerPython import *
import json


class GitLabIntegration:
    """ A class to represent the GitLab Demisto integration """
    DEMISTO_GROUP_ID = 'dsop%2Fopensource%2Fpalo-alto-networks%2Fdemisto'
    IMAGE_PROJECT_ID = 'dsop%2Fopensource%2Fpalo-alto-networks%2Fdemisto%2F{image_name}'
    GITLAB_INTEGRATION_INSTANCE_NAME = 'GitLab-Ironbank'

    def execute_command(self, command, args):
        args['using'] = self.GITLAB_INTEGRATION_INSTANCE_NAME
        return demisto.executeCommand(command, args)[0]['Contents']

    def get_open_merge_requests(self, image_name):
        args = {
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'state': 'opened',
            'target_branch': 'development'
        }
        demisto.info(f'Getting opened merge requests from repo1 for image {image_name}')
        merge_requests = self.execute_command('gitlab-merge-requests-list', args)
        merge_requests = merge_requests if merge_requests else []
        demisto.info(f'Retrieved the following opened merge requests for image {image_name}: {[mr.get("iid") for mr in merge_requests]}')
        return merge_requests

    def get_group_projects(self):
        demisto.info(f'Getting the projects list of {self.DEMISTO_GROUP_ID}')
        args = {
            'group_id': self.DEMISTO_GROUP_ID
        }
        projects = self.execute_command('gitlab-group-projects-list', args)
        projects = projects if projects else []
        return projects

    def get_merge_request(self, image_name, merge_request_iid):
        args = {
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'merge_request_iid': merge_request_iid
        }
        demisto.info(f'Retrieving MR #{merge_request_iid} for image {image_name}')
        merge_request = self.execute_command('gitlab-get-merge-request', args)
        merge_request = merge_request if merge_request else {}
        return merge_request

    def get_latest_pipeline(self, image_name, branch):
        args = {
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'ref': branch
        }
        pipelines = self.execute_command('gitlab-pipelines-list', args)
        latest_pipeline = pipelines[0] if pipelines else {}
        return latest_pipeline

    def get_pipeline_jobs(self, image_name, pipeline_id):
        args = {
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'pipeline_id': pipeline_id
        }
        pipeline_jobs = self.execute_command('gitlab-jobs-list', args)
        pipeline_jobs = pipeline_jobs if pipeline_jobs else []
        return pipeline_jobs

    def get_latest_open_issue(self, image_name):
        args = {
            'state': 'opened',
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'in': 'title',
            'search': f'{image_name}'
        }
        open_issues = self.execute_command('gitlab-issues-list', args)
        latest_open_issue = open_issues[0] if open_issues else {}
        return latest_open_issue

    def get_issue_template_file(self, image_name):
        args = {
            'file_path': '.gitlab%2Fissue_templates%2FApplication%20-%20Update.md',
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name),
            'ref': 'master'
        }
        issue_template = self.execute_command('gitlab-get-raw-file', args)
        issue_template = issue_template if issue_template else ''
        return issue_template

    def create_issue_request(self, image_name, title, description, labels):
        args = {
            'title': title,
            'description': description,
            'labels': labels,
            'project_id': self.IMAGE_PROJECT_ID.format(image_name=image_name)
        }
        issue = self.execute_command('gitlab-create-issue', args)
        issue = issue if issue else {}
        return issue


class GitHubIntegration:
    """ A class to represent the GitHub Demisto integration """
    GITHUB_INTEGRATION_INSTANCE_NAME = 'GitHub-Ironbank'
    FAILURE_BRANCH_ISSUE_TITLE = 'Repo1 {branch_name} branch pipeline failure - {image_name} Ironbank Image'

    def execute_command(self, command, args):
        args['using'] = self.GITHUB_INTEGRATION_INSTANCE_NAME
        return demisto.executeCommand(command, args)[0]['Contents']

    def search_open_failure_issues(self, branch_name, image_name):
        args = {
            'query': self.FAILURE_BRANCH_ISSUE_TITLE.format(branch_name=branch_name, image_name=image_name) + ' in:title type:issue is:open repo:demisto/dockerfiles'
        }
        open_issues = self.execute_command('github-search-issues', args)
        open_issues = open_issues if open_issues else []
        return open_issues

    def create_failure_issue(self, branch_name, image_name):
        args = {
            'title': self.FAILURE_BRANCH_ISSUE_TITLE.format(branch_name=branch_name, image_name=image_name),
            'body': 'This is an Auto-Generated issue, please do not change its title.'
        }
        return self.execute_command('github-create-issue', args)

    def comment_on_failure_issue(self, issue_number, pipeline, reason):
        web_url = pipeline.data.get('web_url')
        body = f'### Pipeline failed on branch {pipeline.branch_name} for image {pipeline.image_name}.'
        if web_url:
            body += f'\nFailure can be seen in: [{web_url}]({web_url})'
        if reason == 'check-cves':
            body += f'\nNew CVEs were found in latest tag for image {pipeline.image_name}.'
        args = {
            'issue_number': issue_number,
            'body': body
        }
        self.execute_command('gitlab-create-comment', args)


class Pipeline:
    def __init__(self, image_name, data):
        self.image_name = image_name
        self.data = data
        self.branch_name = self.data.get('ref')
        self.status = self.data.get('status')
        self.id = self.data.get('id')


class MergeRequest:
    """ A class to represent a Merge Request on Repo 1 """
    def __init__(self, image_name, merge_request_iid, data):
        self.data = data
        self.image_name = image_name
        self.iid = merge_request_iid
        self.state = self.data.get('state')

    def __eq__(self, other):
        return self.image_name == other.image_name and self.iid == other.iid


class MergeRequestsDataStructure:
    """ A class to represent the Ironbank-Opened-Merge-Requests Demisto list """
    LIST_NAME = 'Ironbank-Opened-Merge-Requests'

    def __init__(self, gitlab_integration):
        self.gitlab_integration = gitlab_integration
        self.data = self.get_data()

    def get_data(self):
        remote_list = self.get_remote_list()
        initial_data = self.transform_to_class(remote_list)
        data = self.update_with_all_images_and_merge_requests(initial_data)
        return data

    def get_remote_list(self):
        demisto.info(f'Retrieving {self.LIST_NAME} list from XSOAR instance')
        is_list_exist = demisto.executeCommand('IsListExist', {'listName': self.LIST_NAME})[0]['Contents'].lower() == 'yes'
        if not is_list_exist:
            demisto.info(f'{self.LIST_NAME} list does not exist in XSOAR instance, creating a new one')
            demisto.executeCommand('createList', {'listName': self.LIST_NAME, 'listData': {}})
            return {}
        else:
            demisto.info(f'{self.LIST_NAME} list exist in XSOAR instance')
            return json.loads(demisto.executeCommand('getList', {'listName': self.LIST_NAME})[0]['Contents'])

    def transform_to_class(self, remote_list):
        initial_data = {}
        for image_name, merge_requests_iids in remote_list.items():
            merge_requests = []
            for merge_request_iid in merge_requests_iids:
                merge_request_data = self.gitlab_integration.get_merge_request(image_name, merge_request_iid)
                merge_requests.append(MergeRequest(image_name, merge_request_iid, merge_request_data))
            initial_data[image_name] = merge_requests
        return initial_data

    def update_remote_list(self):
        demisto.info(f'Setting {self.LIST_NAME} list')
        data = {image_name: [mr.iid for mr in merge_requests] for image_name, merge_requests in self.data.items()}
        demisto.executeCommand('setList', {'listName': self.LIST_NAME, 'listData': json.dumps(data)})

    def remove_merge_request(self, merge_request: MergeRequest):
        if merge_request.image_name in self.data:
            if merge_request.iid in self.data[merge_request.image_name]:
                self.data[merge_request.image_name].remove(merge_request.iid)

    def update_with_all_images_and_merge_requests(self, initial_data):
        data = initial_data
        for project in self.gitlab_integration.get_group_projects():
            project_name = project.get('name')
            if project_name:
                raw_open_merge_requests = self.gitlab_integration.get_open_merge_requests(project_name)
                open_merge_requests = [MergeRequest(project_name, mr.get('iid'), mr) for mr in raw_open_merge_requests]
                if project_name not in data:
                    data[project_name] = open_merge_requests
                else:
                    data[project_name] = data[project_name] + [mr for mr in open_merge_requests if mr not in data[project_name]]
                demisto.info(f'All merge requests for image {project_name}: {[mr.iid for mr in data[project_name]]}')
        return data


class IronBankHandler:
    def __init__(self):
        self.gitlab_integration = GitLabIntegration()
        self.github_integration = GitHubIntegration()
        self.merge_requests_data_structure = MergeRequestsDataStructure(self.gitlab_integration)

    def handle_merge_requests(self):
        """ Logic as follows:
        For every image in “Ironbank-Opened-Merge-Requests”:
            For every MR in image:
                If MR is open:
                    If pipeline fails on feature-branch:
                        If there is an issue on demisto/etc, update the issue.
                        Otherwise, open an issue on demisto/etc.
                Otherwise (it is merged)
                    If pipeline fails on development:
                        If there is an issue on demisto/etc, update the issue.
                        Otherwise, open an issue on demisto/etc.
                    Otherwise (pipeline is green):
                        If a hardening request issue is open, update it.
                        Otherwise, open a new hardening request.
                        Remove MR from the list.
        """
        for image_name, merge_requests in self.merge_requests_data_structure.data.items():
            for merge_request in merge_requests:
                demisto.info(f'Handling MR #{merge_request.iid} for image {image_name}')
                task_status = self.handle_merge_request(merge_request)
                if task_status and merge_request.state not in ('opened', 'merged'):
                    demisto.info(f'MR #{merge_request.iid} for image {image_name} is closed (not merged)')
                    self.merge_requests_data_structure.remove_merge_request(merge_request)

    def handle_merge_request(self, merge_request: MergeRequest):
        if merge_request.state == 'opened':
            task_status = self.handle_open_merge_request(merge_request)
        elif merge_request.state == 'merged':
            task_status = self.handle_merged_merge_request(merge_request)
        else:
            task_status = True

        return task_status

    def handle_open_merge_request(self, merge_request: MergeRequest):
        demisto.info(f'MR #{merge_request.iid} for image {merge_request.image_name} is open')
        pipeline = Pipeline(merge_request.image_name, merge_request.data.get('head_pipeline'))
        demisto.info(f'Pipeline {pipeline.id} for image {merge_request.image_name} - MR #{merge_request.iid} - branch {pipeline.branch_name} {pipeline.status}')

        if pipeline.status == 'failed':
            task_status = self.handle_pipeline_failure(pipeline)
        else:
            task_status = True
            demisto.info(f'MR #{merge_request.iid} is open and pipeline is successful, waiting for an Ironbank member to merge it.')

        return task_status

    def handle_merged_merge_request(self, merge_request: MergeRequest):
        development_pipeline_data = self.gitlab_integration.get_latest_pipeline(image_name=merge_request.image_name, branch='development')
        development_pipeline = Pipeline(merge_request.image_name, development_pipeline_data)
        demisto.info(f'Pipeline {development_pipeline.id} for image {merge_request.image_name} - MR #{merge_request.iid} - branch {development_pipeline.branch_name} {development_pipeline.status}')
        task_status = True

        if development_pipeline.status == 'failed':
            task_status = self.handle_pipeline_failure(development_pipeline)
        elif development_pipeline.status == 'success':
            pipeline_jobs = self.gitlab_integration.get_pipeline_jobs(image_name=merge_request.image_name, pipeline_id=development_pipeline.id)
            for job in pipeline_jobs:
                if job.get('stage') == 'check-cves' and job.get('status') == 'failed':
                    # pipeline can be successful but check-cves will fail and will show up as a warning only
                    task_status = self.handle_pipeline_failure(development_pipeline, reason='check-cves')
                    return task_status
            task_status = self.handle_hardening_request(image_name=merge_request.image_name, merge_request_iid=merge_request.iid)
            if task_status:
                self.merge_requests_data_structure.remove_merge_request(merge_request)

        return task_status

    def handle_hardening_request(self, image_name, merge_request_iid):
        demisto.info(f'Handling hardening request for image {image_name} in MR #{merge_request_iid}')
        latest_open_issue = self.gitlab_integration.get_latest_open_issue(image_name)

        if not latest_open_issue:
            application_update_template = self.gitlab_integration.get_issue_template_file(image_name)
            # TODO: tick the check boxes
            created_issue = self.gitlab_integration.create_issue_request(
                image_name=image_name,
                title=f'{image_name} - Auto-Generated Update',
                description=application_update_template,
                labels='Approval'
            )
            demisto.info(f'created issue number {created_issue.get("iid")}')
        else:
            if latest_open_issue == 'initial':
                pass
            elif latest_open_issue == 'update':
                pass

        return True

    def handle_pipeline_failure(self, pipeline, reason='regular-failure'):
        demisto.info(f'Handling pipeline failure for image {pipeline.image_name} branch {pipeline.branch_name} reason: {reason}')
        open_failure_issues = self.github_integration.search_open_failure_issues(pipeline.branch_name, pipeline.image_name)

        if not open_failure_issues:
            demisto.info(f'Did not find corresponding issue for the pipeline #{pipeline.id}, creating an issue.')
            issue = self.github_integration.create_failure_issue(pipeline.branch_name, pipeline.image_name)
        else:
            issue = open_failure_issues[0]

        self.github_integration.comment_on_failure_issue(issue.get('number'), pipeline, reason)
        return True

    def done(self):
        self.merge_requests_data_structure.update_remote_list()


def main():
    success = True
    ironbank_handler = IronBankHandler()

    try:
        ironbank_handler.handle_merge_requests()
    except Exception as e:
        success = False
        return_error(f'Got an exception: {str(e)}')

    finally:
        ironbank_handler.done()
        if success:
            return_results('ok')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()

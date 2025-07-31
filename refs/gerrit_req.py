# -*- coding: utf-8 -*-

import os
import sys
import traceback
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse
import json
import argparse
from loguru import logger

PUBLIC_LIBS_PATH = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(PUBLIC_LIBS_PATH)
from refs.env_config import EnvConfig


class GerritReq(object):
    def __init__(self, default_account='svw-chencheng', default_gerrit='gerrit'):
        self._check_succ_code = [200, 201, 204]
        self._def_account = default_account
        if default_gerrit == 'gerrit':
            self.domain = EnvConfig.GERRIT_INFO['domain']
            self.root_url = EnvConfig.GERRIT_INFO['root_url']
            self.accounts = EnvConfig.GERRIT_INFO['accounts']


    def _exec(self, api_name, data=None, method='GET', account=None, timeout=120, return_json=True, headers=None):
        if not account:
            account = self._def_account
        api_url = '{}/a{}'.format(self.root_url, api_name)
        auth = HTTPBasicAuth(account, self.accounts[account]['http_pwd'])
        if not headers:
            headers = {
                'Content-Type': 'application/json; charset=UTF-8'
            }
        try:
            # logger.debug('gerrit api: {} | {}'.format(method, api_url))
            res = requests.request(method=method, url=api_url, data=data, auth=auth, headers=headers, timeout=timeout)
            # logger.debug('code: {}'.format(res.status_code))
            if res.status_code not in self._check_succ_code:
                logger.error('{} | {}'.format(res.status_code, res.text))
                return False
            if return_json:
                return json.loads(res.text.lstrip(r")]}'\n"))
            return True
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## Accounts APIs ##############################
    '''

    def set_http_password(self, account_id, http_password=None):
        api_name = '/accounts/{}/password.http'.format(account_id)
        data = {
            'generate': True
        }
        if http_password:
            data['http_password'] = http_password
        try:
            return self._exec(api_name, method='PUT', data=json.dumps(data))
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def list_accounts(self):
        api_name = '/accounts/?q=is:active&o=DETAILS'
        try:
            return self._exec(api_name, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_account_detail(self, account_id):
        api_name = '/accounts/{}/detail'.format(account_id)
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_account_groups(self, account_id):
        api_name = '/accounts/{}/groups/'.format(account_id)
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def add_ssh_key(self, account_id, ssh_key):
        api_name = '/accounts/{}/sshkeys'.format(account_id)
        headers = {
            'Content-Type': 'text/plain'
        }
        try:
            return self._exec(api_name, method='POST', data=ssh_key, headers=headers)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_user_id_by_email(self, email):
        api_name = '/accounts/?suggest&q={}'.format(email)
        try:
            response = self._exec(api_name)
            if response:
                return response[0]['_account_id']
            else:
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## Groups APIs ##############################
    '''
    def list_groups(self):
        api_name = '/groups/'
        try:
            return self._exec(api_name, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def list_group_members(self, group_id):
        api_name = '/groups/{}/members/'.format(urllib.parse.quote_plus(group_id))
        try:
            return self._exec(api_name, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False
    
    def remove_group_members(self, group_id, account_list):
        api_name = '/groups/{}/members.delete'.format(urllib.parse.quote_plus(group_id))
        data = json.dumps({
            'members': account_list
        })
        try:
            return self._exec(api_name, method='POST', data=data, return_json=False)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def add_group_members(self, group_id, email_lst):
        api_name = '/groups/{}/members'.format(urllib.parse.quote_plus(group_id))
        data = json.dumps({
            "members": email_lst
        })
        try:
            return self._exec(api_name, method='POST', data=data, return_json=False)
        except Exception as err:
            logger.error(err)
            return False

    def get_group(self, group_id):
        api_name = '/groups/{}'.format(urllib.parse.quote_plus(group_id))
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_group_id_by_name(self, group_name):
        api_name = '/groups/?query={}'.format(urllib.parse.quote_plus(group_name))
        try:
            response = self._exec(api_name)
            if isinstance(response, list) and len(response) > 0:
                return response[0].get('group_id')
            return None
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def rename_group(self, group_id, new_name):
        api_name = '/groups/{}/name'.format(urllib.parse.quote_plus(group_id))
        data = json.dumps({
            'name': new_name
        })
        try:
            return self._exec(api_name, method='PUT', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False
    
    def set_group_description(self, group_id, description):
        api_name = '/groups/{}/description'.format(urllib.parse.quote_plus(group_id))
        data = json.dumps({
            'description': description
        })
        try:
            return self._exec(api_name, method='PUT', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def set_group_owner(self, group_id, owner):
        api_name = '/groups/{}/owner'.format(urllib.parse.quote_plus(group_id))
        data = json.dumps({
            'owner': owner
        })
        try:
            return self._exec(api_name, method='PUT', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False
        
    '''
    ############################## Projects APIs ##############################
    '''

    def list_projects(self, prefix=None, type='ALL'):
        prefix_str = '&p={}'.format(prefix) if prefix else ''
        api_name = '/projects/?t&type={}{}'.format(type, prefix_str)
        try:
            return self._exec(api_name, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_project(self, project_name):
        api_name = '/projects/{}'.format(urllib.parse.quote_plus(project_name))
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_special_start_projects(self, git_start_str):
        api_name = '/projects/?r={}.*'.format(urllib.parse.quote_plus(git_start_str))
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def create_project(self, project_name, parent='All-Projects', permissions_only=False,
                       default_branch=['refs/heads/master']):
        api_name = '/projects/{}'.format(urllib.parse.quote_plus(project_name))
        data = json.dumps({
            'parent': parent,
            'permissions_only': permissions_only,
            'branches': default_branch,
            'create_empty_commit': 'TRUE',
            'require_change_id': 'TRUE'
        })
        try:
            return self._exec(api_name, method='PUT', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def create_git_branch(self, project_name, base_revision, new_branch_name, force_del=False):
        if force_del:
            self.del_project_branch(project_name, new_branch_name)
        api_name = '/projects/{}/branches/{}'.format(urllib.parse.quote_plus(project_name), new_branch_name)
        data = json.dumps({
            'revision': base_revision
        })
        try:
            return self._exec(api_name, method='PUT', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_project_branch(self, project_name, exist_branch_name):
        api_name = '/projects/{}/branches/{}'.format(urllib.parse.quote_plus(project_name), exist_branch_name)
        try:
            return self._exec(api_name, method='GET')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def del_project_branch(self, project_name, del_branch_name):
        api_name = '/projects/{}/branches:delete'.format(urllib.parse.quote_plus(project_name))
        data = json.dumps({
            "branches": [del_branch_name]
        })
        try:
            return self._exec(api_name, method='POST', data=data, return_json=False)
        except Exception as err:
            logger.error(err)
            return False

    def update_project_parent(self, project_name, parent_name):
        api_name = '/projects/{}/parent'.format(urllib.parse.quote_plus(project_name))
        data = json.dumps({
            "parent": parent_name,
            "commit_message": "Update the project parent"
        })
        try:
            return self._exec(api_name, method='PUT', data=data, return_json=False)
        except Exception as err:
            logger.error(err)
            return False

    def get_project_parent(self, project_name):
        api_name = '/projects/{}/parent'.format(urllib.parse.quote_plus(project_name))
        try:
            return self._exec(api_name, method='GET')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_project_children(self, project_name):
        api_name = '/projects/{}/children'.format(urllib.parse.quote_plus(project_name))
        try:
            return self._exec(api_name, method='GET')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## Changes APIs ##############################
    '''

    def get_change_info(self, change_id):
        api_name = '/changes/?q={}&o=DETAILED_ACCOUNTS&o=CURRENT_REVISION&o=CURRENT_FILES&o=CURRENT_COMMIT'.format(
            urllib.parse.quote_plus(change_id))
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_change_detail(self, change_id):
        api_name = '/changes/{}/detail'.format(urllib.parse.quote_plus(change_id))
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_parents(self, change_id, revision_id):
        api_name = '/changes/{}/revisions/{}/commit'.format(urllib.parse.quote_plus(change_id), revision_id)
        try:
            commit = self._exec(api_name)
            if not commit:
                logger.error('get patch parents failed!')
                return False
            return commit.get('parents')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_list_votes(self, change_id, account_id):
        api_name = '/changes/{}/reviewers/{}/votes/'.format(urllib.parse.quote_plus(change_id), account_id)
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def query_changes(self, query_str, limit=500):
        api_name = '/changes/?{}'.format(query_str)
        change_list = []
        try:
            start = 0
            while True:
                new_api = '{}&start={}&limit={}'.format(api_name, start, limit)
                res = self._exec(new_api)
                if not res:
                    break
                change_list.extend(res)
                if not res[-1].get('_more_changes'):
                    break
                start += limit
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return change_list

    def get_change_fileList(self, change_id, revision_id):
        api_name = '/changes/{}/revisions/{}/files/'.format(urllib.parse.quote_plus(change_id), revision_id)
        try:
            return self._exec(api_name, method='GET')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_change_patch(self, change_id, revision_id):
        api_name = '/changes/{}/revisions/{}/patch?zip'.format(urllib.parse.quote_plus(change_id), revision_id)
        try:
            return self._exec(api_name, method='GET')
        except Exception:
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_change_info_ssh(change_id):
        ssh_cmd = 'ssh -p 29418 gerrit.archermind.com.cn gerrit query --format=JSON --current-patch-set {}'.format(
            change_id)
        try:
            res = os.popen(ssh_cmd).read()
            if not res:
                logger.error('get change info error')
                return False
            change_info = {}
            for line in res.splitlines():
                try:
                    json_data = json.loads(line)
                    if 'id' in json_data:
                        change_info = json_data
                        break
                except Exception:
                    continue
            return change_info
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def set_vote(self, change_id, revision_id, label, vote=0, msg='', account='os-scm'):
        api_name = '/changes/{}/revisions/{}/review'.format(change_id, revision_id)
        data = json.dumps({
            'labels': {
                label: vote
            },
            'message': msg
        })
        try:
            return self._exec(api_name, method='POST', data=data, account=account)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def abandon_change(self, change_id):
        api_name = '/changes/{}/abandon'.format(change_id)
        data = json.dumps({})
        try:
            return self._exec(api_name, method='POST', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def restore_change(self, change_id):
        api_name = '/changes/{}/restore'.format(change_id)
        data = json.dumps({})
        try:
            return self._exec(api_name, method='POST', data=data)
        except Exception:
            logger.error(traceback.format_exc())
            return False


    def get_email_from_user(self, account_name):
        api_name = '/accounts/?q=name:{}'.format(account_name)
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False


    def remove_from_group(self, user_id):
        try:
            data = self.get_account_groups(user_id)
            if data is False:
                logger.error(f"Failed to get account groups for user ID: {user_id}")
                return False

            group_ids = [item['name'] for item in data if 'group_id' in item]
            logger.info(f'所属组：{group_ids}')
            if not group_ids:
                logger.info("该用户不属于任何组")
            else:
                for group_id in group_ids:
                    if self.remove_group_members("{}".format(group_id), ["{}".format(user_id)]):
                        logger.info("SUCCESS：{}从{}删除".format(user_id, group_id))
                    else:
                        logger.error("FAILED:{}从{}删除".format(user_id, group_id))
                        return False
            return True
        except Exception:
            logger.error(traceback.format_exc())
            return False
        

if __name__ == '__main__':
    print('###########################################')
    obj = GerritReq()
    # res = obj.create_project('Access/ICDC', parent='All-Projects', permissions_only=True)
    # print(res)

    res = obj.remove_from_group('example@example.com')
    print(res)

    # print(obj.add_group_members('Administrators', ['qianhui@hozonauto.com']))

    # res = obj.list_projects()
    # err_list = []
    # dest_parent = 'Access/IT'
    # i = 0
    # for gitname in res:
    #     if gitname[:3] == 'IT/':
    #         i += 1
    #         print(f'{i} >>>>>>', gitname)
    #         rlt = obj.update_project_parent(gitname, dest_parent)
    #         print(rlt)
    #         if not rlt:
    #             err_list.append(gitname)
    # print(err_list)

    # err_list = []
    # res = obj.list_groups()
    # for group in res:
    #     if 'Admin' in group or 'CDCS_' in group or 'Global_' in group or group in ['Service Users']:
    #         print('>>>>>>', group)
    #         continue
    #     print(group)
    #     group_id = res.get(group).get('id')
    #     members = obj.list_group_members(group_id)
    #     if not members:
    #         continue
    #     mem_list = []
    #     for item in members:
    #         mem_list.append(item.get('_account_id'))
    #     if not obj.remove_group_members(group_id, mem_list):
    #         err_list.append(group)
    # print(err_list)


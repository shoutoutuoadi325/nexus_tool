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
import mimetypes
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib
import zipfile

PUBLIC_LIBS_PATH = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(PUBLIC_LIBS_PATH)
from refs.env_config import EnvConfig

# 延迟导入邮件通知器，避免循环导入
def get_email_notifier():
    """获取邮件通知器实例"""
    try:
        from refs.email_notifier import EmailNotifier
        return EmailNotifier()
    except ImportError:
        logger.warning("邮件通知模块未找到，将跳过邮件通知功能")
        return None


class NexusReq(object):
    def __init__(self, default_account='admin', default_nexus='nexus', enable_email_notification=False, notification_recipients=None):
        self._check_succ_code = [200, 201, 204, 302]
        self._def_account = default_account
        self.enable_email_notification = enable_email_notification
        self.notification_recipients = notification_recipients or []
        
        if default_nexus == 'nexus':
            self.domain = EnvConfig.NEXUS_INFO['domain']
            self.root_url = EnvConfig.NEXUS_INFO['root_url']
            self.accounts = EnvConfig.NEXUS_INFO['accounts']
        
        # 初始化SAST配置
        self.sast_config = EnvConfig.SAST_INFO
        
        # 初始化邮件通知器
        self.email_notifier = None
        if self.enable_email_notification:
            self.email_notifier = get_email_notifier()
            if not self.email_notifier:
                logger.warning("邮件通知功能初始化失败，将禁用邮件通知")
                self.enable_email_notification = False

    def _exec(self, api_name, data=None, method='GET', account=None, timeout=120, return_json=True, headers=None, files=None):
        """执行HTTP请求的核心方法"""
        if not account:
            account = self._def_account
        
        # 构建完整的API URL
        if api_name.startswith('/service/rest'):
            api_url = f'{self.root_url}{api_name}'
        else:
            api_url = f'{self.root_url}/service/rest/v1{api_name}'
        
        # 设置认证信息
        auth = HTTPBasicAuth(
            self.accounts[account]['username'], 
            self.accounts[account]['password']
        )
        
        # 设置默认请求头
        if not headers:
            headers = {}
            if method in ['POST', 'PUT'] and not files:
                headers['Content-Type'] = 'application/json'
        
        try:
            logger.debug(f'nexus api: {method} | {api_url}')
            res = requests.request(
                method=method, 
                url=api_url, 
                data=data, 
                auth=auth, 
                headers=headers, 
                timeout=timeout,
                files=files
            )
            logger.debug(f'response code: {res.status_code}')
            
            if res.status_code not in self._check_succ_code:
                logger.error(f'{res.status_code} | {res.text}')
                return False
            
            if return_json and res.text:
                try:
                    return res.json()
                except json.JSONDecodeError:
                    return res.text
            
            if res.status_code == 302:  # 重定向用于下载
                return res.headers.get('Location', res.url)
            
            return True
            
        except Exception as e:
            logger.error(f'Request failed: {traceback.format_exc()}')
            return False

    def _send_notification(self, operation, success, details=None, error_message=None, user=None, **kwargs):
        """发送邮件通知"""
        if not self.enable_email_notification or not self.email_notifier or not self.notification_recipients:
            return
        
        try:
            current_user = user or self.accounts.get(self._def_account, {}).get('username', 'system')
            
            if success:
                self.email_notifier.send_success_notification(
                    recipients=self.notification_recipients,
                    operation=operation,
                    user=current_user,
                    details=details,
                    **kwargs
                )
            else:
                self.email_notifier.send_failure_notification(
                    recipients=self.notification_recipients,
                    operation=operation,
                    user=current_user,
                    error_message=error_message,
                    details=details
                )
        except Exception as e:
            logger.warning(f"邮件通知发送失败: {e}")

    def _validate_sast_file(self, file_path):
        """验证SAST文件"""
        if not os.path.exists(file_path):
            return False, "文件不存在"
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.sast_config['supported_formats']:
            return False, f"不支持的文件格式: {file_ext}"
        
        file_size = os.path.getsize(file_path)
        if file_size > self.sast_config['max_file_size']:
            return False, f"文件大小超过限制: {file_size} > {self.sast_config['max_file_size']}"
        
        return True, "文件验证通过"

    def _get_file_info(self, file_path):
        """获取文件信息"""
        file_stat = os.stat(file_path)
        return {
            'name': os.path.basename(file_path),
            'size': self._format_file_size(file_stat.st_size),
            'type': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
            'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }

    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"

    '''
    ############################## Component APIs ##############################
    '''

    def list_components(self, repository, continuation_token=None, limit=100):
        """列出仓库中的组件"""
        api_name = '/components'
        params = {
            'repository': repository
        }
        if continuation_token:
            params['continuationToken'] = continuation_token
        
        # 构建查询参数
        query_string = urllib.parse.urlencode(params)
        api_name_with_params = f'{api_name}?{query_string}'
        
        try:
            return self._exec(api_name_with_params, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_component(self, component_id):
        """获取单个组件的详细信息"""
        api_name = f'/components/{component_id}'
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def delete_component(self, component_id):
        """删除组件"""
        api_name = f'/components/{component_id}'
        try:
            return self._exec(api_name, method='DELETE', return_json=False)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def upload_maven_component(self, repository, group_id, artifact_id, version, 
                             jar_file=None, pom_file=None, sources_file=None, 
                             javadoc_file=None, generate_pom=False, packaging='jar'):
        """上传Maven组件"""
        operation = "Maven组件上传"
        component_name = f"{group_id}:{artifact_id}:{version}"
        
        api_name = f'/components?repository={repository}'
        
        files = {}
        data = {
            'maven2.groupId': group_id,
            'maven2.artifactId': artifact_id,
            'maven2.version': version,
            'maven2.packaging': packaging,
            'maven2.generate-pom': str(generate_pom).lower()
        }
        
        asset_count = 1
        uploaded_files = []
        
        # 添加主jar文件
        if jar_file:
            files[f'maven2.asset{asset_count}'] = open(jar_file, 'rb')
            data[f'maven2.asset{asset_count}.extension'] = 'jar'
            uploaded_files.append(jar_file)
            asset_count += 1
        
        # 添加POM文件
        if pom_file:
            files[f'maven2.asset{asset_count}'] = open(pom_file, 'rb')
            data[f'maven2.asset{asset_count}.extension'] = 'pom'
            uploaded_files.append(pom_file)
            asset_count += 1
        
        # 添加源码文件
        if sources_file:
            files[f'maven2.asset{asset_count}'] = open(sources_file, 'rb')
            data[f'maven2.asset{asset_count}.extension'] = 'jar'
            data[f'maven2.asset{asset_count}.classifier'] = 'sources'
            uploaded_files.append(sources_file)
            asset_count += 1
        
        # 添加javadoc文件
        if javadoc_file:
            files[f'maven2.asset{asset_count}'] = open(javadoc_file, 'rb')
            data[f'maven2.asset{asset_count}.extension'] = 'jar'
            data[f'maven2.asset{asset_count}.classifier'] = 'javadoc'
            uploaded_files.append(javadoc_file)
            asset_count += 1
        
        try:
            result = self._exec(api_name, data=data, method='POST', files=files, return_json=False)
            
            # 发送邮件通知
            details = {
                '仓库': repository,
                '组件': component_name,
                'GroupId': group_id,
                'ArtifactId': artifact_id,
                '版本': version,
                '打包类型': packaging,
                '上传文件数': len(uploaded_files),
                '文件列表': ', '.join([os.path.basename(f) for f in uploaded_files])
            }
            
            if result:
                self._send_notification(operation, True, details=details)
                logger.info(f"Maven组件上传成功: {component_name}")
            else:
                self._send_notification(operation, False, details=details, error_message="上传请求失败")
                
            return result
            
        except Exception as e:
            error_msg = f"上传过程中发生异常: {str(e)}"
            logger.error(traceback.format_exc())
            
            # 发送失败通知
            details = {
                '仓库': repository,
                '组件': component_name,
                '错误类型': type(e).__name__
            }
            self._send_notification(operation, False, details=details, error_message=error_msg)
            return False
            
        finally:
            # 关闭所有文件句柄
            for file_handle in files.values():
                file_handle.close()

    def upload_raw_component(self, repository, directory, local_files):
        """上传Raw格式的组件"""
        operation = "Raw组件上传"
        
        api_name = f'/components?repository={repository}'
        
        files = {}
        data = {
            'raw.directory': directory
        }
        
        if isinstance(local_files, str):
            local_files = [local_files]
        
        uploaded_files = []
        for index, file_path in enumerate(local_files, 1):
            file_name = os.path.basename(file_path)
            files[f'raw.asset{index}'] = open(file_path, 'rb')
            data[f'raw.asset{index}.filename'] = file_name
            uploaded_files.append(file_name)
        
        try:
            result = self._exec(api_name, data=data, method='POST', files=files, return_json=False)
            
            # 发送邮件通知
            details = {
                '仓库': repository,
                '目录': directory,
                '文件数量': len(local_files),
                '文件列表': ', '.join(uploaded_files)
            }
            
            if result:
                self._send_notification(operation, True, details=details)
                logger.info(f"Raw组件上传成功: {directory}")
            else:
                self._send_notification(operation, False, details=details, error_message="上传请求失败")
                
            return result
            
        except Exception as e:
            error_msg = f"上传过程中发生异常: {str(e)}"
            logger.error(traceback.format_exc())
            
            # 发送失败通知
            details = {
                '仓库': repository,
                '目录': directory,
                '错误类型': type(e).__name__
            }
            self._send_notification(operation, False, details=details, error_message=error_msg)
            return False
            
        finally:
            # 关闭所有文件句柄
            for file_handle in files.values():
                file_handle.close()

    def upload_npm_component(self, repository, npm_package_file):
        """上传NPM包"""
        api_name = f'/components?repository={repository}'
        
        files = {
            'npm.asset': open(npm_package_file, 'rb')
        }
        
        try:
            result = self._exec(api_name, method='POST', files=files, return_json=False)
            return result
        except Exception:
            logger.error(traceback.format_exc())
            return False
        finally:
            files['npm.asset'].close()

    '''
    ############################## Asset APIs ##############################
    '''

    def list_assets(self, repository, continuation_token=None):
        """列出仓库中的资产"""
        api_name = '/assets'
        params = {
            'repository': repository
        }
        if continuation_token:
            params['continuationToken'] = continuation_token
        
        query_string = urllib.parse.urlencode(params)
        api_name_with_params = f'{api_name}?{query_string}'
        
        try:
            return self._exec(api_name_with_params, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_asset(self, asset_id):
        """获取单个资产的详细信息"""
        api_name = f'/assets/{asset_id}'
        try:
            return self._exec(api_name)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def delete_asset(self, asset_id):
        """删除资产"""
        api_name = f'/assets/{asset_id}'
        try:
            return self._exec(api_name, method='DELETE', return_json=False)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def download_asset(self, asset_id, save_path=None):
        """下载资产"""
        # 首先获取资产信息
        asset_info = self.get_asset(asset_id)
        if not asset_info:
            return False
        
        download_url = asset_info.get('downloadUrl')
        if not download_url:
            logger.error('Asset download URL not found')
            return False
        
        try:
            # 直接下载文件
            auth = HTTPBasicAuth(
                self.accounts[self._def_account]['username'], 
                self.accounts[self._def_account]['password']
            )
            
            response = requests.get(download_url, auth=auth, stream=True)
            if response.status_code == 200:
                # 如果没有指定保存路径，从资产信息中获取文件名
                if not save_path:
                    filename = os.path.basename(asset_info.get('path', f'asset_{asset_id}'))
                    save_path = filename
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f'Asset downloaded successfully: {save_path}')
                return save_path
            else:
                logger.error(f'Download failed: {response.status_code}')
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## Search APIs ##############################
    '''

    def search_components(self, repository=None, group=None, name=None, version=None, 
                         format_type=None, continuation_token=None, **kwargs):
        """搜索组件"""
        api_name = '/search'
        params = {}
        
        if repository:
            params['repository'] = repository
        if group:
            params['group'] = group
        if name:
            params['name'] = name
        if version:
            params['version'] = version
        if format_type:
            params['format'] = format_type
        if continuation_token:
            params['continuationToken'] = continuation_token
        
        # 添加其他自定义参数（如maven.extension等）
        params.update(kwargs)
        
        query_string = urllib.parse.urlencode(params)
        api_name_with_params = f'{api_name}?{query_string}'
        
        try:
            return self._exec(api_name_with_params, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def search_assets(self, repository=None, group=None, name=None, version=None, 
                     format_type=None, continuation_token=None, **kwargs):
        """搜索资产"""
        api_name = '/search/assets'
        params = {}
        
        if repository:
            params['repository'] = repository
        if group:
            params['group'] = group
        if name:
            params['name'] = name
        if version:
            params['version'] = version
        if format_type:
            params['format'] = format_type
        if continuation_token:
            params['continuationToken'] = continuation_token
        
        # 添加其他自定义参数
        params.update(kwargs)
        
        query_string = urllib.parse.urlencode(params)
        api_name_with_params = f'{api_name}?{query_string}'
        
        try:
            return self._exec(api_name_with_params, timeout=60)
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def search_and_download_asset(self, save_path=None, repository=None, group=None, 
                                 name=None, version=None, **kwargs):
        """搜索并下载资产"""
        api_name = '/search/assets/download'
        params = {}
        
        if repository:
            params['repository'] = repository
        if group:
            params['group'] = group
        if name:
            params['name'] = name
        if version:
            params['version'] = version
        
        # 添加其他搜索参数
        params.update(kwargs)
        
        query_string = urllib.parse.urlencode(params)
        api_name_with_params = f'{api_name}?{query_string}'
        
        try:
            # 这个API会返回302重定向到下载URL
            download_url = self._exec(api_name_with_params, return_json=False)
            if download_url and download_url != True:
                # 执行实际下载
                auth = HTTPBasicAuth(
                    self.accounts[self._def_account]['username'], 
                    self.accounts[self._def_account]['password']
                )
                
                response = requests.get(download_url, auth=auth, stream=True)
                if response.status_code == 200:
                    # 如果没有指定保存路径，从URL中推断文件名
                    if not save_path:
                        filename = os.path.basename(urllib.parse.urlparse(download_url).path)
                        save_path = filename
                    
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f'Asset downloaded successfully: {save_path}')
                    return save_path
                else:
                    logger.error(f'Download failed: {response.status_code}')
                    return False
            return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def download_latest_version(self, repository, group, name, extension='jar', 
                               classifier=None, save_path=None):
        """下载最新版本的资产"""
        params = {
            'sort': 'version',
            'repository': repository,
            'group': group,
            'name': name,
            'maven.extension': extension
        }
        
        if classifier:
            params['maven.classifier'] = classifier
        else:
            params['maven.classifier'] = ''  # 空分类器
        
        return self.search_and_download_asset(save_path, **params)

    '''
    ############################## Batch Operations ##############################
    '''

    def batch_download_assets(self, asset_list, download_dir='./downloads', max_workers=5):
        """批量下载资产
        
        Args:
            asset_list: 资产列表，每个元素应包含asset_id和filename（可选）
            download_dir: 下载目录
            max_workers: 最大并发数
        """
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        def download_single_asset(asset_info):
            if isinstance(asset_info, str):
                asset_id = asset_info
                filename = None
            else:
                asset_id = asset_info.get('asset_id') or asset_info.get('id')
                filename = asset_info.get('filename')
            
            if filename:
                save_path = os.path.join(download_dir, filename)
            else:
                save_path = None
            
            result = self.download_asset(asset_id, save_path)
            return asset_id, result
        
        results = {}
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_asset = {executor.submit(download_single_asset, asset): asset 
                                  for asset in asset_list}
                
                for future in concurrent.futures.as_completed(future_to_asset):
                    asset = future_to_asset[future]
                    try:
                        asset_id, result = future.result()
                        results[asset_id] = result
                        if result:
                            logger.info(f'Successfully downloaded asset: {asset_id}')
                        else:
                            logger.error(f'Failed to download asset: {asset_id}')
                    except Exception as exc:
                        asset_id = asset.get('id') if isinstance(asset, dict) else asset
                        logger.error(f'Asset {asset_id} generated an exception: {exc}')
                        results[asset_id] = False
        except Exception:
            logger.error(traceback.format_exc())
            return False
        
        return results

    def batch_delete_components(self, component_ids, max_workers=3):
        """批量删除组件"""
        def delete_single_component(component_id):
            return component_id, self.delete_component(component_id)
        
        results = {}
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_component = {executor.submit(delete_single_component, comp_id): comp_id 
                                      for comp_id in component_ids}
                
                for future in concurrent.futures.as_completed(future_to_component):
                    component_id = future_to_component[future]
                    try:
                        comp_id, result = future.result()
                        results[comp_id] = result
                        if result:
                            logger.info(f'Successfully deleted component: {comp_id}')
                        else:
                            logger.error(f'Failed to delete component: {comp_id}')
                    except Exception as exc:
                        logger.error(f'Component {component_id} deletion generated an exception: {exc}')
                        results[component_id] = False
        except Exception:
            logger.error(traceback.format_exc())
            return False
        
        return results

    '''
    ############################## Repository Management ##############################
    '''

    def move_component_between_repositories(self, source_repo, target_repo, component_id):
        """在仓库间移动组件（通过下载再上传实现）"""
        try:
            # 获取组件信息
            component = self.get_component(component_id)
            if not component:
                logger.error(f'Failed to get component info: {component_id}')
                return False
            
            # 下载所有资产
            assets = component.get('assets', [])
            temp_files = []
            
            for asset in assets:
                asset_id = asset['id']
                temp_file = f"temp_{asset_id}_{os.path.basename(asset['path'])}"
                result = self.download_asset(asset_id, temp_file)
                if result:
                    temp_files.append((temp_file, asset))
                else:
                    logger.error(f'Failed to download asset: {asset_id}')
            
            if not temp_files:
                return False
            
            # 根据格式重新上传到目标仓库
            format_type = component.get('format')
            success = False
            
            if format_type == 'maven2':
                # Maven格式处理
                jar_file = None
                pom_file = None
                sources_file = None
                javadoc_file = None
                
                for temp_file, asset in temp_files:
                    path = asset['path']
                    if path.endswith('.jar'):
                        if 'sources' in path:
                            sources_file = temp_file
                        elif 'javadoc' in path:
                            javadoc_file = temp_file
                        else:
                            jar_file = temp_file
                    elif path.endswith('.pom'):
                        pom_file = temp_file
                
                success = self.upload_maven_component(
                    target_repo, 
                    component['group'], 
                    component['name'], 
                    component['version'],
                    jar_file=jar_file,
                    pom_file=pom_file,
                    sources_file=sources_file,
                    javadoc_file=javadoc_file
                )
            
            elif format_type == 'raw':
                # Raw格式处理
                file_list = [temp_file for temp_file, _ in temp_files]
                directory = os.path.dirname(assets[0]['path'])
                success = self.upload_raw_component(target_repo, directory, file_list)
            
            # 清理临时文件
            for temp_file, _ in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            if success:
                # 删除源组件
                delete_result = self.delete_component(component_id)
                if delete_result:
                    logger.info(f'Successfully moved component {component_id} from {source_repo} to {target_repo}')
                    return True
                else:
                    logger.warning(f'Component uploaded to {target_repo} but failed to delete from {source_repo}')
                    return True
            
            return False
            
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## Utility Methods ##############################
    '''

    def get_all_components_in_repository(self, repository):
        """获取仓库中的所有组件"""
        all_components = []
        continuation_token = None
        
        try:
            while True:
                result = self.list_components(repository, continuation_token)
                if not result:
                    break
                
                components = result.get('items', [])
                all_components.extend(components)
                
                continuation_token = result.get('continuationToken')
                if not continuation_token:
                    break
            
            return all_components
        except Exception:
            logger.error(traceback.format_exc())
            return []

    def cleanup_old_versions(self, repository, group, name, keep_latest_count=5):
        """清理旧版本，只保留最新的几个版本"""
        try:
            # 搜索所有版本
            components = self.search_components(
                repository=repository,
                group=group,
                name=name
            )
            
            if not components or not components.get('items'):
                return False
            
            # 按版本排序（这里简单按字符串排序，实际可能需要版本号比较逻辑）
            items = components['items']
            items.sort(key=lambda x: x.get('version', ''), reverse=True)
            
            # 删除超出保留数量的版本
            to_delete = items[keep_latest_count:]
            if to_delete:
                component_ids = [item['id'] for item in to_delete]
                return self.batch_delete_components(component_ids)
            
            return True
        except Exception:
            logger.error(traceback.format_exc())
            return False

    '''
    ############################## SAST工具文件上传 ##############################
    '''

    def upload_sast_report(self, project_name, sast_category='generic', files=None, 
                          repository=None, scan_date=None, additional_info=None,
                          create_zip=True):
        """上传SAST工具扫描报告
        
        Args:
            project_name: 项目名称
            sast_category: SAST工具类型 (sonar/checkmarx/fortify/coverity/veracode/generic)
            files: 要上传的文件列表 (可以是单个文件或文件列表)
            repository: 目标仓库 (默认使用配置的SAST仓库)
            scan_date: 扫描日期 (YYYY-MM-DD格式)
            additional_info: 附加信息字典
            create_zip: 是否将多个文件打包成zip
        """
        operation = "SAST工具资料上传"
        
        if not files:
            logger.error("未指定要上传的文件")
            return False
        
        if isinstance(files, str):
            files = [files]
        
        # 验证文件
        validated_files = []
        for file_path in files:
            is_valid, msg = self._validate_sast_file(file_path)
            if not is_valid:
                error_msg = f"文件验证失败 {file_path}: {msg}"
                logger.error(error_msg)
                self._send_notification(operation, False, 
                                      details={'项目': project_name, 'SAST工具': sast_category}, 
                                      error_message=error_msg)
                return False
            validated_files.append(file_path)
        
        # 设置默认仓库
        if not repository:
            repository = self.sast_config['default_repository']
        
        # 设置扫描日期
        if not scan_date:
            scan_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 构建目录路径
            sast_category_name = self.sast_config['categories'].get(sast_category, sast_category)
            directory_path = f"{project_name}/{sast_category}/{scan_date}"
            
            upload_files = validated_files
            
            # 如果有多个文件且需要打包
            if len(validated_files) > 1 and create_zip:
                zip_filename = f"{project_name}_{sast_category}_{scan_date}.zip"
                zip_path = os.path.join(os.path.dirname(validated_files[0]), zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in validated_files:
                        zipf.write(file_path, os.path.basename(file_path))
                
                upload_files = [zip_path]
                logger.info(f"已创建压缩包: {zip_path}")
            
            # 上传文件
            results = []
            file_infos = []
            
            for file_path in upload_files:
                # 构建文件在仓库中的路径
                filename = os.path.basename(file_path)
                file_directory = f"{directory_path}/{filename}"
                
                # 上传单个文件
                result = self.upload_raw_component(repository, file_directory, file_path)
                results.append(result)
                
                # 收集文件信息用于通知
                file_infos.append(self._get_file_info(file_path))
                
                if result:
                    logger.info(f"SAST文件上传成功: {filename}")
                else:
                    logger.error(f"SAST文件上传失败: {filename}")
            
            # 清理临时zip文件
            if len(validated_files) > 1 and create_zip and upload_files != validated_files:
                try:
                    os.remove(upload_files[0])  # 删除临时zip文件
                except:
                    pass
            
            # 判断整体上传结果
            success = all(results)
            
            # 准备通知详情
            details = {
                '项目名称': project_name,
                'SAST工具': f"{sast_category_name} ({sast_category})",
                '扫描日期': scan_date,
                '目标仓库': repository,
                '上传路径': directory_path,
                '文件数量': len(validated_files),
                '成功数量': sum(1 for r in results if r),
                '失败数量': sum(1 for r in results if not r)
            }
            
            if additional_info:
                details.update(additional_info)
            
            # 构建下载URL (如果有成功上传的文件)
            download_url = None
            if success and upload_files:
                filename = os.path.basename(upload_files[0])
                download_url = f"{self.root_url}/repository/{repository}/{directory_path}/{filename}"
            
            # 发送邮件通知
            if success:
                self._send_notification(operation, True, details=details)
                
                # 发送SAST专用通知
                if self.email_notifier and self.notification_recipients:
                    self.email_notifier.send_sast_upload_notification(
                        recipients=self.notification_recipients,
                        component=project_name,
                        repository=repository,
                        sast_category=sast_category_name,
                        files=file_infos,
                        download_url=download_url,
                        scan_date=scan_date,
                        project_name=project_name,
                        message=f"成功上传{len(file_infos)}个SAST报告文件"
                    )
            else:
                error_msg = f"部分或全部文件上传失败，成功: {sum(1 for r in results if r)}/{len(results)}"
                self._send_notification(operation, False, details=details, error_message=error_msg)
            
            return success
            
        except Exception as e:
            error_msg = f"SAST文件上传过程中发生异常: {str(e)}"
            logger.error(traceback.format_exc())
            
            details = {
                '项目名称': project_name,
                'SAST工具': sast_category,
                '错误类型': type(e).__name__
            }
            self._send_notification(operation, False, details=details, error_message=error_msg)
            return False

    def batch_upload_sast_reports(self, sast_configs):
        """批量上传SAST报告
        
        Args:
            sast_configs: SAST配置列表，每个元素包含upload_sast_report的参数
        """
        results = []
        
        logger.info(f"开始批量上传{len(sast_configs)}个SAST报告")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for config in sast_configs:
                future = executor.submit(self.upload_sast_report, **config)
                futures.append((future, config.get('project_name', 'Unknown')))
            
            for future, project_name in futures:
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    results.append(result)
                    
                    if result:
                        logger.info(f"项目 {project_name} SAST报告上传成功")
                    else:
                        logger.error(f"项目 {project_name} SAST报告上传失败")
                        
                except Exception as e:
                    logger.error(f"项目 {project_name} SAST报告上传异常: {e}")
                    results.append(False)
        
        success_count = sum(1 for r in results if r)
        
        # 发送批量操作汇总通知
        if self.enable_email_notification:
            details = {
                '总项目数': len(sast_configs),
                '成功数量': success_count,
                '失败数量': len(results) - success_count,
                '成功率': f"{success_count/len(results)*100:.1f}%"
            }
            
            self._send_notification(
                "批量SAST报告上传",
                success_count == len(results),
                details=details,
                error_message=f"部分项目上传失败" if success_count < len(results) else None
            )
        
        logger.info(f"批量SAST报告上传完成: {success_count}/{len(results)} 成功")
        return results

    def list_sast_reports(self, project_name=None, sast_category=None, repository=None):
        """列出SAST报告
        
        Args:
            project_name: 项目名称 (可选)
            sast_category: SAST工具类型 (可选)
            repository: 仓库名称 (可选)
        """
        if not repository:
            repository = self.sast_config['default_repository']
        
        try:
            # 构建搜索路径
            search_path = ""
            if project_name:
                search_path = project_name
                if sast_category:
                    search_path += f"/{sast_category}"
            
            # 获取所有组件
            components = self.get_all_components_in_repository(repository)
            
            # 过滤SAST相关组件
            sast_components = []
            for component in components:
                component_name = component.get('name', '')
                
                if search_path and not component_name.startswith(search_path):
                    continue
                
                # 检查是否为SAST相关文件
                assets = component.get('assets', [])
                for asset in assets:
                    file_ext = os.path.splitext(asset.get('path', ''))[-1].lower()
                    if file_ext in self.sast_config['supported_formats']:
                        sast_components.append(component)
                        break
            
            return sast_components
            
        except Exception as e:
            logger.error(f"列出SAST报告失败: {traceback.format_exc()}")
            return []

    def download_sast_report(self, project_name, sast_category, scan_date, 
                           filename=None, repository=None, download_dir=None):
        """下载SAST报告
        
        Args:
            project_name: 项目名称
            sast_category: SAST工具类型
            scan_date: 扫描日期
            filename: 文件名 (可选，如果不指定则下载目录下所有文件)
            repository: 仓库名称 (可选)
            download_dir: 下载目录 (可选)
        """
        if not repository:
            repository = self.sast_config['default_repository']
        
        if not download_dir:
            download_dir = os.path.join(os.getcwd(), 'sast_downloads', project_name, sast_category, scan_date)
        
        try:
            # 构建搜索路径
            search_path = f"{project_name}/{sast_category}/{scan_date}"
            
            if filename:
                # 下载特定文件
                file_path = f"{search_path}/{filename}"
                return self.download_asset_by_path(repository, file_path, download_dir)
            else:
                # 下载目录下所有文件
                components = self.list_sast_reports(project_name, sast_category, repository)
                
                downloaded_files = []
                for component in components:
                    component_name = component.get('name', '')
                    if component_name.startswith(search_path):
                        assets = component.get('assets', [])
                        for asset in assets:
                            asset_path = asset.get('path', '')
                            if asset_path.startswith(search_path):
                                result = self.download_asset_by_path(repository, asset_path, download_dir)
                                if result:
                                    downloaded_files.append(asset_path)
                
                return downloaded_files
                
        except Exception as e:
            logger.error(f"下载SAST报告失败: {traceback.format_exc()}")
            return False


if __name__ == '__main__':
    # 示例用法
    nexus = NexusReq()
    
    # 列出组件
    # components = nexus.list_components('maven-releases')
    # print(json.dumps(components, indent=2))
    
    # 搜索组件
    # search_result = nexus.search_components(repository='maven-central', group='org.springframework')
    # print(json.dumps(search_result, indent=2))
    
    # 下载最新版本
    # nexus.download_latest_version('maven-central', 'org.springframework', 'spring-core')

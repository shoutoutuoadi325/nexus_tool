# -*- coding: utf-8 -*-

import os
import traceback
from loguru import logger


class EnvConfig(object):
    JENKINS_INFO = {
        'jenkins_new': {
            'root_url': '',
            'jenkins_user': '',
            'jenkins_api_token': ''
        }
    }

    FEISHU_INFO = {
        'root_url': 'https://open.feishu.cn',
        'accounts': {
            'feishu_PkgUpload': {
                'app_id': 'cli_aaaaaaaaaaaaaaaa',
                'app_secret': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
            },
            'feishu_TianGong': {
                'app_id': 'cli_bbbbbbbbbbbbbbb',
                'app_secret': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
            }
        }
    }

    OA_LDAP_INFO = {
        'host': '',
        'port': 389,
        'user': '',
        'pwd': '',
        'base_dn': ''
    }

    ARTIFACTORY_INFO = {
        'root_url': '',
        'user_name': '',
        'user_pwd': '',
        'api_version': 1
    }

    FTP_INFO = {
        "shanghai": {
            'host': '',
            'port': 2112,
            'user': '',
            'pwd': ''
        },
        "beijing": {
            'host': '',
            'port': 21,
            'user': '',
            'pwd': ''
        }

    }
    GERRIT_INFO = {
        'domain': 'gerrit.archermind.com.cn',
        'root_url': 'http://gerrit.archermind.com.cn:8080',
        'accounts': {
            'svw-user': {
                'login_pwd': '',
                'http_pwd': ''
            },
            'scm-prebuild': {
                'login_pwd': '',
                'http_pwd': ''
            },
            'scm-coverity': {
                'login_pwd': '',
                'http_pwd': ''
            },
            'scm-sonar': {
                'login_pwd': '',
                'http_pwd': ''
            },
            'scm-whitelist': {
                'login_pwd': '',
                'http_pwd': ''
            }

        }
    }

    NEXUS_INFO = {
        'domain': 'nexus.example.com',
        'root_url': 'http://nexus.example.com:8081',
        'accounts': {
            'admin': {
                'username': 'admin',
                'password': 'admin123'
            },
            'deploy-user': {
                'username': 'deploy',
                'password': 'deploy123'
            }
        }
    }

    # SMTP邮件配置
    SMTP_INFO = {
        'smtp_server': 'smtp.gmail.com',  # SMTP服务器地址
        'smtp_port': 587,  # SMTP端口
        'use_tls': True,  # 是否使用TLS
        'accounts': {
            'default': {
                'username': 'your-email@gmail.com',  # 发送邮箱
                'password': 'your-app-password',  # 邮箱密码或应用密码
                'from_name': 'Nexus Notification System'  # 发送者名称
            }
        },
        'templates': {
            'success': {
                'subject': 'Nexus操作成功通知 - {operation}',
                'template_file': 'email_success.html'
            },
            'failure': {
                'subject': 'Nexus操作失败通知 - {operation}',
                'template_file': 'email_failure.html'
            },
            'sast_upload': {
                'subject': 'SAST工具资料上传通知 - {component}',
                'template_file': 'email_sast_upload.html'
            }
        }
    }

    # SAST工具配置
    SAST_INFO = {
        'supported_formats': ['.pdf', '.doc', '.docx', '.txt', '.md', '.html', '.xml', '.json'],
        'max_file_size': 50 * 1024 * 1024,  # 50MB
        'repository_prefix': 'sast-reports',  # SAST报告仓库前缀
        'default_repository': 'sast-reports-raw',  # 默认SAST报告仓库
        'categories': {
            'sonar': 'SonarQube报告',
            'checkmarx': 'Checkmarx报告', 
            'fortify': 'Fortify报告',
            'coverity': 'Coverity报告',
            'veracode': 'Veracode报告',    
            'generic': '通用SAST报告'
        }
    }


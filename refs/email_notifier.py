# -*- coding: utf-8 -*-

import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from typing import List, Dict, Optional
from loguru import logger
import traceback
from datetime import datetime
import jinja2

PUBLIC_LIBS_PATH = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(PUBLIC_LIBS_PATH)
from refs.env_config import EnvConfig


class EmailNotifier:
    """邮件通知类 - 按照gerrit_req模式实现"""
    
    def __init__(self, default_account='default'):
        """初始化邮件通知器"""
        self._def_account = default_account
        self.smtp_config = EnvConfig.SMTP_INFO
        self.templates_dir = os.path.join(PUBLIC_LIBS_PATH, '..', 'templates')
        
        # 确保模板目录存在
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            self._create_default_templates()
        
        # 初始化Jinja2模板环境
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.templates_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def _create_default_templates(self):
        """创建默认邮件模板"""
        # 成功模板
        success_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>操作成功通知</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #28a745; color: white; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { color: #6c757d; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>✅ Nexus操作成功</h2>
    </div>
    <div class="content">
        <p><strong>操作类型:</strong> {{ operation }}</p>
        <p><strong>执行时间:</strong> {{ timestamp }}</p>
        <p><strong>操作者:</strong> {{ user }}</p>
        
        {% if details %}
        <div class="details">
            <h3>操作详情:</h3>
            {% for key, value in details.items() %}
            <p><strong>{{ key }}:</strong> {{ value }}</p>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if message %}
        <p><strong>附加信息:</strong> {{ message }}</p>
        {% endif %}
    </div>
    <div class="footer">
        <p>此邮件由Nexus自动化系统发送，请勿回复。</p>
        <p>发送时间: {{ timestamp }}</p>
    </div>
</body>
</html>
        """
        
        # 失败模板
        failure_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>操作失败通知</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #dc3545; color: white; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { color: #6c757d; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>❌ Nexus操作失败</h2>
    </div>
    <div class="content">
        <p><strong>操作类型:</strong> {{ operation }}</p>
        <p><strong>失败时间:</strong> {{ timestamp }}</p>
        <p><strong>操作者:</strong> {{ user }}</p>
        
        {% if error_message %}
        <div class="error">
            <h3>错误信息:</h3>
            <p>{{ error_message }}</p>
        </div>
        {% endif %}
        
        {% if details %}
        <div class="details">
            <h3>操作详情:</h3>
            {% for key, value in details.items() %}
            <p><strong>{{ key }}:</strong> {{ value }}</p>
            {% endfor %}
        </div>
        {% endif %}
        
        <p><strong>建议:</strong> 请检查配置和权限设置，或联系系统管理员。</p>
    </div>
    <div class="footer">
        <p>此邮件由Nexus自动化系统发送，请勿回复。</p>
        <p>发送时间: {{ timestamp }}</p>
    </div>
</body>
</html>
        """
        
        # SAST上传模板
        sast_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SAST工具资料上传通知</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #17a2b8; color: white; padding: 15px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .sast-info { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .file-list { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { color: #6c757d; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>🛡️ SAST工具资料上传通知</h2>
    </div>
    <div class="content">
        <p><strong>组件名称:</strong> {{ component }}</p>
        <p><strong>上传时间:</strong> {{ timestamp }}</p>
        <p><strong>上传者:</strong> {{ user }}</p>
        <p><strong>仓库:</strong> {{ repository }}</p>
        
        {% if sast_category %}
        <div class="sast-info">
            <h3>SAST工具信息:</h3>
            <p><strong>工具类型:</strong> {{ sast_category }}</p>
            {% if scan_date %}<p><strong>扫描日期:</strong> {{ scan_date }}</p>{% endif %}
            {% if project_name %}<p><strong>项目名称:</strong> {{ project_name }}</p>{% endif %}
        </div>
        {% endif %}
        
        {% if files %}
        <div class="file-list">
            <h3>上传文件列表:</h3>
            <ul>
            {% for file in files %}
                <li><strong>{{ file.name }}</strong> ({{ file.size }}) - {{ file.type }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        {% if download_url %}
        <p><strong>下载地址:</strong> <a href="{{ download_url }}">{{ download_url }}</a></p>
        {% endif %}
        
        {% if message %}
        <p><strong>附加信息:</strong> {{ message }}</p>
        {% endif %}
    </div>
    <div class="footer">
        <p>此邮件由Nexus自动化系统发送，请勿回复。</p>
        <p>发送时间: {{ timestamp }}</p>
    </div>
</body>
</html>
        """
        
        # 写入模板文件
        with open(os.path.join(self.templates_dir, 'email_success.html'), 'w', encoding='utf-8') as f:
            f.write(success_template)
        
        with open(os.path.join(self.templates_dir, 'email_failure.html'), 'w', encoding='utf-8') as f:
            f.write(failure_template)
            
        with open(os.path.join(self.templates_dir, 'email_sast_upload.html'), 'w', encoding='utf-8') as f:
            f.write(sast_template)
    
    def _get_smtp_connection(self, account=None):
        """获取SMTP连接"""
        if not account:
            account = self._def_account
        
        account_info = self.smtp_config['accounts'][account]
        
        try:
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            
            if self.smtp_config.get('use_tls', True):
                server.starttls()
            
            server.login(account_info['username'], account_info['password'])
            return server
        except Exception as e:
            logger.error(f"SMTP连接失败: {e}")
            return None
    
    def _render_template(self, template_name, **kwargs):
        """渲染邮件模板"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return None
    
    def send_notification(self, template_type, recipients, operation, user='system', 
                         details=None, message=None, error_message=None, 
                         account=None, attachments=None, **kwargs):
        """发送通知邮件
        
        Args:
            template_type: 模板类型 (success/failure/sast_upload)
            recipients: 收件人列表
            operation: 操作类型
            user: 操作用户
            details: 操作详情字典
            message: 附加消息
            error_message: 错误消息
            account: 发送账户
            attachments: 附件列表
            **kwargs: 额外的模板参数
        """
        if not account:
            account = self._def_account
        
        if not isinstance(recipients, list):
            recipients = [recipients]
        
        try:
            # 获取模板配置
            template_config = self.smtp_config['templates'].get(template_type)
            if not template_config:
                logger.error(f"未找到模板类型: {template_type}")
                return False
            
            # 准备模板数据
            template_data = {
                'operation': operation,
                'user': user,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': details or {},
                'message': message,
                'error_message': error_message,
                **kwargs
            }
            
            # 渲染邮件内容
            html_content = self._render_template(template_config['template_file'], **template_data)
            if not html_content:
                return False
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = Header(f"{self.smtp_config['accounts'][account]['from_name']} <{self.smtp_config['accounts'][account]['username']}>", 'utf-8')
            msg['Subject'] = Header(template_config['subject'].format(operation=operation, **kwargs), 'utf-8')
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 添加附件
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(attachment_path)}'
                            )
                            msg.attach(part)
            
            # 发送邮件
            smtp_server = self._get_smtp_connection(account)
            if not smtp_server:
                return False
            
            for recipient in recipients:
                msg_copy = MIMEMultipart('alternative')
                for key, value in msg.items():
                    msg_copy[key] = value
                msg_copy['To'] = Header(recipient, 'utf-8')
                
                # 复制所有部分
                for part in msg.get_payload():
                    msg_copy.attach(part)
                
                smtp_server.send_message(msg_copy)
                logger.info(f"邮件发送成功: {recipient}")
            
            smtp_server.quit()
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {traceback.format_exc()}")
            return False
    
    def send_success_notification(self, recipients, operation, user='system', 
                                 details=None, message=None, account=None):
        """发送成功通知"""
        return self.send_notification(
            template_type='success',
            recipients=recipients,
            operation=operation,
            user=user,
            details=details,
            message=message,
            account=account
        )
    
    def send_failure_notification(self, recipients, operation, user='system', 
                                 error_message=None, details=None, account=None):
        """发送失败通知"""
        return self.send_notification(
            template_type='failure',
            recipients=recipients,
            operation=operation,
            user=user,
            error_message=error_message,
            details=details,
            account=account
        )
    
    def send_sast_upload_notification(self, recipients, component, repository, 
                                    user='system', sast_category=None, files=None, 
                                    download_url=None, scan_date=None, 
                                    project_name=None, message=None, account=None):
        """发送SAST上传通知"""
        return self.send_notification(
            template_type='sast_upload',
            recipients=recipients,
            operation='SAST工具资料上传',
            user=user,
            component=component,
            repository=repository,
            sast_category=sast_category,
            files=files or [],
            download_url=download_url,
            scan_date=scan_date,
            project_name=project_name,
            message=message,
            account=account
        )

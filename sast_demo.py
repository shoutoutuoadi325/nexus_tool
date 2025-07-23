#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SAST工具文件上传示例
演示如何使用Nexus工具上传SAST扫描报告并发送邮件通知
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from refs.nexus_req import NexusReq


def demo_sast_upload():
    """演示SAST工具报告上传功能"""
    print("=== SAST工具报告上传示例 ===\n")
    
    # 启用邮件通知的Nexus客户端
    nexus = NexusReq(
        default_account='admin',
        enable_email_notification=True,
        notification_recipients=['security-team@company.com', 'dev-team@company.com']
    )
    
    # 1. 单个SAST报告上传
    print("1. 上传单个SonarQube报告...")
    result1 = nexus.upload_sast_report(
        project_name='web-frontend',
        sast_category='sonar',
        files=['./examples/sonar-report.pdf'],  # 假设文件存在
        scan_date='2024-01-15',
        additional_info={
            '扫描类型': '全量扫描',
            '代码行数': '50000',
            '问题数量': '25个',
            '质量门禁': '通过'
        }
    )
    print(f"上传结果: {'✅ 成功' if result1 else '❌ 失败'}\n")
    
    # 2. 多文件SAST报告上传（自动打包）
    print("2. 上传多个Checkmarx报告文件...")
    result2 = nexus.upload_sast_report(
        project_name='api-backend',
        sast_category='checkmarx',
        files=[
            './examples/checkmarx-report.pdf',
            './examples/checkmarx-details.xml',
            './examples/checkmarx-summary.html'
        ],
        scan_date='2024-01-15',
        additional_info={
            '扫描类型': '增量扫描',
            '漏洞等级': 'High: 5, Medium: 12, Low: 8',
            '修复建议': '优先修复高危漏洞'
        },
        create_zip=True  # 自动创建zip压缩包
    )
    print(f"上传结果: {'✅ 成功' if result2 else '❌ 失败'}\n")
    
    # 3. 批量上传配置
    print("3. 批量上传多个项目的SAST报告...")
    batch_configs = [
        {
            'project_name': 'mobile-app',
            'sast_category': 'fortify',
            'files': ['./examples/fortify-report.pdf'],
            'scan_date': '2024-01-14',
            'additional_info': {
                '扫描版本': 'v2.1.0',
                '关键漏洞': '3个'
            }
        },
        {
            'project_name': 'desktop-client',
            'sast_category': 'coverity',
            'files': ['./examples/coverity-report.pdf'],
            'scan_date': '2024-01-14',
            'additional_info': {
                '缺陷密度': '0.5 defects/KLOC',
                '新增缺陷': '2个'
            }
        }
    ]
    
    results = nexus.batch_upload_sast_reports(batch_configs)
    success_count = sum(1 for r in results if r)
    print(f"批量上传结果: {success_count}/{len(results)} 成功\n")
    
    # 4. 列出已上传的SAST报告
    print("4. 列出web-frontend项目的SonarQube报告...")
    reports = nexus.list_sast_reports(
        project_name='web-frontend',
        sast_category='sonar'
    )
    
    if reports:
        print(f"找到 {len(reports)} 个报告:")
        for report in reports:
            print(f"  - {report.get('name', '')}")
            for asset in report.get('assets', []):
                print(f"    📄 {asset.get('path', '')} ({asset.get('size', 0)} bytes)")
    else:
        print("  未找到报告")
    
    print("\n=== 示例完成 ===")


def demo_email_notification():
    """演示邮件通知功能"""
    print("\n=== 邮件通知功能示例 ===\n")
    
    # 直接使用邮件通知器
    try:
        from refs.email_notifier import EmailNotifier
        
        email_notifier = EmailNotifier()
        
        # 发送成功通知
        print("1. 发送操作成功通知...")
        success = email_notifier.send_success_notification(
            recipients=['admin@company.com'],
            operation='Maven组件上传',
            user='developer01',
            details={
                '仓库': 'maven-releases',
                '组件': 'com.example:my-app:1.0.0',
                '文件数量': '3',
                '文件大小': '2.5MB'
            },
            message='所有文件上传成功，组件已可用'
        )
        print(f"邮件发送结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 发送SAST上传通知
        print("2. 发送SAST上传专用通知...")
        success = email_notifier.send_sast_upload_notification(
            recipients=['security-team@company.com'],
            component='web-frontend',
            repository='sast-reports-raw',
            sast_category='SonarQube报告',
            files=[
                {'name': 'sonar-report.pdf', 'size': '1.2 MB', 'type': 'application/pdf'},
                {'name': 'sonar-details.json', 'size': '45.6 KB', 'type': 'application/json'}
            ],
            download_url='http://nexus.example.com:8081/repository/sast-reports-raw/web-frontend/sonar/2024-01-15/',
            scan_date='2024-01-15',
            project_name='web-frontend',
            message='SonarQube扫描报告已上传，请及时查看和处理'
        )
        print(f"SAST通知发送结果: {'✅ 成功' if success else '❌ 失败'}")
        
    except ImportError:
        print("❌ 邮件通知模块未正确安装，请安装依赖: pip install jinja2")
    
    print("\n=== 邮件通知示例完成 ===")


def demo_cli_usage():
    """演示命令行工具的使用方法"""
    print("\n=== 命令行工具使用示例 ===\n")
    
    print("以下是新增的命令行使用方法：\n")
    
    print("1. 上传单个SAST报告：")
    print("python nexus_cli.py upload-sast web-frontend sonar report.pdf \\")
    print("    --scan-date 2024-01-15 \\")
    print("    --description '全量代码扫描报告' \\")
    print("    --email-recipients 'security@company.com,dev@company.com'\n")
    
    print("2. 上传多个SAST文件（不打包）：")
    print("python nexus_cli.py upload-sast api-backend checkmarx \\")
    print("    report.pdf details.xml summary.html \\")
    print("    --no-zip \\")
    print("    --email-recipients 'security@company.com'\n")
    
    print("3. 列出SAST报告：")
    print("python nexus_cli.py list-sast --project web-frontend --category sonar\n")
    
    print("4. 下载SAST报告：")
    print("python nexus_cli.py download-sast web-frontend sonar 2024-01-15 \\")
    print("    --output ./downloads/\n")
    
    print("5. 批量上传SAST报告：")
    print("python nexus_cli.py batch-upload-sast examples/batch_sast_config.json \\")
    print("    --email-recipients 'security@company.com'\n")
    
    print("6. Maven组件上传带邮件通知：")
    print("python nexus_cli.py upload-maven maven-releases \\")
    print("    com.example my-app 1.0.0 \\")
    print("    --jar my-app.jar --pom my-app.pom \\")
    print("    --email-recipients 'team@company.com'\n")
    
    print("=== 命令行示例完成 ===")


if __name__ == '__main__':
    print("Nexus SAST工具集成示例")
    print("=======================\n")
    
    # 注意：以下示例需要实际的文件存在才能运行
    # 这里只是演示代码结构
    
    try:
        # demo_sast_upload()
        demo_email_notification()
        demo_cli_usage()
        
    except Exception as e:
        print(f"❌ 示例运行出错: {e}")
        print("请确保配置正确且相关文件存在")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nexus Repository 命令行工具
提供常用的Nexus操作命令行接口
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from refs.nexus_req import NexusReq


def list_components_cmd(args):
    """列出组件命令"""
    nexus = NexusReq(default_account=args.account)
    
    print(f"正在列出仓库 '{args.repository}' 中的组件...")
    components = nexus.list_components(args.repository)
    
    if not components:
        print("❌ 获取组件列表失败")
        return False
    
    items = components.get('items', [])
    print(f"✅ 找到 {len(items)} 个组件:")
    
    for i, comp in enumerate(items[:args.limit], 1):
        group = comp.get('group', '')
        name = comp.get('name', '')
        version = comp.get('version', '')
        asset_count = len(comp.get('assets', []))
        
        print(f"  {i:3d}. {group}.{name}:{version} ({asset_count} assets)")
        if args.verbose:
            print(f"       ID: {comp.get('id', '')}")
            print(f"       Format: {comp.get('format', '')}")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(components, f, indent=2, ensure_ascii=False)
        print(f"📁 详细信息已保存到: {args.output}")
    
    return True


def search_components_cmd(args):
    """搜索组件命令"""
    nexus = NexusReq(default_account=args.account)
    
    print(f"正在搜索组件...")
    print(f"  仓库: {args.repository}")
    if args.group:
        print(f"  组: {args.group}")
    if args.name:
        print(f"  名称: {args.name}")
    if args.version:
        print(f"  版本: {args.version}")
    
    result = nexus.search_components(
        repository=args.repository,
        group=args.group,
        name=args.name,
        version=args.version
    )
    
    if not result:
        print("❌ 搜索失败")
        return False
    
    items = result.get('items', [])
    print(f"✅ 找到 {len(items)} 个匹配的组件:")
    
    for i, comp in enumerate(items[:args.limit], 1):
        group = comp.get('group', '')
        name = comp.get('name', '')
        version = comp.get('version', '')
        print(f"  {i:3d}. {group}.{name}:{version}")
        
        if args.verbose:
            print(f"       ID: {comp.get('id', '')}")
            for asset in comp.get('assets', []):
                print(f"       Asset: {asset.get('path', '')}")
    
    return True


def download_cmd(args):
    """下载命令"""
    nexus = NexusReq(default_account=args.account)
    
    if args.latest:
        print(f"正在下载最新版本...")
        print(f"  仓库: {args.repository}")
        print(f"  组: {args.group}")
        print(f"  名称: {args.name}")
        
        save_path = args.output or f"./{args.name}-latest.{args.extension}"
        
        result = nexus.download_latest_version(
            repository=args.repository,
            group=args.group,
            name=args.name,
            extension=args.extension,
            classifier=args.classifier,
            save_path=save_path
        )
    else:
        print(f"正在下载指定版本...")
        print(f"  仓库: {args.repository}")
        print(f"  组: {args.group}")
        print(f"  名称: {args.name}")
        print(f"  版本: {args.version}")
        
        save_path = args.output or f"./{args.name}-{args.version}.{args.extension}"
        
        result = nexus.search_and_download_asset(
            save_path=save_path,
            repository=args.repository,
            group=args.group,
            name=args.name,
            version=args.version,
            **{f'maven.extension': args.extension, 'maven.classifier': args.classifier or ''}
        )
    
    if result:
        print(f"✅ 下载成功: {result}")
    else:
        print("❌ 下载失败")
    
    return bool(result)


def upload_maven_cmd(args):
    """上传Maven组件命令"""
    # 启用邮件通知（如果提供了收件人）
    enable_email = bool(getattr(args, 'email_recipients', None))
    recipients = args.email_recipients.split(',') if enable_email else []
    
    nexus = NexusReq(
        default_account=args.account,
        enable_email_notification=enable_email,
        notification_recipients=recipients
    )
    
    print(f"正在上传Maven组件...")
    print(f"  仓库: {args.repository}")
    print(f"  组: {args.group_id}")
    print(f"  名称: {args.artifact_id}")
    print(f"  版本: {args.version}")
    
    # 检查文件是否存在
    if args.jar and not os.path.exists(args.jar):
        print(f"❌ JAR文件不存在: {args.jar}")
        return False
    
    if args.pom and not os.path.exists(args.pom):
        print(f"❌ POM文件不存在: {args.pom}")
        return False
    
    result = nexus.upload_maven_component(
        repository=args.repository,
        group_id=args.group_id,
        artifact_id=args.artifact_id,
        version=args.version,
        jar_file=args.jar,
        pom_file=args.pom,
        sources_file=args.sources,
        javadoc_file=args.javadoc,
        generate_pom=args.generate_pom,
        packaging=args.packaging
    )
    
    if result:
        print("✅ 上传成功")
        if enable_email:
            print(f"📧 邮件通知已发送给: {', '.join(recipients)}")
    else:
        print("❌ 上传失败")
    
    return bool(result)


def upload_raw_cmd(args):
    """上传Raw组件命令"""
    # 启用邮件通知（如果提供了收件人）
    enable_email = bool(getattr(args, 'email_recipients', None))
    recipients = args.email_recipients.split(',') if enable_email else []
    
    nexus = NexusReq(
        default_account=args.account,
        enable_email_notification=enable_email,
        notification_recipients=recipients
    )
    
    print(f"正在上传Raw组件...")
    print(f"  仓库: {args.repository}")
    print(f"  目录: {args.directory}")
    
    # 检查文件是否存在
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
    
    print(f"  文件数量: {len(args.files)}")
    for file_path in args.files:
        print(f"    - {os.path.basename(file_path)}")
    
    result = nexus.upload_raw_component(
        repository=args.repository,
        directory=args.directory,
        local_files=args.files
    )
    
    if result:
        print("✅ 上传成功")
        if enable_email:
            print(f"📧 邮件通知已发送给: {', '.join(recipients)}")
    else:
        print("❌ 上传失败")
    
    return bool(result)


def delete_component_cmd(args):
    """删除组件命令"""
    nexus = NexusReq(default_account=args.account)
    
    if not args.force:
        confirm = input(f"确定要删除组件 '{args.component_id}' 吗? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 操作已取消")
            return False
    
    print(f"正在删除组件: {args.component_id}")
    result = nexus.delete_component(args.component_id)
    
    if result:
        print("✅ 删除成功")
    else:
        print("❌ 删除失败")
    
    return bool(result)


def upload_sast_cmd(args):
    """上传SAST报告命令"""
    # 启用邮件通知（如果提供了收件人）
    enable_email = bool(args.email_recipients)
    recipients = args.email_recipients.split(',') if args.email_recipients else []
    
    nexus = NexusReq(
        default_account=args.account,
        enable_email_notification=enable_email,
        notification_recipients=recipients
    )
    
    print(f"正在上传SAST报告...")
    print(f"  项目: {args.project}")
    print(f"  SAST工具: {args.category}")
    print(f"  文件: {', '.join(args.files) if isinstance(args.files, list) else args.files}")
    
    # 构建附加信息
    additional_info = {}
    if args.scan_date:
        additional_info['扫描日期'] = args.scan_date
    if args.description:
        additional_info['描述'] = args.description
    
    result = nexus.upload_sast_report(
        project_name=args.project,
        sast_category=args.category,
        files=args.files,
        repository=args.repository,
        scan_date=args.scan_date,
        additional_info=additional_info if additional_info else None,
        create_zip=not args.no_zip
    )
    
    if result:
        print("✅ SAST报告上传成功")
        if enable_email:
            print(f"📧 邮件通知已发送给: {', '.join(recipients)}")
    else:
        print("❌ SAST报告上传失败")
    
    return bool(result)


def list_sast_cmd(args):
    """列出SAST报告命令"""
    nexus = NexusReq(default_account=args.account)
    
    print(f"正在列出SAST报告...")
    if args.project:
        print(f"  项目: {args.project}")
    if args.category:
        print(f"  工具类型: {args.category}")
    
    reports = nexus.list_sast_reports(
        project_name=args.project,
        sast_category=args.category,
        repository=args.repository
    )
    
    if not reports:
        print("❌ 未找到SAST报告")
        return False
    
    print(f"✅ 找到 {len(reports)} 个SAST报告:")
    
    for i, report in enumerate(reports[:args.limit], 1):
        name = report.get('name', '')
        assets = report.get('assets', [])
        
        print(f"  {i:3d}. {name}")
        
        if args.verbose:
            for asset in assets:
                path = asset.get('path', '')
                size = asset.get('size', 0)
                last_modified = asset.get('lastModified', '')
                print(f"       📄 {path} ({size} bytes, {last_modified})")
    
    return True


def download_sast_cmd(args):
    """下载SAST报告命令"""
    nexus = NexusReq(default_account=args.account)
    
    print(f"正在下载SAST报告...")
    print(f"  项目: {args.project}")
    print(f"  工具类型: {args.category}")
    print(f"  扫描日期: {args.scan_date}")
    
    result = nexus.download_sast_report(
        project_name=args.project,
        sast_category=args.category,
        scan_date=args.scan_date,
        filename=args.filename,
        repository=args.repository,
        download_dir=args.output
    )
    
    if result:
        if isinstance(result, list):
            print(f"✅ 成功下载 {len(result)} 个文件")
            if args.verbose:
                for file_path in result:
                    print(f"  📄 {file_path}")
        else:
            print("✅ 下载成功")
    else:
        print("❌ 下载失败")
    
    return bool(result)


def batch_upload_sast_cmd(args):
    """批量上传SAST报告命令"""
    if not os.path.exists(args.config):
        print(f"❌ 配置文件不存在: {args.config}")
        return False
    
    # 启用邮件通知（如果提供了收件人）
    enable_email = bool(args.email_recipients)
    recipients = args.email_recipients.split(',') if args.email_recipients else []
    
    nexus = NexusReq(
        default_account=args.account,
        enable_email_notification=enable_email,
        notification_recipients=recipients
    )
    
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            sast_configs = json.load(f)
        
        print(f"正在批量上传 {len(sast_configs)} 个SAST报告...")
        
        results = nexus.batch_upload_sast_reports(sast_configs)
        success_count = sum(1 for r in results if r)
        
        print(f"✅ 批量上传完成: {success_count}/{len(results)} 成功")
        
        if enable_email:
            print(f"📧 汇总邮件通知已发送给: {', '.join(recipients)}")
        
        return success_count == len(results)
        
    except Exception as e:
        print(f"❌ 批量上传失败: {e}")
        return False


def cleanup_versions_cmd(args):
    """清理版本命令"""
    nexus = NexusReq(default_account=args.account)
    
    print(f"正在清理旧版本...")
    print(f"  仓库: {args.repository}")
    print(f"  组: {args.group}")
    print(f"  名称: {args.name}")
    print(f"  保留版本数: {args.keep}")
    
    if not args.force:
        confirm = input("确定要清理旧版本吗? 此操作不可撤销! (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 操作已取消")
            return False
    
    result = nexus.cleanup_old_versions(
        repository=args.repository,
        group=args.group,
        name=args.name,
        keep_latest_count=args.keep
    )
    
    if result:
        print("✅ 清理完成")
    else:
        print("❌ 清理失败")
    
    return bool(result)


def main():
    parser = argparse.ArgumentParser(description="Nexus Repository 命令行工具")
    parser.add_argument('--account', '-a', default='admin', help='使用的账户名 (默认: admin)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出组件命令
    list_parser = subparsers.add_parser('list', help='列出组件')
    list_parser.add_argument('repository', help='仓库名称')
    list_parser.add_argument('--limit', '-l', type=int, default=50, help='显示数量限制 (默认: 50)')
    list_parser.add_argument('--output', '-o', help='保存详细信息到JSON文件')
    
    # 搜索组件命令
    search_parser = subparsers.add_parser('search', help='搜索组件')
    search_parser.add_argument('repository', help='仓库名称')
    search_parser.add_argument('--group', '-g', help='组ID')
    search_parser.add_argument('--name', '-n', help='组件名称')
    search_parser.add_argument('--version', help='版本')
    search_parser.add_argument('--limit', '-l', type=int, default=20, help='显示数量限制 (默认: 20)')
    
    # 下载命令
    download_parser = subparsers.add_parser('download', help='下载组件')
    download_parser.add_argument('repository', help='仓库名称')
    download_parser.add_argument('group', help='组ID')
    download_parser.add_argument('name', help='组件名称')
    download_parser.add_argument('--version', help='版本 (不指定则下载最新版)')
    download_parser.add_argument('--extension', default='jar', help='文件扩展名 (默认: jar)')
    download_parser.add_argument('--classifier', help='分类器 (如: sources, javadoc)')
    download_parser.add_argument('--output', '-o', help='保存文件路径')
    download_parser.add_argument('--latest', action='store_true', help='下载最新版本')
    
    # 上传Maven组件命令
    upload_maven_parser = subparsers.add_parser('upload-maven', help='上传Maven组件')
    upload_maven_parser.add_argument('repository', help='仓库名称')
    upload_maven_parser.add_argument('group_id', help='组ID')
    upload_maven_parser.add_argument('artifact_id', help='构件ID')
    upload_maven_parser.add_argument('version', help='版本')
    upload_maven_parser.add_argument('--jar', help='JAR文件路径')
    upload_maven_parser.add_argument('--pom', help='POM文件路径')
    upload_maven_parser.add_argument('--sources', help='源码JAR文件路径')
    upload_maven_parser.add_argument('--javadoc', help='Javadoc JAR文件路径')
    upload_maven_parser.add_argument('--packaging', default='jar', help='打包类型 (默认: jar)')
    upload_maven_parser.add_argument('--generate-pom', action='store_true', help='自动生成POM文件')
    
    # 上传Raw组件命令
    upload_raw_parser = subparsers.add_parser('upload-raw', help='上传Raw组件')
    upload_raw_parser.add_argument('repository', help='仓库名称')
    upload_raw_parser.add_argument('directory', help='目标目录路径')
    upload_raw_parser.add_argument('files', nargs='+', help='要上传的文件列表')
    
    # 删除组件命令
    delete_parser = subparsers.add_parser('delete', help='删除组件')
    delete_parser.add_argument('component_id', help='组件ID')
    delete_parser.add_argument('--force', action='store_true', help='强制删除，不询问确认')
    
    # 清理版本命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧版本')
    cleanup_parser.add_argument('repository', help='仓库名称')
    cleanup_parser.add_argument('group', help='组ID')
    cleanup_parser.add_argument('name', help='组件名称')
    cleanup_parser.add_argument('--keep', type=int, default=5, help='保留版本数 (默认: 5)')
    cleanup_parser.add_argument('--force', action='store_true', help='强制清理，不询问确认')
    
    # SAST报告上传命令
    upload_sast_parser = subparsers.add_parser('upload-sast', help='上传SAST工具报告')
    upload_sast_parser.add_argument('project', help='项目名称')
    upload_sast_parser.add_argument('category', 
                                   choices=['sonar', 'checkmarx', 'fortify', 'coverity', 'veracode', 'generic'],
                                   help='SAST工具类型')
    upload_sast_parser.add_argument('files', nargs='+', help='要上传的SAST报告文件列表')
    upload_sast_parser.add_argument('--repository', help='目标仓库 (默认: sast-reports-raw)')
    upload_sast_parser.add_argument('--scan-date', help='扫描日期 (YYYY-MM-DD格式，默认当前日期)')
    upload_sast_parser.add_argument('--description', help='附加描述信息')
    upload_sast_parser.add_argument('--no-zip', action='store_true', help='多文件时不创建zip压缩包')
    upload_sast_parser.add_argument('--email-recipients', help='邮件通知收件人列表 (逗号分隔)')
    
    # SAST报告列表命令
    list_sast_parser = subparsers.add_parser('list-sast', help='列出SAST工具报告')
    list_sast_parser.add_argument('--project', help='项目名称 (可选)')
    list_sast_parser.add_argument('--category', 
                                 choices=['sonar', 'checkmarx', 'fortify', 'coverity', 'veracode', 'generic'],
                                 help='SAST工具类型 (可选)')
    list_sast_parser.add_argument('--repository', help='仓库名称 (默认: sast-reports-raw)')
    list_sast_parser.add_argument('--limit', type=int, default=50, help='显示数量限制 (默认: 50)')
    
    # SAST报告下载命令
    download_sast_parser = subparsers.add_parser('download-sast', help='下载SAST工具报告')
    download_sast_parser.add_argument('project', help='项目名称')
    download_sast_parser.add_argument('category', 
                                     choices=['sonar', 'checkmarx', 'fortify', 'coverity', 'veracode', 'generic'],
                                     help='SAST工具类型')
    download_sast_parser.add_argument('scan_date', help='扫描日期 (YYYY-MM-DD格式)')
    download_sast_parser.add_argument('--filename', help='特定文件名 (可选，不指定则下载所有文件)')
    download_sast_parser.add_argument('--repository', help='源仓库 (默认: sast-reports-raw)')
    download_sast_parser.add_argument('--output', help='下载目录 (默认: ./sast_downloads)')
    
    # 批量上传SAST报告命令
    batch_sast_parser = subparsers.add_parser('batch-upload-sast', help='批量上传SAST工具报告')
    batch_sast_parser.add_argument('config', help='批量上传配置文件 (JSON格式)')
    batch_sast_parser.add_argument('--email-recipients', help='邮件通知收件人列表 (逗号分隔)')
    
    # 为所有现有命令添加邮件通知支持
    for cmd_parser in [upload_maven_parser, upload_raw_parser]:
        cmd_parser.add_argument('--email-recipients', help='邮件通知收件人列表 (逗号分隔)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # 执行对应的命令
        command_map = {
            'list': list_components_cmd,
            'search': search_components_cmd,
            'download': download_cmd,
            'upload-maven': upload_maven_cmd,
            'upload-raw': upload_raw_cmd,
            'delete': delete_component_cmd,
            'cleanup': cleanup_versions_cmd,
            'upload-sast': upload_sast_cmd,
            'list-sast': list_sast_cmd,
            'download-sast': download_sast_cmd,
            'batch-upload-sast': batch_upload_sast_cmd
        }
        
        if args.command in command_map:
            success = command_map[args.command](args)
            return 0 if success else 1
        else:
            print(f"❌ 未知命令: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ 操作被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

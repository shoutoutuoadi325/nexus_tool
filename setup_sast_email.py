#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nexus SAST和邮件通知功能快速设置脚本
帮助用户快速配置SMTP和SAST相关设置
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def setup_smtp_config():
    """配置SMTP邮件设置"""
    print("=== SMTP邮件配置 ===\n")
    
    smtp_server = input("SMTP服务器地址 (如: smtp.gmail.com): ").strip()
    smtp_port = input("SMTP端口 (默认: 587): ").strip() or "587"
    use_tls = input("使用TLS加密? (y/N): ").strip().lower() == 'y'
    
    email_address = input("发送邮箱地址: ").strip()
    email_password = input("邮箱密码/应用密码: ").strip()
    from_name = input("发送者名称 (默认: Nexus Notification System): ").strip() or "Nexus Notification System"
    
    smtp_config = {
        'smtp_server': smtp_server,
        'smtp_port': int(smtp_port),
        'use_tls': use_tls,
        'accounts': {
            'default': {
                'username': email_address,
                'password': email_password,
                'from_name': from_name
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
    
    print(f"\n✅ SMTP配置完成!")
    return smtp_config


def setup_sast_config():
    """配置SAST工具设置"""
    print("\n=== SAST工具配置 ===\n")
    
    print("支持的SAST工具:")
    print("1. SonarQube")
    print("2. Checkmarx")
    print("3. Fortify")
    print("4. Coverity")
    print("5. Veracode")
    print("6. Generic (通用)")
    
    default_repo = input("\n默认SAST报告仓库名称 (默认: sast-reports-raw): ").strip() or "sast-reports-raw"
    max_size_mb = input("最大文件大小(MB) (默认: 50): ").strip() or "50"
    
    sast_config = {
        'supported_formats': ['.pdf', '.doc', '.docx', '.txt', '.md', '.html', '.xml', '.json'],
        'max_file_size': int(max_size_mb) * 1024 * 1024,
        'repository_prefix': 'sast-reports',
        'default_repository': default_repo,
        'categories': {
            'sonar': 'SonarQube报告',
            'checkmarx': 'Checkmarx报告', 
            'fortify': 'Fortify报告',
            'coverity': 'Coverity报告',
            'veracode': 'Veracode报告',
            'generic': '通用SAST报告'
        }
    }
    
    print(f"\n✅ SAST配置完成!")
    return sast_config


def test_smtp_connection(smtp_config):
    """测试SMTP连接"""
    print("\n=== 测试SMTP连接 ===\n")
    
    try:
        from refs.email_notifier import EmailNotifier
        
        # 临时更新配置
        from refs.env_config import EnvConfig
        original_smtp = EnvConfig.SMTP_INFO
        EnvConfig.SMTP_INFO = smtp_config
        
        # 创建邮件通知器
        notifier = EmailNotifier()
        
        # 发送测试邮件
        test_recipient = input("输入测试邮件接收地址: ").strip()
        
        success = notifier.send_success_notification(
            recipients=[test_recipient],
            operation='SMTP配置测试',
            user='setup_script',
            details={
                'SMTP服务器': smtp_config['smtp_server'],
                '端口': smtp_config['smtp_port'],
                'TLS': '是' if smtp_config['use_tls'] else '否'
            },
            message='如果您收到这封邮件，说明SMTP配置成功！'
        )
        
        if success:
            print("✅ 测试邮件发送成功!")
        else:
            print("❌ 测试邮件发送失败，请检查配置")
        
        # 恢复原配置
        EnvConfig.SMTP_INFO = original_smtp
        
        return success
        
    except ImportError:
        print("❌ 邮件模块未安装，请先运行: pip install jinja2")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def update_env_config(smtp_config, sast_config):
    """更新环境配置文件"""
    print("\n=== 更新配置文件 ===\n")
    
    config_file = os.path.join('refs', 'env_config.py')
    
    try:
        # 读取现有配置
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 备份原文件
        backup_file = f"{config_file}.backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已备份原配置文件到: {backup_file}")
        
        # 更新SMTP配置
        smtp_str = f"""
    # SMTP邮件配置
    SMTP_INFO = {json.dumps(smtp_config, indent=8, ensure_ascii=False)}"""
        
        # 更新SAST配置
        sast_str = f"""
    # SAST工具配置
    SAST_INFO = {json.dumps(sast_config, indent=8, ensure_ascii=False)}"""
        
        # 检查是否已存在配置
        if 'SMTP_INFO' in content:
            # 替换现有配置
            import re
            content = re.sub(r'SMTP_INFO\s*=\s*{.*?}', smtp_str.strip(), content, flags=re.DOTALL)
        else:
            # 添加新配置
            content += smtp_str
        
        if 'SAST_INFO' in content:
            # 替换现有配置
            import re
            content = re.sub(r'SAST_INFO\s*=\s*{.*?}', sast_str.strip(), content, flags=re.DOTALL)
        else:
            # 添加新配置
            content += sast_str
        
        # 写入更新后的配置
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 配置文件已更新: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False


def create_example_files():
    """创建示例文件"""
    print("\n=== 创建示例文件 ===\n")
    
    # 创建示例目录
    examples_dir = Path('examples')
    examples_dir.mkdir(exist_ok=True)
    
    # 创建示例SAST配置文件
    batch_config = {
        "batch_sast_config_example": [
            {
                "project_name": "web-frontend",
                "sast_category": "sonar",
                "files": ["/path/to/sonar-report.pdf"],
                "scan_date": "2024-01-15",
                "additional_info": {
                    "扫描类型": "全量扫描",
                    "代码行数": "50000"
                }
            }
        ]
    }
    
    config_file = examples_dir / 'batch_sast_config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(batch_config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已创建示例配置文件: {config_file}")
    
    # 创建示例SAST文件
    for filename in ['sonar-report.pdf', 'checkmarx-report.pdf', 'fortify-report.pdf']:
        example_file = examples_dir / filename
        if not example_file.exists():
            with open(example_file, 'w') as f:
                f.write("# 这是一个示例SAST报告文件\n")
                f.write(f"文件名: {filename}\n")
                f.write("请用实际的SAST报告文件替换此文件\n")
    
    print(f"✅ 已创建示例SAST文件")


def main():
    """主函数"""
    print("Nexus SAST和邮件通知功能设置向导")
    print("=====================================\n")
    
    print("此脚本将帮助您配置:")
    print("1. SMTP邮件通知设置")
    print("2. SAST工具集成设置")
    print("3. 测试邮件功能")
    print("4. 创建示例文件\n")
    
    # 1. SMTP配置
    smtp_config = setup_smtp_config()
    
    # 2. SAST配置
    sast_config = setup_sast_config()
    
    # 3. 测试SMTP连接
    test_smtp = input("\n是否测试SMTP连接? (y/N): ").strip().lower() == 'y'
    if test_smtp:
        test_smtp_connection(smtp_config)
    
    # 4. 更新配置文件
    update_config = input("\n是否更新配置文件? (y/N): ").strip().lower() == 'y'
    if update_config:
        update_env_config(smtp_config, sast_config)
    
    # 5. 创建示例文件
    create_examples = input("\n是否创建示例文件? (y/N): ").strip().lower() == 'y'
    if create_examples:
        create_example_files()
    
    print("\n=== 设置完成 ===")
    print("\n接下来您可以:")
    print("1. 运行 python sast_demo.py 查看使用示例")
    print("2. 使用命令行工具上传SAST报告: python nexus_cli.py upload-sast --help")
    print("3. 在代码中使用邮件通知功能")
    
    print("\n感谢使用Nexus工具集!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 设置被用户中断")
    except Exception as e:
        print(f"\n❌ 设置过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

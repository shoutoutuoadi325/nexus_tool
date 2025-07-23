#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nexus配置助手
帮助用户快速配置Nexus服务器连接信息
"""

import os
import json
import getpass
import requests
from urllib.parse import urlparse


def test_nexus_connection(url, username, password):
    """测试Nexus连接"""
    try:
        # 测试基本API连接
        test_url = f"{url.rstrip('/')}/service/rest/v1/repositories"
        
        response = requests.get(
            test_url,
            auth=(username, password),
            timeout=10
        )
        
        if response.status_code == 200:
            repos = response.json()
            return True, f"连接成功! 找到 {len(repos)} 个仓库"
        elif response.status_code == 401:
            return False, "认证失败: 用户名或密码错误"
        elif response.status_code == 403:
            return False, "权限不足: 用户无权限访问API"
        else:
            return False, f"连接失败: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "连接超时: 请检查网络或服务器地址"
    except requests.exceptions.ConnectionError:
        return False, "连接错误: 无法连接到服务器"
    except Exception as e:
        return False, f"未知错误: {e}"


def get_nexus_info():
    """获取Nexus服务器信息"""
    print("=== Nexus Repository 配置助手 ===\n")
    
    # 获取服务器URL
    while True:
        url = input("请输入Nexus服务器URL (例: http://nexus.example.com:8081): ").strip()
        if not url:
            print("❌ URL不能为空!")
            continue
            
        # 验证URL格式
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print("❌ URL格式不正确! 请包含协议 (http:// 或 https://)")
                continue
            break
        except Exception:
            print("❌ URL格式不正确!")
            continue
    
    # 获取域名（从URL中提取）
    domain = urlparse(url).netloc
    
    accounts = {}
    
    print(f"\n服务器URL: {url}")
    print(f"服务器域名: {domain}")
    
    # 获取管理员账户
    print("\n=== 配置管理员账户 ===")
    while True:
        admin_user = input("管理员用户名 (默认: admin): ").strip() or "admin"
        admin_pass = getpass.getpass("管理员密码: ")
        
        if not admin_pass:
            print("❌ 密码不能为空!")
            continue
        
        print("正在测试连接...")
        success, message = test_nexus_connection(url, admin_user, admin_pass)
        
        if success:
            print(f"✅ {message}")
            accounts['admin'] = {
                'username': admin_user,
                'password': admin_pass
            }
            break
        else:
            print(f"❌ {message}")
            retry = input("是否重试? (y/N): ").strip().lower()
            if retry != 'y':
                return None
    
    # 询问是否添加其他账户
    while True:
        add_more = input("\n是否添加其他账户? (y/N): ").strip().lower()
        if add_more != 'y':
            break
        
        account_name = input("账户名称 (用于标识, 如: deploy-user): ").strip()
        if not account_name or account_name in accounts:
            print("❌ 账户名称不能为空或已存在!")
            continue
        
        username = input(f"{account_name} 用户名: ").strip()
        password = getpass.getpass(f"{account_name} 密码: ")
        
        if not username or not password:
            print("❌ 用户名和密码不能为空!")
            continue
        
        print("正在测试连接...")
        success, message = test_nexus_connection(url, username, password)
        
        if success:
            print(f"✅ {message}")
            accounts[account_name] = {
                'username': username,
                'password': password
            }
        else:
            print(f"❌ {message}")
            print("账户添加失败，但可以继续")
    
    return {
        'domain': domain,
        'root_url': url,
        'accounts': accounts
    }


def update_config_file(nexus_info):
    """更新配置文件"""
    config_file = os.path.join(os.path.dirname(__file__), 'refs', 'env_config.py')
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    try:
        # 读取现有配置
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 生成新的NEXUS_INFO配置
        nexus_config = f"""    NEXUS_INFO = {{
        'domain': '{nexus_info['domain']}',
        'root_url': '{nexus_info['root_url']}',
        'accounts': {{"""
        
        for account_name, account_info in nexus_info['accounts'].items():
            nexus_config += f"""
            '{account_name}': {{
                'username': '{account_info['username']}',
                'password': '{account_info['password']}'
            }},"""
        
        nexus_config += """
        }
    }"""
        
        # 查找并替换NEXUS_INFO部分
        if 'NEXUS_INFO = {' in content:
            # 找到现有配置的开始和结束位置
            start_pos = content.find('NEXUS_INFO = {')
            brace_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(content[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            # 替换配置
            new_content = content[:start_pos] + nexus_config + content[end_pos:]
        else:
            # 添加新配置
            # 在文件末尾添加
            if not content.endswith('\n'):
                content += '\n'
            new_content = content + '\n' + nexus_config + '\n'
        
        # 备份原文件
        backup_file = config_file + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 写入新配置
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 配置已更新: {config_file}")
        print(f"📁 原配置已备份: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False


def show_config_summary(nexus_info):
    """显示配置摘要"""
    print("\n=== 配置摘要 ===")
    print(f"服务器URL: {nexus_info['root_url']}")
    print(f"服务器域名: {nexus_info['domain']}")
    print(f"配置账户数: {len(nexus_info['accounts'])}")
    
    for account_name in nexus_info['accounts']:
        print(f"  - {account_name}")
    
    print("\n=== 使用示例 ===")
    print("# Python代码中使用:")
    print("from refs.nexus_req import NexusReq")
    print("nexus = NexusReq(default_account='admin')")
    print()
    print("# 命令行工具使用:")
    print("python nexus_cli.py --account admin list maven-releases")
    print()


def main():
    try:
        # 获取Nexus配置信息
        nexus_info = get_nexus_info()
        
        if not nexus_info:
            print("❌ 配置获取失败")
            return 1
        
        # 显示配置摘要
        show_config_summary(nexus_info)
        
        # 确认更新配置文件
        update_config = input("是否更新配置文件? (Y/n): ").strip().lower()
        if update_config != 'n':
            if update_config_file(nexus_info):
                print("\n🎉 Nexus配置完成! 现在可以使用工具类了。")
            else:
                print("\n❌ 配置文件更新失败，请手动配置。")
                print("\n手动配置信息:")
                print(json.dumps(nexus_info, indent=2, ensure_ascii=False))
        else:
            print("\n配置信息 (请手动添加到 env_config.py):")
            print(json.dumps(nexus_info, indent=2, ensure_ascii=False))
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ 配置被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 配置过程中发生错误: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

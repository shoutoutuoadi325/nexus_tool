# -*- coding: utf-8 -*-

"""
Nexus工具类使用示例
按照gerrit_req的模式实现的Nexus Repository管理工具

主要功能：
1. 组件管理：上传、下载、删除、查询
2. 资产管理：列出、下载、删除资产
3. 搜索功能：搜索组件和资产
4. 批量操作：批量下载、批量删除
5. 仓库间转移：组件迁移
6. 版本管理：清理旧版本

支持的仓库格式：
- Maven2
- Raw
- NPM
- NuGet
- PyPI
- Docker等
"""

import json
import os
from refs.nexus_req import NexusReq

def demo_component_operations():
    """演示组件操作"""
    print("=== 组件操作示例 ===")
    
    nexus = NexusReq(default_account='admin')
    
    # 1. 列出仓库中的组件
    print("1. 列出maven-releases仓库中的组件:")
    components = nexus.list_components('maven-releases')
    if components:
        print(f"找到 {len(components.get('items', []))} 个组件")
        for comp in components.get('items', [])[:3]:  # 只显示前3个
            print(f"  - {comp.get('group', '')}.{comp.get('name', '')}:{comp.get('version', '')}")
    
    # 2. 搜索组件
    print("\n2. 搜索Spring相关组件:")
    search_result = nexus.search_components(
        repository='maven-central', 
        group='org.springframework'
    )
    if search_result and search_result.get('items'):
        print(f"找到 {len(search_result['items'])} 个Spring组件")
        for comp in search_result['items'][:3]:
            print(f"  - {comp.get('name', '')}:{comp.get('version', '')}")
    
    # 3. 获取特定组件详情
    if components and components.get('items'):
        component_id = components['items'][0]['id']
        print(f"\n3. 获取组件详情 (ID: {component_id}):")
        detail = nexus.get_component(component_id)
        if detail:
            print(f"  组件名: {detail.get('name', '')}")
            print(f"  版本: {detail.get('version', '')}")
            print(f"  资产数量: {len(detail.get('assets', []))}")

def demo_upload_operations():
    """演示上传操作"""
    print("\n=== 上传操作示例 ===")
    
    nexus = NexusReq()
    
    # Maven组件上传示例（需要实际文件）
    print("1. Maven组件上传示例:")
    print("  nexus.upload_maven_component(")
    print("    repository='maven-releases',")
    print("    group_id='com.example',")
    print("    artifact_id='my-library',")
    print("    version='1.0.0',")
    print("    jar_file='path/to/my-library-1.0.0.jar',")
    print("    pom_file='path/to/pom.xml',")
    print("    sources_file='path/to/my-library-1.0.0-sources.jar'")
    print("  )")
    
    # Raw组件上传示例
    print("\n2. Raw组件上传示例:")
    print("  nexus.upload_raw_component(")
    print("    repository='raw-hosted',")
    print("    directory='/releases/v1.0',")
    print("    local_files=['file1.txt', 'file2.zip']")
    print("  )")
    
    # NPM包上传示例
    print("\n3. NPM包上传示例:")
    print("  nexus.upload_npm_component(")
    print("    repository='npm-hosted',")
    print("    npm_package_file='my-package-1.0.0.tgz'")
    print("  )")

def demo_download_operations():
    """演示下载操作"""
    print("\n=== 下载操作示例 ===")
    
    nexus = NexusReq()
    
    # 1. 搜索并下载资产
    print("1. 搜索并下载Spring Core最新版本:")
    result = nexus.download_latest_version(
        repository='maven-central',
        group='org.springframework',
        name='spring-core',
        save_path='./downloads/spring-core-latest.jar'
    )
    if result:
        print(f"  下载成功: {result}")
    else:
        print("  下载失败或资产不存在")
    
    # 2. 通过搜索下载特定版本
    print("\n2. 下载特定版本的资产:")
    result = nexus.search_and_download_asset(
        save_path='./downloads/spring-core-5.3.21.jar',
        repository='maven-central',
        group='org.springframework',
        name='spring-core',
        version='5.3.21',
        **{'maven.extension': 'jar', 'maven.classifier': ''}
    )
    if result:
        print(f"  下载成功: {result}")
    else:
        print("  下载失败")

def demo_batch_operations():
    """演示批量操作"""
    print("\n=== 批量操作示例 ===")
    
    nexus = NexusReq()
    
    # 批量下载示例
    print("1. 批量下载资产:")
    asset_list = [
        {'asset_id': 'asset-id-1', 'filename': 'file1.jar'},
        {'asset_id': 'asset-id-2', 'filename': 'file2.jar'},
        'asset-id-3'  # 可以只提供ID，文件名自动推断
    ]
    
    print("  nexus.batch_download_assets(")
    print("    asset_list=[")
    for asset in asset_list:
        print(f"      {asset},")
    print("    ],")
    print("    download_dir='./batch_downloads',")
    print("    max_workers=5")
    print("  )")
    
    # 批量删除示例
    print("\n2. 批量删除组件:")
    component_ids = ['comp-id-1', 'comp-id-2', 'comp-id-3']
    print("  nexus.batch_delete_components([")
    for comp_id in component_ids:
        print(f"    '{comp_id}',")
    print("  ])")

def demo_repository_management():
    """演示仓库管理操作"""
    print("\n=== 仓库管理示例 ===")
    
    nexus = NexusReq()
    
    # 1. 获取仓库中所有组件
    print("1. 获取仓库中所有组件:")
    print("  all_components = nexus.get_all_components_in_repository('maven-releases')")
    print("  print(f'总共有 {len(all_components)} 个组件')")
    
    # 2. 组件迁移
    print("\n2. 组件在仓库间迁移:")
    print("  nexus.move_component_between_repositories(")
    print("    source_repo='maven-snapshots',")
    print("    target_repo='maven-releases',")
    print("    component_id='component-id-to-move'")
    print("  )")
    
    # 3. 版本清理
    print("\n3. 清理旧版本:")
    print("  nexus.cleanup_old_versions(")
    print("    repository='maven-releases',")
    print("    group='com.example',")
    print("    name='my-library',")
    print("    keep_latest_count=5  # 只保留最新的5个版本")
    print("  )")

def demo_search_operations():
    """演示搜索操作"""
    print("\n=== 搜索操作示例 ===")
    
    nexus = NexusReq()
    
    # 1. 基本搜索
    print("1. 基本组件搜索:")
    result = nexus.search_components(
        repository='maven-central',
        group='org.apache',
        name='commons-lang3'
    )
    if result and result.get('items'):
        print(f"  找到 {len(result['items'])} 个匹配的组件")
    
    # 2. 高级搜索（使用额外参数）
    print("\n2. Maven特定搜索:")
    result = nexus.search_assets(
        repository='maven-central',
        group='org.springframework',
        name='spring-core',
        version='5.3.21',
        **{
            'maven.extension': 'jar',
            'maven.classifier': 'sources'  # 搜索源码包
        }
    )
    if result and result.get('items'):
        print(f"  找到 {len(result['items'])} 个源码包")
    
    # 3. 分页搜索
    print("\n3. 分页搜索示例:")
    print("  continuation_token = None")
    print("  all_results = []")
    print("  while True:")
    print("    result = nexus.search_components(")
    print("      repository='maven-central',")
    print("      group='org.springframework',")
    print("      continuation_token=continuation_token")
    print("    )")
    print("    if not result or not result.get('items'):")
    print("      break")
    print("    all_results.extend(result['items'])")
    print("    continuation_token = result.get('continuationToken')")
    print("    if not continuation_token:")
    print("      break")

def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理示例 ===")
    
    nexus = NexusReq()
    
    print("1. 处理不存在的组件:")
    result = nexus.get_component('non-existent-component-id')
    if result:
        print("  组件存在")
    else:
        print("  组件不存在或发生错误")
    
    print("\n2. 处理网络错误:")
    print("  try:")
    print("    result = nexus.list_components('some-repository')")
    print("    if result:")
    print("      # 处理成功结果")
    print("      pass")
    print("    else:")
    print("      # 处理失败情况")
    print("      print('操作失败')")
    print("  except Exception as e:")
    print("    print(f'发生异常: {e}')")

if __name__ == '__main__':
    print("Nexus Repository 工具类使用示例")
    print("=" * 50)
    
    # 注意：以下示例需要配置正确的Nexus服务器信息才能运行
    print("注意：运行这些示例需要：")
    print("1. 在 env_config.py 中配置正确的Nexus服务器信息")
    print("2. 确保Nexus服务器可访问且认证信息正确")
    print("3. 目标仓库已存在")
    print()
    
    try:
        demo_component_operations()
        demo_upload_operations()
        demo_download_operations()
        demo_batch_operations()
        demo_repository_management()
        demo_search_operations()
        demo_error_handling()
        
        print("\n" + "=" * 50)
        print("示例演示完成！")
        print("请根据实际需求调用相应的方法。")
        
    except Exception as e:
        print(f"示例运行出错: {e}")
        print("请检查Nexus服务器配置和网络连接。")

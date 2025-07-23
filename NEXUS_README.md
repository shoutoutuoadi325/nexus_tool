# Nexus Repository 工具类

按照gerrit_req模式实现的Nexus Repository管理工具，提供了完整的Nexus仓库操作功能。

## 功能特性

### 🎯 核心功能
- **组件管理**：上传、下载、删除、查询组件
- **资产管理**：列出、下载、删除资产
- **搜索功能**：强大的组件和资产搜索
- **批量操作**：批量下载和删除
- **仓库管理**：组件迁移、版本清理
- **多格式支持**：Maven2、Raw、NPM、NuGet、PyPI等

### 🚀 高级特性
- **并发下载**：支持多线程批量下载
- **智能重试**：网络错误自动重试机制
- **版本管理**：自动清理旧版本
- **错误处理**：完善的异常处理和日志记录

## 安装依赖

```bash
pip install requests loguru
```

## 配置说明

在 `refs/env_config.py` 中配置Nexus服务器信息：

```python
NEXUS_INFO = {
    'domain': 'your-nexus-domain.com',
    'root_url': 'http://your-nexus-domain.com:8081',
    'accounts': {
        'admin': {
            'username': 'admin',
            'password': 'your-password'
        },
        'deploy-user': {
            'username': 'deploy',
            'password': 'deploy-password'
        }
    }
}
```

## 快速开始

```python
from refs.nexus_req import NexusReq

# 创建Nexus客户端
nexus = NexusReq(default_account='admin')

# 列出仓库组件
components = nexus.list_components('maven-releases')

# 搜索组件
result = nexus.search_components(
    repository='maven-central', 
    group='org.springframework'
)

# 下载最新版本
nexus.download_latest_version(
    repository='maven-central',
    group='org.springframework',
    name='spring-core',
    save_path='./spring-core-latest.jar'
)
```

## 详细API文档

### 组件操作

#### 列出组件
```python
# 列出仓库中的所有组件
components = nexus.list_components('maven-releases')

# 分页查询
components = nexus.list_components('maven-releases', continuation_token='token')
```

#### 获取组件详情
```python
component = nexus.get_component('component-id')
```

#### 删除组件
```python
result = nexus.delete_component('component-id')
```

### 上传操作

#### Maven组件上传
```python
nexus.upload_maven_component(
    repository='maven-releases',
    group_id='com.example',
    artifact_id='my-library',
    version='1.0.0',
    jar_file='path/to/library.jar',
    pom_file='path/to/pom.xml',
    sources_file='path/to/sources.jar',  # 可选
    javadoc_file='path/to/javadoc.jar',  # 可选
    generate_pom=False,  # 是否自动生成POM
    packaging='jar'
)
```

#### Raw格式上传
```python
nexus.upload_raw_component(
    repository='raw-hosted',
    directory='/releases/v1.0',
    local_files=['file1.txt', 'file2.zip', 'file3.tar.gz']
)
```

#### NPM包上传
```python
nexus.upload_npm_component(
    repository='npm-hosted',
    npm_package_file='my-package-1.0.0.tgz'
)
```

### 下载操作

#### 下载资产
```python
# 通过资产ID下载
nexus.download_asset('asset-id', save_path='./downloaded-file.jar')

# 搜索并下载
nexus.search_and_download_asset(
    save_path='./spring-core.jar',
    repository='maven-central',
    group='org.springframework',
    name='spring-core',
    version='5.3.21',
    **{'maven.extension': 'jar', 'maven.classifier': ''}
)

# 下载最新版本
nexus.download_latest_version(
    repository='maven-central',
    group='org.springframework',
    name='spring-core',
    extension='jar',
    classifier='sources',  # 可选，下载源码包
    save_path='./spring-core-sources.jar'
)
```

### 搜索功能

#### 搜索组件
```python
# 基本搜索
result = nexus.search_components(
    repository='maven-central',
    group='org.springframework',
    name='spring-core'
)

# 高级搜索
result = nexus.search_components(
    repository='maven-central',
    group='org.apache',
    **{'maven.extension': 'jar'}
)
```

#### 搜索资产
```python
assets = nexus.search_assets(
    repository='maven-central',
    group='org.springframework',
    name='spring-core',
    version='5.3.21'
)
```

### 批量操作

#### 批量下载
```python
asset_list = [
    {'asset_id': 'asset-id-1', 'filename': 'custom-name1.jar'},
    {'asset_id': 'asset-id-2', 'filename': 'custom-name2.jar'},
    'asset-id-3'  # 使用默认文件名
]

results = nexus.batch_download_assets(
    asset_list=asset_list,
    download_dir='./downloads',
    max_workers=5  # 并发数
)
```

#### 批量删除
```python
component_ids = ['comp-id-1', 'comp-id-2', 'comp-id-3']
results = nexus.batch_delete_components(component_ids, max_workers=3)
```

### 仓库管理

#### 组件迁移
```python
# 将组件从一个仓库移动到另一个仓库
nexus.move_component_between_repositories(
    source_repo='maven-snapshots',
    target_repo='maven-releases',
    component_id='component-to-move'
)
```

#### 版本清理
```python
# 清理旧版本，只保留最新的5个版本
nexus.cleanup_old_versions(
    repository='maven-releases',
    group='com.example',
    name='my-library',
    keep_latest_count=5
)
```

#### 获取所有组件
```python
all_components = nexus.get_all_components_in_repository('maven-releases')
```

## 支持的仓库格式

### Maven2
- ✅ 组件上传（支持jar、pom、sources、javadoc）
- ✅ 自动POM生成
- ✅ 分类器支持（sources、javadoc等）
- ✅ 版本管理

### Raw
- ✅ 多文件上传
- ✅ 自定义目录结构
- ✅ 任意文件格式

### NPM
- ✅ 标准NPM包上传
- ✅ package.json解析

### 其他格式
- NuGet、PyPI、Docker等格式的基础支持
- 可根据需要扩展特定格式的上传逻辑

## 错误处理

工具类提供了完善的错误处理机制：

```python
try:
    result = nexus.upload_maven_component(...)
    if result:
        print("上传成功")
    else:
        print("上传失败")
except Exception as e:
    print(f"发生异常: {e}")
```

常见错误类型：
- **认证错误**：用户名密码不正确
- **权限错误**：用户无足够权限执行操作
- **网络错误**：Nexus服务器不可达
- **仓库错误**：目标仓库不存在
- **文件错误**：上传文件不存在或格式不正确

## 性能优化

### 并发控制
- 批量操作支持并发控制
- 默认并发数为5，可根据服务器性能调整
- 避免过高并发导致服务器压力

### 内存管理
- 大文件上传使用流式处理
- 自动关闭文件句柄
- 临时文件自动清理

### 网络优化
- 支持连接超时设置
- 大文件下载使用分块传输
- 自动重试机制

## 示例项目

查看 `nexus_demo.py` 获取完整的使用示例：

```bash
python nexus_demo.py
```

## 注意事项

1. **权限要求**：确保使用的账户有足够权限访问目标仓库
2. **仓库存在**：操作前确保目标仓库已创建
3. **网络连接**：确保能够访问Nexus服务器
4. **文件路径**：上传时使用绝对路径避免路径问题
5. **版本格式**：Maven版本号应符合语义化版本规范

## 扩展开发

### 添加新的仓库格式支持

1. 在 `upload_xxx_component` 方法中添加新格式
2. 实现格式特定的参数处理
3. 添加相应的测试用例

### 自定义认证方式

```python
class CustomNexusReq(NexusReq):
    def _exec(self, api_name, **kwargs):
        # 实现自定义认证逻辑
        # 调用父类方法
        return super()._exec(api_name, **kwargs)
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

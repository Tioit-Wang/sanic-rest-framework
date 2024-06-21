在Sanic Web框架中缺少一款类似于 Django + DRF 一样便捷的高度统一的框架，SRF 由此应运而生。

[English](https://github.com/Tioit-Wang/sanic-rest-framework/blob/main/README.md)

如果你在为以下事情烦恼，那么应该立即使用 SRF:
- 为每个简单的CRUD接口编写重复的代码
- 重复校验每个接口输入和输出的值是否符合特定规则
- 熟悉Django生态却困惑于Sanic各种插件
- 仍在手动实现各种登录鉴权、权限控制、API限流、API缓存的代码
- ORM插件支持不佳，令人沮丧

## 特性
- **支持OpenAPI v3.0**: 提供独立的 SwaggerUi，支持定制API文档，少量的代码带来优美的体验。
- **ClassView优先的接口设计**: 支持95%的CRUD需求，通过配置实现登录鉴权、权限控制、API限流、API缓存。
- **快速开发工具**: 提供project-helper，用于支持快速开发，组织项目结构。
- **高可用的序列化工具**: 类似于DRF的serializers和fields。
- **全面支持Tortoise ORM**: 与Tortoise ORM深度集成。
- **完整的文档**: 项目文档提供中英文版本 [Chinese](https://tioit.cc/docs/SanicSRF/start) [English](https://tioit.cc/docs/SanicSRF/en/start)

## 需求
- **Sanic**: 21.6 最新版
- **Tortoise ORM**: 最新版
- **orjson**: 最新版

我们强烈推荐并且只官方支持Sanic和Tortoise ORM系列的最新补丁版本。

## 安装

使用`pip`安装：

```bash
pip install sanic-rest-framework # Old

# latest version
git clone https://github.com/Tioit-Wang/sanic-rest-framework.git
cd sanic-rest-framework
pip install -e .
```

在你的Sanic应用初始化时添加`SRFRequest`：

```python
from sanic import Sanic
from rest_framework.request import SRFRequest

app = Sanic(name='your app name', request_class=SRFRequest)
```

## 简单示例

你可以查看[Github上的示例](https://github.com/Tioit-Wang/srf_simple_example)或在[Web VSCode中打开示例](https://vscode.dev/github/Tioit-Wang/srf_simple_example)。

```python
from sanic import Sanic
from sanic.response import json
from rest_framework.views import APIView
from rest_framework.request import SRFRequest

app = Sanic("SampleApp", request_class=SRFRequest)

class HelloWorldView(APIView):
    def get(self, request):
        return json({'hello': 'world'})

app.add_route(HelloWorldView.as_view(), '/')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## 项目计划

- ✅ 支持 tortoise-orm
- ✅ 任意数据源序列化器
- ✅ 模型序列化器
- ✅ 序列化器基础字段
- ✅ 复杂的序列化器字段
- ✅ 字段验证器
- ✅ 权限验证
- ✅ 身份认证
- ✅ API视图
- ✅ 通用视图
- ✅ 模型视图
- ✅ 节流
- ✅ 分页
- ✅ 单元测试
- ❌ 低代码入侵
- ❌ 支持GINO-orm
- ❌ 缓存视图

## 项目模板

......

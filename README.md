# Sanic Rest Framework (SRF) 

[Chinese](https://github.com/Tioit-Wang/sanic-rest-framework/blob/main/README_CN.md)

SRF is born to provide a highly unified framework for Sanic Web framework, similar to Django + DRF.

If you are troubled by the following issues, you should start using SRF immediately:
- Writing repetitive code for each simple CRUD interface.
- Repeatedly validating the input and output values of each interface to comply with specific rules.
- Familiar with the Django ecosystem but puzzled by various Sanic plugins.
- Still manually implementing various login authentication, permission control, API rate limiting, and API caching.
- Frustrated by poor ORM plugin support.

## Features
- **Supports OpenAPI v3.0**: Offers a standalone SwaggerUi, supports customized API documentation, providing a pleasant experience with minimal code.
- **ClassView-first interface design**: Supports 95% of CRUD needs, achieving login authentication, permission control, API rate limiting, and API caching through configuration.
- **Rapid development tools**: Provides project-helper for rapid development and organizing project structure.
- **Highly available serialization tools**: Similar to DRF's serializers and fields.
- **Comprehensive support for Tortoise ORM**: Deeply integrated with Tortoise ORM.
- **Complete documentation**: Project documentation is available in both Chinese and English [Chinese](https://tioit.cc/docs/SanicSRF/start) [English](https://tioit.cc/docs/SanicSRF/en/start)

## Requirements
- **Sanic**: Latest version 21.6
- **Tortoise ORM**: Latest version
- **orjson**: Latest version

We strongly recommend and officially support only the latest patch versions of the Sanic and Tortoise ORM series.

## Installation

Install using `pip`:

```bash
pip install sanic-rest-framework # Old

# latest version
git clone https://github.com/Tioit-Wang/sanic-rest-framework.git
cd sanic-rest-framework
pip install -e .
```

Add `SRFRequest` when initializing your Sanic application:

```python
from sanic import Sanic
from rest_framework.request import SRFRequest

app = Sanic(name='your app name', request_class=SRFRequest)
```

## Simple Example

You can check out the [example on Github](https://github.com/Tioit-Wang/srf_simple_example) or open the example in [Web VSCode](https://vscode.dev/github/Tioit-Wang/srf_simple_example).

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

## Project Plan

- ✅ Support for tortoise-orm
- ✅ Serializer for any data source
- ✅ Model serializer
- ✅ Basic fields for serializers
- ✅ Complex serializer fields
- ✅ Field validators
- ✅ Permission validation
- ✅ Authentication
- ✅ API views
- ✅ Generic views
- ✅ Model views
- ✅ Throttling
- ✅ Pagination
- ✅ Unit tests
- ❌ Low code intrusion
- ❌ Support for GINO-orm
- ❌ Cache views

## Project Template

......
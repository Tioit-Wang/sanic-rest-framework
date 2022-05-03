# [Sanic REST Framework](https://github.com/encode/django-rest-framework)

Supports OpenAPI v3.0 Web APIs

Full documentation for the project is available at [Chinese](https://www.tioit.cc/index.php/category/srf/) [English](https://www.tioit.cc/index.php/category/srf_en/)

---

## Overview

Sanic REST framework is a powerful and flexible toolkit for building Web APIs.

Some reasons you might want to use REST framework:

- Serialization that supports both ORM and non-ORM data sources.
- Customizable all the way down - just use regular function-based views if you don't need the more powerful features.
- Simple and efficient serializer and validator
- OpenAPI v3.0 swagger supports

<br/>

## Requirements

- Sanic 21.6+
- Tortoise ORM 0.17.3+
- ujson latest

We highly recommend and only officially support the latest patch release of each Sanic and Tortoise ORM series.

<br/>

## Installation

Install using `pip` ...

```
pip install sanic-rest-framework
```

Add `SRFRequest` to you sanic app initialization

```python
from sanic from Sanic
from srf.request import SRFRequest

app = Sanic(name='your app name', request_class=SRFRequest)
```

## Simple example

> model.py

```python
from tortoise import Model, fields

class UserModel(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)

    def __str__(self):
        return f"User {self.id}: {self.name}"
```

> serializers.py

```python
class UserSerializer(ModelSerializer):
    class Meta:
        model = UserModel
        read_only_fields = ('id')
```

> app.py

```python
import logging

from sanic import Sanic, response

from srf.request import SRFRequest
from srf.routes import ViewSetRouter
from srf.serializers import ModelSerializer
from srf.views import ModelViewSet

from tortoise import Model, fields
from tortoise.contrib.sanic import register_tortoise

from serializers import UserSerializer
from models import UserModel

logging.basicConfig(level=logging.DEBUG)
app = Sanic(__name__, request_class=SRFRequest)

class TestView(ModelViewSet):
    serializer_class = UserSerializer
    queryset = UserModel
    search_fields = ('@question',)


route = ViewSetRouter()
route.register(TestView, '/TestView', 'test', True)
for i in route.urls:
    i.pop('is_base')
    app.add_route(**i)

register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ['models']}, generate_schemas=True
)

if __name__ == "__main__":
    app.run(port=5000)
```

Accessing `http://127.0.0.1:5000/TestView` yields the following response

```json5
{
    "data": {
        "count": 0,
        "next": null,
        "next_page_num": null,
        "previous": null,
        "previous_num": 0,
        "results": []
    },
    "message": "Success",
    "status": 1
}
```

## Project plan

- [x] Arbitrary data source serializer
- [x] Model serializer
- [x] Serializer base field
- [x] Complex serializer fields
- [x] Field validator
- [x] Permission to verify
- [x] Identity authentication
- [x] API view
- [x] Generics view
- [x] Model view
- [ ] Cache view 
- [ ] Throttling
- [x] Paginations
- [ ] Low code intrusion
- [x] Support tortoise-orm
- [ ] Support GINO-orm

## Complete example

......

## Project Template

......
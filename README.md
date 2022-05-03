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

[Example in github](https://github.com/Tioit-Wang/srf_simple_example)

[Open example in web vscode](https://vscode.dev/github/Tioit-Wang/srf_simple_example)


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


## Project Template

......
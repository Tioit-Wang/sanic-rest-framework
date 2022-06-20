class Parameter:
    def __init__(self, field_name: str, field_type='string', used_for='query', title=None, required=False):
        """
        @param field_name:
        @param field_type:
        @param used_for:
        @param title:
        @param required:
        """
        self.field_name = field_name
        self.title = title or self.field_name
        self.field_type = field_type
        self.used_for = used_for
        self.required = required
        self.field_type = field_type

    def to_dict(self):
        return {
            "required": self.required,
            "schema": {
                "title": self.title,
                "type": self.field_type
            },
            "name": self.field_name,
            "in": self.used_for
        }


class Parameters:
    def __init__(self):
        self._parameters = []

    def add(self, item: Parameter):
        self._parameters.append(item.to_dict())

    @property
    def parameters(self):
        return self._parameters


class ApiKeySecurity:
    def __init__(self, name='Token', used_for='header'):
        self.name = name
        self.used_for = used_for

    def to_dict(self):
        return {
            'type': 'apiKey',
            'in': self.used_for,
            'name': self.name
        }


class PropItem:
    def __init__(self, title, field_type, field_format=None):
        self.title = title
        self.field_type = field_type
        self.field_format = field_format

    def to_dict(self):
        field_dict = {
            "title": self.title,
            "type": self.field_type
        }
        if self.field_format:
            field_dict['format'] = self.field_format
        return field_dict


class ObjectItem:
    def __init__(self, title):
        self.title = title
        self.field_type = 'object'
        self.properties = {}
        self.required = []

    def add(self, field_name, field, required=False):
        self.properties[field_name] = field
        if required:
            self.required.append(field_name)

    def to_dict(self):
        res = {
            "title": self.title,
            "type": self.field_type,
            "properties": self.properties,
        }
        if self.required:
            res['required'] = self.required
        return res


class ArrayItem:

    def __init__(self, title, items):
        self.title = title
        self.field_type = 'array'
        self.items = items

    def to_dict(self):
        return {
            "title": self.title,
            "type": self.field_type,
            "items": self.items,
        }

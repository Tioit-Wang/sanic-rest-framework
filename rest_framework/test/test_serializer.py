from enum import Enum
import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import (
    CharField,
    IntegerField,
    FloatField,
    DecimalField,
    DateTimeField,
    DateField,
    TimeField,
    ChoiceField,
    EnumChoiceField,
)
from rest_framework.serializers import Serializer


class InheritanceSerializerTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        class BaseSerializer(Serializer):
            test_char = CharField(description='test_char')

        class ChildSerializer(BaseSerializer):
            test_child_char = CharField(description='test_child_char')

        self.sample_serializer = ChildSerializer()

    async def test_fields(self):
        field_names = [
            'test_char',
            'test_child_char',
        ]
        self.assertEqual(field_names, [field.field_name for field in self.sample_serializer.fields.values()])


class SerializerToOpenapiTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        class OpenapiEnum(Enum):
            Choice1 = 1
            Choice2 = 2
            Choice3 = 3

        class ChildSerializer(Serializer):
            test_char = CharField(description='test_char', max_length=18, min_length=1)

        class OpenapiSerializer(Serializer):
            test_char = CharField(description='test_char', max_length=18, min_length=1)
            test_int = IntegerField(description='test_int', max_value=10, min_value=1, allow_null=True, required=False)
            test_float = FloatField(description='test_float', max_value=10.0, min_value=1.0)
            test_only_read = CharField(description='test_only_read', read_only=True)
            test_only_write = CharField(description='test_only_write', write_only=True)
            test_date = DateField(description='test_date')
            test_datetime = DateTimeField(description='test_datetime')
            test_time = TimeField(description='test_time')
            test_decimal = DecimalField(description='test_decimal', max_value=10, min_value=1, decimal_places=2, max_digits=5)
            test_choice = ChoiceField(description='test_enum', choices=((1, 'Choice 1'), (2, 'Choice 2'), (3, 'Choice 3')))
            test_enum = EnumChoiceField(description='test_enum', enum_type=OpenapiEnum, value_type=str)

            child = ChildSerializer()
            children = ChildSerializer(many=True)

        self.serializer = OpenapiSerializer()

    async def test_to_openapi(self):
        expected = {
            'properties': {
                'child': {
                    'properties': {
                        'test_char': {
                            'description': 'test_char',
                            'maxLength': 18,
                            'minLength': 1,
                            'nullable': False,
                            'required': True,
                            'type': 'string',
                        }
                    },
                    'required': ['test_char'],
                    'type': 'object',
                },
                'children': {
                    'items': {
                        'properties': {
                            'test_char': {
                                'description': 'test_char',
                                'maxLength': 18,
                                'minLength': 1,
                                'nullable': False,
                                'required': True,
                                'type': 'string',
                            }
                        },
                        'required': ['test_char'],
                        'type': 'object',
                    },
                    'type': 'array',
                },
                'test_char': {
                    'description': 'test_char',
                    'maxLength': 18,
                    'minLength': 1,
                    'nullable': False,
                    'required': True,
                    'type': 'string',
                },
                'test_choice': {'description': 'test_enum', 'enum': [1, 2, 3], 'nullable': False, 'required': True, 'type': 'string'},
                'test_date': {'description': 'test_date', 'format': 'date', 'nullable': False, 'required': True, 'type': 'string'},
                'test_datetime': {
                    'description': 'test_datetime',
                    'format': 'date-time',
                    'nullable': False,
                    'required': True,
                    'type': 'string',
                },
                'test_decimal': {
                    'description': 'test_decimal',
                    'format': 'float',
                    'maxLength': 1000,
                    'maximum': 10,
                    'minimum': 1,
                    'nullable': False,
                    'required': True,
                    'type': 'number',
                },
                'test_enum': {'description': 'test_enum', 'enum': [1, 2, 3], 'nullable': False, 'required': True, 'type': 'string'},
                'test_float': {
                    'description': 'test_float',
                    'format': 'float',
                    'maximum': 10.0,
                    'minimum': 1.0,
                    'nullable': False,
                    'required': True,
                    'type': 'number',
                },
                'test_int': {
                    'description': 'test_int',
                    'format': 'int32',
                    'maximum': 10,
                    'minimum': 1,
                    'nullable': True,
                    'required': False,
                    'type': 'integer',
                },
                'test_only_read': {'description': 'test_only_read', 'nullable': False, 'type': 'string'},
                'test_only_write': {'description': 'test_only_write', 'nullable': False, 'required': True, 'type': 'string'},
                'test_time': {'description': 'test_time', 'format': 'time', 'nullable': False, 'required': True, 'type': 'string'},
            },
            'required': [
                'test_char',
                'test_float',
                'test_only_write',
                'test_date',
                'test_datetime',
                'test_time',
                'test_decimal',
                'test_choice',
                'test_enum',
                'child',
                'children',
            ],
            'type': 'object',
        }
        self.assertEqual(self.serializer.to_openapi().serialize(), expected)


class SampleSerializerTestCase(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        class SampleSerializer(Serializer):
            test_char = CharField(description='test_char', max_length=18, min_length=1)
            test_int = IntegerField(description='test_int', max_value=10, min_value=1, allow_null=True, required=False)
            test_float = FloatField(description='test_float', max_value=10.0, min_value=1.0)

            test_only_read = CharField(description='test_only_read', read_only=True)
            test_only_write = CharField(description='test_only_write', write_only=True)

        self.sample_serializer = SampleSerializer()
        self.sample_serializer_class = SampleSerializer

    async def test_writable_fields(self):
        writable_fields = list(self.sample_serializer._writable_fields)
        writable_field_names = [
            'test_char',
            'test_int',
            'test_float',
            'test_only_write',
        ]
        self.assertEqual(writable_field_names, [field.field_name for field in writable_fields])

    async def test_readable_fields(self):
        readable_fields = list(self.sample_serializer._readable_fields)
        readable_field_names = [
            'test_char',
            'test_int',
            'test_float',
            'test_only_read',
        ]
        self.assertEqual(readable_field_names, [field.field_name for field in readable_fields])

    async def test_fields(self):
        field_names = [
            'test_char',
            'test_int',
            'test_float',
            'test_only_read',
            'test_only_write',
        ]
        self.assertEqual(field_names, [field.field_name for field in self.sample_serializer.fields.values()])

        class SampleSerializer2(self.sample_serializer_class):
            test_2 = CharField()

        field_names = field_names + ['test_2']
        serializer2 = SampleSerializer2()
        self.assertEqual(field_names, [field.field_name for field in serializer2.fields.values()])

    async def test_external_to_internal(self):
        data = {
            'test_char': 'test',
            'test_int': 1,
            'test_float': 1.1,
            'test_only_write': 'write_only_value',
        }
        result = await self.sample_serializer.external_to_internal(data)
        self.assertEqual(result, data)

    async def test_internal_to_external(self):
        data = {
            'test_char': 'test',
            'test_int': 1,
            'test_float': 1.1,
            'test_only_read': 'read_only_value',
        }
        result = await self.sample_serializer.internal_to_external(data)
        self.assertEqual(result, data)

    async def test_field_validate_method(self):
        class SampleSerializer3(self.sample_serializer_class):

            async def validate_test_int(self, value, data):
                if value == 8:
                    raise ValidationException({'test_int': 'test_int is 8'})
                return value

        serializer3 = SampleSerializer3()

        data = {
            'test_char': 'test',
            'test_int': 8,
            'test_float': 1.1,
            'test_only_write': 'write_only_value',
        }
        with self.assertRaises(ValidationException):
            await serializer3.external_to_internal(data)

        data = {
            'test_char': 'test',
            'test_int': 1,
            'test_float': 1.1,
            'test_only_write': 'write_only_value',
        }
        result = await serializer3.external_to_internal(data)
        self.assertEqual(result, data)

    async def test_allow_null_and_not_required(self):
        data = {
            'test_int': None,
            'test_char': 'test',
            'test_float': 1.1,
            'test_only_write': 'write_only_value',
        }
        result = await self.sample_serializer.external_to_internal(data)
        self.assertEqual(result, data)

    async def test_to_openapi(self):
        openapi_schema = self.sample_serializer.to_openapi()
        expected_schema = {
            "type": "object",
            "properties": {
                "test_char": {
                    "type": "string",
                    "description": "test_char",
                    "nullable": False,
                    "required": True,
                    "maxLength": 18,
                    "minLength": 1,
                },
                "test_int": {
                    "type": "integer",
                    "format": "int32",
                    "description": "test_int",
                    "nullable": True,
                    "required": False,
                    "maximum": 10,
                    "minimum": 1,
                },
                "test_float": {
                    "type": "number",
                    "format": "float",
                    "description": "test_float",
                    "nullable": False,
                    "required": True,
                    "maximum": 10.0,
                    "minimum": 1.0,
                },
                "test_only_read": {"type": "string", "description": "test_only_read", "nullable": False},
                "test_only_write": {"type": "string", "description": "test_only_write", "nullable": False, "required": True},
            },
            "required": ["test_char", "test_float", "test_only_write"],
        }

        self.assertEqual(openapi_schema.serialize(), expected_schema)

import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import BooleanField


class TestBooleanField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = BooleanField(allow_null=True, description='Ismail', default=True, required=True)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(
            self.field.TRUE_VALUES, {'t', 'T', 'y', 'Y', 'yes', 'YES', 'true', 'True', 'TRUE', 'on', 'On', 'ON', '1', 1, True}
        )
        self.assertEqual(
            self.field.FALSE_VALUES, {'f', 'F', 'n', 'N', 'no', 'NO', 'false', 'False', 'FALSE', 'off', 'Off', 'OFF', '0', 0, 0.0, False}
        )
        self.assertEqual(self.field.NULL_VALUES, {'null', 'Null', 'NULL', '', None})
        self.assertTrue(self.field.allow_null)

    async def test_external_to_internal_true_values(self):
        # Test valid true values
        for value in self.field.TRUE_VALUES:
            result = await self.field.external_to_internal(value)
            self.assertTrue(result)

    async def test_external_to_internal_false_values(self):
        # Test valid false values
        for value in self.field.FALSE_VALUES:
            result = await self.field.external_to_internal(value)
            self.assertFalse(result)

    async def test_external_to_internal_null_values(self):
        # Test valid null values
        for value in self.field.NULL_VALUES:
            result = await self.field.external_to_internal(value)
            self.assertIsNone(result)

    async def test_external_to_internal_invalid_value(self):
        # Test invalid input type
        data = "invalid_boolean"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external_true_values(self):
        # Test internal to external conversion for true values
        for value in self.field.TRUE_VALUES:
            result = await self.field.internal_to_external(value)
            self.assertTrue(result)

    async def test_internal_to_external_false_values(self):
        # Test internal to external conversion for false values
        for value in self.field.FALSE_VALUES:
            result = await self.field.internal_to_external(value)
            self.assertFalse(result)

    async def test_internal_to_external_null_values(self):
        # Test internal to external conversion for null values
        for value in self.field.NULL_VALUES:
            result = await self.field.internal_to_external(value)
            self.assertIsNone(result)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'boolean', 'description': 'Ismail', 'default': True, 'nullable': True, 'required': True}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)

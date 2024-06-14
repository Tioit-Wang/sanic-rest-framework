import unittest
import decimal

from rest_framework.exceptions import ValidationException
from rest_framework.fields import DecimalField


class TestDecimalField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.field = DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.max_digits, 10)
        self.assertEqual(self.field.decimal_places, 2)
        self.assertTrue(self.field.coerce_to_string)
        self.assertEqual(self.field.MAX_STRING_LENGTH, 1000)

    async def test_external_to_internal_valid_decimal(self):
        # Test valid decimal input
        data = "123.45"
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, decimal.Decimal("123.45"))

    async def test_external_to_internal_valid_integer(self):
        # Test valid integer input
        data = "123"
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, decimal.Decimal("123.00"))

    async def test_external_to_internal_invalid_type(self):
        # Test invalid input type
        data = "invalid_decimal"
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_external_to_internal_string_length_exceeded(self):
        # Test string input exceeding max length
        data = "1" * 1001
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = decimal.Decimal("123.45")
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, "123.45")

    async def test_max_value_validator(self):
        # Test max value validation
        field = DecimalField(max_digits=10, decimal_places=2, max_value=decimal.Decimal("100.00"))
        data = decimal.Decimal("200.00")
        with self.assertRaises(ValidationException):
            await field.run_validation(data)

    async def test_min_value_validator(self):
        # Test min value validation
        field = DecimalField(max_digits=10, decimal_places=2, min_value=decimal.Decimal("0.00"))
        data = decimal.Decimal("-10.00")
        with self.assertRaises(ValidationException):
            await field.run_validation(data)

    async def test_validate_precision(self):
        # Test precision validation
        data = decimal.Decimal("12345.678")
        with self.assertRaises(ValidationException):
            self.field.validate_precision(data)

    async def test_quantize(self):
        # Test quantization
        data = decimal.Decimal("123.4567")
        result = self.field.quantize(data)
        self.assertEqual(result, decimal.Decimal("123.46"))

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'number', 'format': 'float', 'nullable': False, 'required': True, 'maxLength': 1000}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)

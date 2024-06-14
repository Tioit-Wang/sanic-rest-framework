import unittest

from rest_framework.exceptions import ValidationException
from rest_framework.fields import ChoiceField


class TestChoiceField(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.choices = [(1, 'Choice 1'), (2, 'Choice 2'), (3, 'Choice 3')]
        self.field = ChoiceField(choices=self.choices)

    async def test_initialization(self):
        # Test that the field is initialized with the correct attributes
        self.assertEqual(self.field.choices, self.choices)

    async def test_external_to_internal_valid_choice(self):
        # Test valid choice input
        data = 1
        result = await self.field.external_to_internal(data)
        self.assertEqual(result, "Choice 1")

    async def test_external_to_internal_invalid_choice(self):
        # Test invalid choice input
        data = 4
        with self.assertRaises(ValidationException):
            await self.field.external_to_internal(data)

    async def test_internal_to_external(self):
        # Test internal to external conversion
        data = "Choice 2"
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, 2)

    async def test_internal_to_external_invalid_choice(self):
        # Test internal to external conversion for invalid choice
        data = 4
        result = await self.field.internal_to_external(data)
        self.assertEqual(result, 4)

    async def test_choices_get_value_by_key(self):
        # Test getting value by key
        result = self.field.choices_get_value_by_key(3)
        self.assertEqual(result, 'Choice 3')

    async def test_check_key_choices(self):
        # Test checking if key is a valid choice
        self.assertTrue(self.field.check_key_choices(1))
        self.assertFalse(self.field.check_key_choices(4))

    async def test_get_choices(self):
        # Test getting choices as dictionary
        expected = {1: 'Choice 1', 2: 'Choice 2', 3: 'Choice 3'}
        self.assertEqual(self.field.get_choices(), expected)

    async def test_to_openapi(self):
        # Test OpenAPI schema generation
        expected_schema = {'type': 'string', 'nullable': False, 'required': True, 'enum': [1, 2, 3]}
        self.assertEqual(self.field.to_openapi().serialize(), expected_schema)


if __name__ == "__main__":
    unittest.main()

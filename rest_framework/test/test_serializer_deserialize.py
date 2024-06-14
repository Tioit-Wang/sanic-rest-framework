import unittest
from collections import OrderedDict

from rest_framework.exceptions import ValidationException
from rest_framework.fields import CharField
from rest_framework.serializers import Serializer
from rest_framework.validators import BaseValidator


class SerializerDeserializeTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Serializer class's deserialization tests.

    Validates the handling of various parameters during deserialization by controlling individual parameters
    and observing their interaction with related parameters to ensure expected behavior.
    """

    async def test_field_required(self):
        """
        Validates the behavior of fields with the `required` parameter during deserialization.
        The required parameter defaults to True.
        """

        class TestSerializer(Serializer):
            test1 = CharField()
            test2 = CharField(required=False)

        # Positive scenario: Required field is provided.
        serializer = TestSerializer(data={'test1': 'test1'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'test1'}))

        # Negative scenario: Required field is missing.
        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)

        # Positive scenario: Non-required field is missing.
        serializer = TestSerializer(data={'test1': 'test1'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'test1'}))

    async def test_field_read_only(self):
        """
        Validates the behavior of fields with the `read_only` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(read_only=True)

        # Positive scenario: Read-only field is provided but not included in validated_data.
        serializer = TestSerializer(data={'test1': 'test1'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertNotIn('test1', serializer.validated_data)

        # Negative scenario: Read-only field should not cause validation failure.
        serializer = TestSerializer(data={})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})

    async def test_field_write_only(self):
        """
        Validates the behavior of fields with the `write_only` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(write_only=True)

        # Positive scenario: Write-only field is included in validated_data.
        serializer = TestSerializer(data={'test1': 'test1'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test1', serializer.validated_data)

    async def test_field_allow_null(self):
        """
        Validates the behavior of fields with the `allow_null` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(allow_null=True)

        # Positive scenario: Null value is accepted.
        serializer = TestSerializer(data={'test1': None})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': None}))

        # Negative scenario: Null value causes validation failure when allow_null is False.
        class TestSerializer2(Serializer):
            test1 = CharField()

        serializer = TestSerializer2(data={'test1': None})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)

    async def test_field_default(self):
        """
        Validates the behavior of fields with the `default` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(default='default_value')

        # Positive scenario: Default value is used when no data is provided.
        serializer = TestSerializer(data={})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'default_value'}))

        # Negative scenario: Default value does not overwrite provided data.
        serializer = TestSerializer(data={'test1': 'override'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'override'}))

    async def test_field_source(self):
        """
        Validates the behavior of fields with the `source` parameter during deserialization.
        The source parameter affects the serializer, not the deserializer.
        """

        class TestSerializer(Serializer):
            test1 = CharField(source='source_field')

        # Positive scenario: Source field maps correctly.
        serializer = TestSerializer(data={'test1': 'test1'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'test1'}))

        # Negative scenario: Source field is not found.
        serializer = TestSerializer(data={'wrong_source': 'test1'})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)

    async def test_field_validators(self):
        """
        Validates the behavior of fields with the `validators` parameter during deserialization.
        """

        def custom_validator(value, field):
            if value != 'valid':
                raise ValidationException('Invalid value')

        class TestSerializer(Serializer):
            test1 = CharField(validators=[custom_validator])

        # Positive scenario: Validation passes with correct value.
        serializer = TestSerializer(data={'test1': 'valid'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'valid'}))

        # Negative scenario: Validation fails with incorrect value.
        serializer = TestSerializer(data={'test1': 'invalid'})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)

    async def test_field_error_messages(self):
        """
        Validates the behavior of fields with the `error_messages` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(error_messages={'required': 'Custom error message'})

        # Positive scenario: Custom error message is displayed for missing required field.
        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)
        self.assertIn('Custom error message', serializer.errors['test1'][0])

        # Negative scenario: Standard error message is used when no custom message is provided.
        class TestSerializer2(Serializer):
            test1 = CharField(required=True)

        serializer = TestSerializer2(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test1', serializer.errors)
        self.assertNotIn('Custom error message', serializer.errors['test1'][0])

    async def test_field_description(self):
        """
        Validates the behavior of fields with the `description` parameter during deserialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(description='Test description')

        # Positive scenario: Description is accessible via the field.
        serializer = TestSerializer()
        self.assertEqual(serializer.fields['test1'].description, 'Test description')

        # Negative scenario: Description does not affect deserialization.
        serializer = TestSerializer(data={'test1': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertEqual(serializer.validated_data, OrderedDict({'test1': 'test'}))


class SerializerDeserializeCombinedFieldsTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Tests the handling of various parameter combinations during deserialization by the Serializer class.
    Validates the behavior of different parameter configurations in the deserialization process.
    """

    async def test_read_only_with_required(self):
        # Attempting to create a field with read_only=True and required=True should raise an AssertionError
        with self.assertRaises(AssertionError):

            class TestSerializer(Serializer):
                test_read_only_required = CharField(read_only=True, required=True)

        # When data is provided for a read_only=True field, it should not appear in the validated_data
        class Test2Serializer(Serializer):
            test_read_only_required = CharField(read_only=True)

        serializer = Test2Serializer(data={'test_read_only_required': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertNotIn('test_read_only_required', serializer.validated_data)

    async def test_read_only_with_default(self):
        # Even when data is provided, a read_only=True field with a default value should not appear in validated_data
        class TestSerializer(Serializer):
            test_read_only_default = CharField(read_only=True, default='default_value')

        serializer = TestSerializer(data={'test_read_only_default': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertNotIn('test_read_only_default', serializer.validated_data)

        # When no data is provided, a read_only=True field with a default value should not appear in validated_data
        serializer = TestSerializer(data={})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertNotIn('test_read_only_default', serializer.validated_data)

    async def test_write_only_with_required(self):
        # For a write_only=True field, if required=True, validation should succeed when data is provided
        class TestSerializer(Serializer):
            test_write_only_required = CharField(write_only=True, required=True)

        serializer = TestSerializer(data={'test_write_only_required': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_write_only_required', serializer.validated_data)

        # For a write_only=True field, if required=True, validation should fail when no data is provided
        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test_write_only_required', serializer.errors)

        # For a write_only=True field, if required=False, validation should succeed when data is provided
        class Test2Serializer(Serializer):
            test_write_only_required = CharField(write_only=True, required=False)

        serializer = Test2Serializer(data={'test_write_only_required': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_write_only_required', serializer.validated_data)

        # For a write_only=True field, if required=False, validation should succeed and the field should not be included when no data is provided
        serializer = Test2Serializer(data={})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertNotIn('test_write_only_required', serializer.validated_data)

    async def test_write_only_with_default(self):
        # For a write_only=True field, with a default value, if no data is provided, the field should appear in validated_data using the default value
        class TestSerializer(Serializer):
            test_write_only_default = CharField(write_only=True, default='default_value')

        serializer = TestSerializer(data={})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_write_only_default', serializer.validated_data)
        self.assertEqual(serializer.validated_data['test_write_only_default'], 'default_value')

        # For a write_only=True field, with a default value, if data is provided, the field should appear in validated_data using the provided data
        serializer = TestSerializer(data={'test_write_only_default': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_write_only_default', serializer.validated_data)
        self.assertEqual(serializer.validated_data['test_write_only_default'], 'test')

    async def test_required_with_allow_null(self):
        # For a required=True field, if allow_null=True, null values should be allowed
        class TestSerializer(Serializer):
            test_required_allow_null = CharField(required=True, allow_null=True)

        serializer = TestSerializer(data={'test_required_allow_null': None})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_required_allow_null', serializer.validated_data)
        self.assertIsNone(serializer.validated_data['test_required_allow_null'])

        # For a required=True field, if allow_null=True, validation should fail when no data is provided
        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test_required_allow_null', serializer.errors)

    async def test_required_with_source(self):
        # For a required=True field, when using source, data should be retrieved from the specified source
        class TestSerializer(Serializer):
            test_required_source = CharField(required=True, source='real_source')

        serializer = TestSerializer(data={'test_required_source': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_required_source', serializer.validated_data)
        self.assertEqual(serializer.validated_data['test_required_source'], 'test')

        # For a required=True field, when using source, validation should fail if the specified source data is not provided
        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test_required_source', serializer.errors)

    async def test_required_with_validators(self):
        # Define a custom validator
        class EqualToValidator(BaseValidator):
            default_error_messages = {
                'invalid_value': 'Invalid value. Expected {expected}, received {actual}.',
            }

            def __call__(self, value, serializer=None):
                if value != 'valid':
                    self.raise_error('invalid_value', expected='valid', actual=value)

        # For a required=True field, when using validators, data should pass through the validator
        class TestSerializer(Serializer):
            test_required_validators = CharField(required=True, validators=[EqualToValidator()])

        serializer = TestSerializer(data={'test_required_validators': 'valid'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_required_validators', serializer.validated_data)
        self.assertEqual(serializer.validated_data['test_required_validators'], 'valid')

        # For a required=True field, when using validators, validation should fail if data does not pass through the validator
        serializer = TestSerializer(data={'test_required_validators': 'invalid'})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test_required_validators', serializer.errors)
        self.assertEqual(serializer.errors['test_required_validators'][0], 'Invalid value. Expected valid, received invalid.')

    async def test_required_with_error_messages(self):
        # For a required=True field, when using custom error messages, validation failure should display the custom error message
        class TestSerializer(Serializer):
            test_required_error_messages = CharField(required=True, error_messages={'required': 'Custom required message'})

        serializer = TestSerializer(data={})
        self.assertFalse(await serializer.is_valid())
        self.assertIn('test_required_error_messages', serializer.errors)
        self.assertEqual(serializer.errors['test_required_error_messages'][0], 'Custom required message')

        # For a required=True field, when using custom error messages, validation success should not display the error message
        serializer = TestSerializer(data={'test_required_error_messages': 'test'})
        self.assertTrue(await serializer.is_valid())
        self.assertEqual(serializer.errors, {})
        self.assertIn('test_required_error_messages', serializer.validated_data)
        self.assertEqual(serializer.validated_data['test_required_error_messages'], 'test')


if __name__ == '__main__':
    unittest.main()

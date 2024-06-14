import unittest
from collections import OrderedDict
from rest_framework.fields import CharField
from rest_framework.serializers import Serializer
from rest_framework.exceptions import ValidationException
from rest_framework.validators import BaseValidator


class SerializerSerializationTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Serializer class's serialization tests.

    Validates the handling of various parameters during serialization by controlling individual parameters
    and observing their interaction with related parameters to ensure expected behavior.
    """

    async def test_field_required(self):
        """
        Validates the behavior of fields with the `required` parameter during serialization.
        The required parameter defaults to True.
        """

        class TestSerializer(Serializer):
            test1 = CharField()
            test2 = CharField(required=False)  # allow_null 在 serializer 中被忽略, 无值即为None

        # Positive scenario: Required field is provided.
        serializer = TestSerializer(instance={'test1': 'test1'})
        data = await serializer.data
        self.assertEqual(data, OrderedDict({'test1': 'test1', 'test2': None}))

        # Negative scenario: Required field is missing.
        serializer = TestSerializer(instance={})
        with self.assertRaises(ValidationException):
            await serializer.data

    async def test_field_read_only(self):
        """
        Validates the behavior of fields with the `read_only` parameter during serialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(read_only=True)

        # Positive scenario: Read-only field is included in serialized data.
        serializer = TestSerializer(instance={'test1': 'test1'})
        self.assertEqual(await serializer.data, OrderedDict({'test1': 'test1'}))

    async def test_field_write_only(self):
        """
        Validates the behavior of fields with the `write_only` parameter during serialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(write_only=True)

        # Positive scenario: Write-only field is not included in serialized data.
        serializer = TestSerializer(instance={'test1': 'test1'})
        self.assertEqual(await serializer.data, OrderedDict())

    async def test_field_allow_null(self):
        """
        allow_null 在 serializer 中不生效
        """
        pass

    async def test_field_default(self):
        """
        default 优先于 required
        """

        class TestSerializer(Serializer):
            test1 = CharField(default='default_value')

        # Positive scenario: Default value is used when no data is provided.
        serializer = TestSerializer(instance={})
        self.assertEqual(await serializer.data, OrderedDict({'test1': 'default_value'}))

        # Negative scenario: Default value does not overwrite provided data.
        serializer = TestSerializer(instance={'test1': 'override'})
        self.assertEqual(await serializer.data, OrderedDict({'test1': 'override'}))

    async def test_field_source(self):
        """
        Validates the behavior of fields with the `source` parameter during serialization.
        The source parameter affects the serializer, not the deserializer.
        """

        class TestSerializer(Serializer):
            test1 = CharField(source='source_field')

        # Positive scenario: Source field maps correctly.
        serializer = TestSerializer(instance={'source_field': 'test1'})
        self.assertEqual(await serializer.data, OrderedDict({'test1': 'test1'}))

        # Negative scenario: Source field is not found.
        serializer = TestSerializer(instance={'wrong_source': 'test1'})
        with self.assertRaises(ValidationException):
            await serializer.data

    async def test_field_validators(self):
        """
        srf 对 instance 提供的数据是绝对信任的，除了转换格式外是不验证的
        """
        pass

    async def test_field_error_messages(self):
        """
        error_messages 在 serializer 中不生效
        """
        pass

    async def test_field_description(self):
        """
        Validates the behavior of fields with the `description` parameter during serialization.
        """

        class TestSerializer(Serializer):
            test1 = CharField(description='Test description')

        # Positive scenario: Description is accessible via the field.
        serializer = TestSerializer()
        self.assertEqual(serializer.fields['test1'].description, 'Test description')

        # Negative scenario: Description does not affect serialization.
        serializer = TestSerializer(instance={'test1': 'test'})
        self.assertEqual(await serializer.data, OrderedDict({'test1': 'test'}))


class SerializerSerializationCombinedFieldsTestCase(unittest.IsolatedAsyncioTestCase):
    """
    Serializer 类的序列化测试。

    Tests the handling of various parameter combinations during serialization by the Serializer class.
    Validates the behavior of different parameter configurations in the serialization process.
    """

    async def test_read_only_with_required(self):
        """
        验证 read_only=True 和 required=True 组合时的行为。
        Validates the behavior when combining read_only=True and required=True.
        """

        with self.assertRaises(AssertionError):

            class TestSerializer(Serializer):
                test_read_only_required = CharField(read_only=True, required=True)

        class Test2Serializer(Serializer):
            test_read_only_required = CharField(read_only=True)

        serializer = Test2Serializer(instance={'test_read_only_required': 'test'})
        self.assertEqual(await serializer.data, OrderedDict({'test_read_only_required': 'test'}))

    async def test_read_only_with_default(self):
        """
        验证 read_only=True 和 default 组合时的行为。
        Validates the behavior when combining read_only=True and default.
        """

        class TestSerializer(Serializer):
            test_read_only_default = CharField(read_only=True, default='default_value')

        serializer = TestSerializer(instance={'test_read_only_default': 'test'})
        self.assertEqual(await serializer.data, OrderedDict({'test_read_only_default': 'test'}))

        serializer = TestSerializer(instance={})
        self.assertEqual(await serializer.data, OrderedDict({'test_read_only_default': 'default_value'}))

    async def test_write_only_with_required(self):
        """
        验证 write_only=True 和 required=True 组合时的行为。
        Validates the behavior when combining write_only=True and required=True.
        """

        class TestSerializer(Serializer):
            test_write_only_required = CharField(write_only=True, required=True)

        serializer = TestSerializer(instance={'test_write_only_required': 'test'})
        self.assertEqual(await serializer.data, OrderedDict())

        serializer = TestSerializer(instance={})
        self.assertEqual(await serializer.data, OrderedDict())

        class Test2Serializer(Serializer):
            test_write_only_required = CharField(write_only=True, required=False)

        serializer = Test2Serializer(instance={'test_write_only_required': 'test'})
        self.assertEqual(await serializer.data, OrderedDict())

        serializer = Test2Serializer(instance={})
        self.assertEqual(await serializer.data, OrderedDict())

    async def test_write_only_with_default(self):
        """
        验证 write_only=True 和 default 组合时的行为。
        Validates the behavior when combining write_only=True and default.
        """

        class TestSerializer(Serializer):
            test_write_only_default = CharField(write_only=True, default='default_value')

        serializer = TestSerializer(instance={})
        self.assertEqual(await serializer.data, OrderedDict())

        serializer = TestSerializer(instance={'test_write_only_default': 'test'})
        self.assertEqual(await serializer.data, OrderedDict())

    async def test_required_with_allow_null(self):
        """
        验证 required=True 和 allow_null=True 组合时的行为。
        Validates the behavior when combining required=True and allow_null=True.
        """

        class TestSerializer(Serializer):
            test_required_allow_null = CharField(required=True, allow_null=True)

        serializer = TestSerializer(instance={'test_required_allow_null': None})
        self.assertEqual(await serializer.data, OrderedDict({'test_required_allow_null': None}))

        serializer = TestSerializer(instance={})
        with self.assertRaises(ValidationException):
            await serializer.data

    async def test_required_with_source(self):
        """
        验证 required=True 和 source 组合时的行为。
        Validates the behavior when combining required=True and source.
        """

        class TestSerializer(Serializer):
            test_required_source = CharField(required=True, source='real_source')

        serializer = TestSerializer(instance={'real_source': 'test'})
        self.assertEqual(await serializer.data, OrderedDict({'test_required_source': 'test'}))

        serializer = TestSerializer(instance={})
        with self.assertRaises(ValidationException):
            await serializer.data

    async def test_required_with_validators(self):
        """
        验证 required=True 和 validators 组合时的行为。
        Validates the behavior when combining required=True and validators.

        Note: 在设计中 `validators` 是不在 Serialization 中生效的
        """
        pass

    async def test_required_with_error_messages(self):
        """
        验证 required=True 和 error_messages 组合时的行为。
        Validates the behavior when combining required=True and error_messages.
        """

        class TestSerializer(Serializer):
            test_required_error_messages = CharField(required=True, error_messages={'required': 'Custom required message'})

        serializer = TestSerializer(instance={})
        with self.assertRaises(ValidationException):
            await serializer.data

        serializer = TestSerializer(instance={'test_required_error_messages': 'test'})
        self.assertEqual(await serializer.data, OrderedDict({'test_required_error_messages': 'test'}))


if __name__ == '__main__':
    unittest.main()

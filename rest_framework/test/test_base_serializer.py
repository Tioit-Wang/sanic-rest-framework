import unittest
from rest_framework.serializers import BaseSerializer
from rest_framework.fields import Field, empty
from rest_framework.exceptions import ValidationException


class TestBaseSerializer(unittest.IsolatedAsyncioTestCase):
    class DummySerializer(BaseSerializer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        async def external_to_internal(self, data):
            # 模拟外部数据转换为内部数据
            return {key: value.upper() if isinstance(value, str) else value for key, value in data.items()}

        async def internal_to_external(self, data):
            # 模拟内部数据转换为外部数据
            return {key: value.lower() if isinstance(value, str) else value for key, value in data.items()}

        async def validate(self, attr):
            # 模拟验证逻辑
            if 'name' not in attr:
                raise ValidationException("Field 'name' is required.")
            return attr

        async def create(self, validated_data):
            # 模拟创建逻辑
            return validated_data

        async def update(self, instance, validated_data):
            # 模拟更新逻辑
            instance.update(validated_data)
            return instance

    def setUp(self):
        self.data = {'name': 'John Doe', 'age': 30}
        self.instance = {'name': 'Jane Doe', 'age': 25}
        self.serializer = self.DummySerializer(instance=self.instance, data=self.data)

    async def test_initialization(self):
        self.assertEqual(self.serializer.initial_data, self.data)
        self.assertEqual(self.serializer.instance, self.instance)

    async def test_is_valid(self):
        is_valid = await self.serializer.is_valid()
        self.assertTrue(is_valid)

    async def test_is_valid_with_invalid_data(self):
        invalid_data = {'age': 30}
        serializer = self.DummySerializer(data=invalid_data)
        is_valid = await serializer.is_valid()
        self.assertFalse(is_valid)
        self.assertIn("Field 'name' is required.", serializer.errors)

    async def test_save_create(self):
        serializer = self.DummySerializer(data=self.data)
        await serializer.is_valid()
        created_instance = await serializer.save()
        self.assertEqual(created_instance['name'], 'JOHN DOE')
        self.assertEqual(created_instance['age'], 30)

    async def test_save_update(self):
        await self.serializer.is_valid()
        updated_instance = await self.serializer.save()
        self.assertEqual(updated_instance['name'], 'JOHN DOE')
        self.assertEqual(updated_instance['age'], 30)

    async def test_data_property(self):
        await self.serializer.is_valid()
        data = await self.serializer.data
        self.assertEqual(data['name'], 'jane doe')
        self.assertEqual(data['age'], 25)

    async def test_validated_data_property(self):
        await self.serializer.is_valid()
        validated_data = self.serializer.validated_data
        self.assertEqual(validated_data['name'], 'JOHN DOE')
        self.assertEqual(validated_data['age'], 30)

    async def test_errors_property(self):
        invalid_data = {'age': 30}
        serializer = self.DummySerializer(data=invalid_data)
        await serializer.is_valid()
        errors = serializer.errors
        self.assertIn("Field 'name' is required.", errors)


if __name__ == '__main__':
    unittest.main()

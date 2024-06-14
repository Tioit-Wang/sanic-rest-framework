"""
@Author: TioitWang
@E-mile: me@tioit.cc
@CreateTime: 2021/1/20 13:20
@DependencyLibrary:
@MainFunction:
@FileDoc:
    qr.py
    序列化器文件
"""

import copy
from functools import lru_cache
import inspect
import traceback
from collections import OrderedDict
from typing import Any, Mapping

from tortoise import fields as tortoise_fields
from tortoise.fields.relational import ReverseRelation
from tortoise.queryset import ValuesListQuery, ValuesQuery

from rest_framework.constant import ALL_FIELDS, LIST_SERIALIZER_KWARGS
from rest_framework.converter import DEFAULT_NESTED_DEPTH, ModelConverter
from rest_framework.exceptions import ValidationException
from rest_framework.fields import Field, SkipField, empty
from rest_framework.helpers import BindingDict
from rest_framework.openapi3.types import Array, Object, Schema
from rest_framework.utils import run_awaitable, run_awaitable_val


def set_value(dictionary: dict, keys: list, value: Any) -> None:
    """
    set_value({'a': 1}, [], {'b': 2}) -> {'a': 1, 'b': 2}
    set_value({'a': 1}, ['x'], 2) -> {'a': 1, 'x': 2}
    set_value({'a': 1}, ['x', 'y'], 2) -> {'a': 1, 'x': {'y': 2}}
    """
    if not keys:
        dictionary.update(value)
        return

    for key in keys[:-1]:
        dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value


class BaseSerializer(Field):
    """Serializer
    .instance ->
        .get_internal_value ->
            .internal_to_external() ->
                .data

    .install_data -> .get_external_value -> .external_to_internal() -> .validated_data
    """

    def __init__(self, instance=None, data=empty, **kwargs):
        self.instance = instance
        if data is not empty:
            self.initial_data = data
        self.partial = kwargs.pop('partial', False)
        self._context = kwargs.pop('context', {})
        self.__kwargs = kwargs
        super().__init__(**kwargs)

    def __new__(cls, *args, **kwargs):
        if kwargs.pop('many', False):
            return cls.many_init(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """Initialize multivalued serializer"""
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
            'context': child_serializer._context,
        }
        list_kwargs.update({key: value for key, value in kwargs.items() if key in LIST_SERIALIZER_KWARGS})
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', ListSerializer)
        return list_serializer_class(*args, **list_kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        """Serialized data conversion and return."""
        raise NotImplementedError(f'`{self.__class__.__name__}.external_to_internal` method must override.')

    async def internal_to_external(self, data: Any) -> Any:
        """Deserialize the data and return it."""
        raise NotImplementedError(f'`{self.__class__.__name__}.internal_to_external` method must override.')

    async def validate(self, attr):
        return attr

    async def run_validation(self, data):
        value = await super(BaseSerializer, self).run_validation(data)
        value = await run_awaitable_val(self.validate(value))
        return value

    async def update(self, instance, validated_data):
        """
        This method is defined in the base class for updating a given ORM instance.
        Subclasses should override this method to customize the update logic for their specific ORM or business requirements.
        By default, this method raises a `NotImplementedError`, indicating that subclasses need to provide their own implementation.

        In a general-purpose serializer, it's crucial not to bind to a specific ORM or enforce fixed business logic.
        This design allows the serializer to be flexible and reusable across different contexts and data models.

        Args:
            instance (Any): The ORM instance to update.
            validated_data (dict): The validated data to update the instance with.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError('`update()` must be implemented.')

    async def create(self, validated_data):
        """
        This method is defined in the base class for creating a new ORM instance.
        Subclasses should override this method to customize the creation logic for their specific ORM or business requirements.
        By default, this method raises a `NotImplementedError`, indicating that subclasses need to provide their own implementation.

        In a general-purpose serializer, it's crucial not to bind to a specific ORM or enforce fixed business logic.
        This design allows the serializer to be flexible and reusable across different contexts and data models.

        Args:
            validated_data (dict): The validated data to create the new instance with.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

        raise NotImplementedError('`create()` must be implemented.')

    async def save(self, **kwargs):
        assert hasattr(self, '_errors'), 'You must call `.is_valid()` before calling `.save()`.'
        assert not self.errors, 'You cannot call `.save()` on a serializer with invalid data.'
        assert 'commit' not in kwargs, (
            "'commit' is not a valid keyword argument to the 'save()' method. "
            "If you need to access data before committing to the database then "
            "inspect 'serializer.validated_data' instead. "
        )
        assert not hasattr(self, '_data'), "You cannot call `.save()` after accessing `serializer.data`."

        validated_data = {**self.validated_data, **kwargs}
        if self.instance is not None:
            self.instance = await self.update(self.instance, validated_data)
            assert self.instance is not None, '`update()` did not return an object instance.'
        else:
            self.instance = await self.create(validated_data)
            assert self.instance is not None, '`create()` did not return an object instance.'
        return self.instance

    async def is_valid(self, raise_exception=False):
        assert hasattr(self, 'initial_data'), (
            'Cannot call `.is_valid()` as no `data=` keyword argument was ' 'passed when instantiating the serializer instance.'
        )

        if hasattr(self, '_validated_data'):
            return not bool(self._errors)

        try:
            self._validated_data = await self.run_validation(self.initial_data)
        except ValidationException as exc:
            self._validated_data = {}
            self._errors = exc.error_detail
        else:
            self._errors = {}

        if self._errors and raise_exception:
            raise ValidationException(self.errors)
        return not bool(self._errors)

    @property
    async def data(self):
        assert self.instance is not None, (
            'When a serializer is passed a `data` keyword argument you '
            'must call `.is_valid()` before attempting to access the '
            'serialized `.data` representation.'
        )
        if not hasattr(self, '_data'):
            self._data = await self.internal_to_external(self.instance)
        return self._data

    @property
    def errors(self):
        if not hasattr(self, '_errors'):
            raise AssertionError('You must call `.is_valid()` before accessing `.errors`.')
        return self._errors

    @property
    def validated_data(self):
        """Data validated for internal use"""
        if not hasattr(self, '_validated_data'):
            raise AssertionError('You must call `.is_valid()` before accessing `.validated_data`.')
        return self._validated_data


class SerializerMetaclass(type):

    @classmethod
    def _get_declared_fields(cls, bases, attrs):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in list(attrs.items()) if isinstance(obj, Field)]
        fields.sort(key=lambda x: x[1]._sort_counter)

        known = set(attrs)

        def visit(name):
            known.add(name)
            return name

        base_fields = []
        for base in bases:
            if hasattr(base, '_declared_fields'):
                for name, field in base._declared_fields.items():
                    if name not in known:
                        base_fields.append((visit(name), field))

        return OrderedDict(base_fields + fields)

    def __new__(cls, name, bases, attrs):
        attrs['_declared_fields'] = cls._get_declared_fields(bases, attrs)
        return super().__new__(cls, name, bases, attrs)


class Serializer(BaseSerializer, metaclass=SerializerMetaclass):
    default_error_messages = {'invalid': 'Invalid data. Expected a dictionary, but got {datatype}.'}

    @property
    @lru_cache()
    def fields(self):
        """
        {field_name: field_instance}.
        Fields are dynamically loaded to avoid unexpected errors during import.
        """
        fields = BindingDict(self)
        for key, value in self.get_fields().items():
            fields[key] = value
        return fields

    @property
    def _writable_fields(self):
        return (field for field in self.fields.values() if not field.read_only)

    @property
    def _readable_fields(self):
        return (field for field in self.fields.values() if not field.write_only)

    def get_fields(self) -> dict:
        return copy.deepcopy(self._declared_fields)

    async def internal_to_external(self, data: Any) -> Any:
        """
        Convert Python type to JSON type
        :param data: Data to convert
        :return: Converted data
        """
        res = OrderedDict()
        for field in self._readable_fields:
            try:
                value = await field.get_internal_value(data)
            except SkipField:
                continue
            if value is not None:
                value = await field.internal_to_external(value)
            res[field.field_name] = value
        return res

    async def external_to_internal(self, data: Any) -> Any:
        """
        Convert JSON type to Python type

        :param data: Data to convert
        :return: Converted data

        This method converts the JSON-like data to Python types. It first retrieves the writable
        fields and then iterates over them. Each field is processed in the following steps:

        1. The value for the field is retrieved from the input data.
        2. The value is validated against the field's type and constraints.
        3. If the validation passes, the value is set in the resulting dictionary.

        If any validation errors occur, a `ValidationException` is raised with the details of the errors.
        """
        res = OrderedDict()
        errors = OrderedDict()
        for field in self._writable_fields:
            validate_method = getattr(self, f'validate_{field.field_name}', None)
            try:
                primitive_value = await field.get_external_value(data)
                validated_value = await field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = await run_awaitable(validate_method, validated_value, data)
            except ValidationException as exc:
                errors[field.field_name] = exc.error_detail
            except SkipField:
                pass
            else:
                # `source` is not used in deserialize process.
                set_value(res, [field.field_name], validated_value)
        if errors:
            raise ValidationException(errors)
        return res

    async def validate(self, attrs):
        return attrs

    def __iter__(self):
        for field in self.fields.values():
            yield self[field.field_name]

    def __getitem__(self, key):
        field = self.fields[key]
        value = self.data.get(key)
        error = self.errors.get(key) if hasattr(self, '_errors') else None
        return {
            'field': field,
            'value': value,
            'error': error,
        }

    def to_openapi(self) -> Schema:
        properties = {}
        required_fields = []

        for field_name, field in self.fields.items():
            properties[field_name] = field.to_openapi()
            if field.required and not self.partial:
                required_fields.append(field_name)

        return Object(properties=properties, required=required_fields)


class ListSerializer(BaseSerializer):
    child = None
    many = True

    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'null': 'This list may not be empty.',
    }

    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        assert self.child is not None, '`child` is a required argument.'
        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        super().__init__(*args, **kwargs)
        self.child.bind(field_name='', parent=self)

    async def get_internal_value(self, instance: Any) -> Any:
        for attr in self.source_attrs:
            if isinstance(instance, Mapping):
                instance = instance.get(attr, [])
                if not isinstance(instance, list):
                    instance = [instance]
            else:
                instance = getattr(instance, attr)
        return instance

    async def internal_to_external(self, data: Any) -> Any:
        """
        Convert Python type to JSON type for lists
        :param data: Data to convert
        :return: Converted data
        """
        if not inspect.isawaitable(data):
            iterable = data
        elif isinstance(data, (ValuesQuery, ValuesListQuery)):
            iterable = await data
        elif isinstance(data, ReverseRelation):
            iterable = data.related_objects if data._fetched else await data.all()
        else:
            iterable = await data.all()

        return [await self.child.internal_to_external(item) for item in iterable]

    async def external_to_internal(self, data: Any) -> Any:
        """
        Convert JSON type to Python type for lists
        :param data: Data to convert
        :return: Converted data
        """
        if not isinstance(data, list):
            raise self.raise_error('not_a_list', input_type=type(data).__name__)

        if not self.allow_null and not data:
            raise self.raise_error('null')

        ret = []
        errors = []

        for item in data:
            try:
                value = await self.child.run_validation(item)
            except ValidationException as exc:
                errors.append(exc.error_detail)
            else:
                ret.append(value)
                errors.append({})
        if any(errors):
            raise ValidationException(errors)
        return ret

    async def run_validation(self, data=empty):
        """
        Override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a 'non_fields_error' key.
        """
        is_empty_value, data = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = await self.external_to_internal(data)
        self.run_validators(value)
        value = await self.validate(value)
        return value

    async def update(self, instance, validated_data):
        raise NotImplementedError(
            "Serializers with many=True do not support multiple update by "
            "default, only multiple create. For updates it is unclear how to "
            "deal with insertions and deletions. If you need to support "
            "multiple update, use a `ListSerializer` class and override "
            "`.update()` so you can specify the behavior exactly."
        )

    async def create(self, validated_data):
        """
        Create instances from validated data
        """
        return [await self.child.create(attrs) for attrs in validated_data]

    async def save(self, **kwargs):
        """
        Save instances
        """
        assert 'commit' not in kwargs, (
            "`commit` is not a valid keyword argument for `save()`."
            "If you need to access data before committing to the database, "
            "consider checking `serializer.validated_data` instead."
            "You may also pass additional keyword arguments to `save()` "
            "to set extra attributes on the saved model instance(s)."
            "For example, 'serializer.save(owner=request.user)'."
        )

        validated_data = [{**attrs, **kwargs} for attrs in self.validated_data]

        if self.instance is None:
            self.instance = await self.create(validated_data)
            assert self.instance is not None, '`create()` did not return an object instance.'
        else:
            self.instance = await self.update(self.instance, validated_data)
            assert self.instance is not None, '`update()` did not return an object instance.'

        return self.instance

    def to_openapi(self) -> Schema:
        assert self.child is not None, '`child` is a required argument.'
        child_schema = self.child.to_openapi()
        return Array(items=child_schema)


class ModelSerializer(Serializer):
    """
    class Meta:
        model = None
        depth = 0
        extra_kwargs = {}
        fields = ()  # 冲突，不能与exclude共存
        exclude = ()  # 冲突，不能与fields共存
        read_only_fields = ()  # 字段与write_only_fields冲突
        write_only_fields = ()  # 字段与read_only_fields冲突
    """

    @property
    def fields(self):
        assert hasattr(self, 'Meta'), 'The {serializer_class} class has no "Meta" attribute.'.format(
            serializer_class=self.__class__.__name__
        )
        assert hasattr(self.Meta, 'model'), 'The {serializer_class} class has no "Meta.model" attribute.'.format(
            serializer_class=self.__class__.__name__
        )
        if self.Meta.model._meta.abstract:
            raise ValueError('不能将ModelSerializer与抽象模型一起使用。')
        depth = getattr(self.Meta, 'depth', DEFAULT_NESTED_DEPTH)
        if depth is not None:
            assert depth >= 0, "'depth' may not be negative."
            assert depth <= 10, "'depth' may not be greater than 10."

        declared_fields = copy.deepcopy(self._declared_fields)
        model_meta = getattr(self.Meta, 'model')
        meta_fields = getattr(self.Meta, 'fields', None)

        converter = ModelConverter(ModelSerializer)
        model_fields_map = model_meta._meta.fields_map
        # fields_without_relation_id = self.clean_id_fields_from_relations(model_fields_map)
        fields_filtered_by_depth = self.filter_fields_by_depth(model_fields_map, depth)
        usable_fields = self.determine_usable_fields(fields_filtered_by_depth)
        configured_fields = BindingDict(self)

        for field_name, field_class in usable_fields.items():
            field_kwargs = self.get_field_kwargs_by_meta(field_name, model_meta)
            current_field_instance = converter.convert(self, field_class, **field_kwargs)
            configured_fields[field_name] = current_field_instance

        if meta_fields is not None and meta_fields != ALL_FIELDS:
            for field_name in declared_fields:
                assert (
                    field_name in meta_fields
                ), "declared field '{field_name}' is not present in " "Meta.fields of {serializer_class}".format(
                    field_name=field_name, serializer_class=self.__class__.__name__
                )
        configured_fields.update(declared_fields)
        return configured_fields

    def clean_id_fields_from_relations(self, model_fields):
        foreign_key_field_types = (
            tortoise_fields.relational.ForeignKeyFieldInstance,
            tortoise_fields.relational.OneToOneFieldInstance,
        )
        excluded_field_ids = []
        for field_name, field_instance in model_fields.items():
            if isinstance(field_instance, (*foreign_key_field_types,)):
                excluded_field_ids.append(f'{field_name}_id')
        return {field_name: field_instance for field_name, field_instance in model_fields.items() if field_name not in excluded_field_ids}

    def filter_fields_by_depth(self, model_fields, depth):
        if depth > 0:
            return model_fields
        return {
            field_name: field_instance
            for field_name, field_instance in model_fields.items()
            if not isinstance(
                field_instance, (tortoise_fields.relational.RelationalField, tortoise_fields.relational.OneToOneFieldInstance)
            )
        }

    def determine_usable_fields(self, model_fields) -> dict:
        meta_fields = getattr(self.Meta, 'fields', None)
        meta_exclude = getattr(self.Meta, 'exclude', None)
        if meta_exclude and meta_fields:
            raise ValueError(f'class ”{self.__class__.__name__}“ ’Meta.fields‘ 和 ’Meta.exclude‘ 不可以共存 ')
        relationship_field_names = self.get_relationship_field_names(model_fields)

        if meta_exclude is not None:
            return {
                field_name: field_instance
                for field_name, field_instance in model_fields.items()
                if field_name not in meta_exclude and field_name not in relationship_field_names
            }
        elif meta_fields is None or meta_fields is ALL_FIELDS:
            return {
                field_name: field_instance
                for field_name, field_instance in model_fields.items()
                if field_name not in relationship_field_names
            }
        else:
            return {field_name: field_instance for field_name, field_instance in model_fields.items() if field_name in meta_fields}

    def get_field_kwargs_by_meta(self, field_name, model):
        """
        判断当前字段是否在Meat内设置了只读或只写
        :param field_name:
        :return:
        """
        read_only_fields = getattr(self.Meta, 'read_only_fields', [])
        write_only_fields = getattr(self.Meta, 'write_only_fields', [])
        if field_name in read_only_fields and field_name in write_only_fields:
            raise ValueError(
                f'字段 {field_name} 不可用同时存在于类 ”{self.__class__.__name__}“ '
                f'的 ’Meta.read_only_fields‘ 和 ’Meta.write_only_fields‘ 属性中'
            )

        if field_name in read_only_fields:
            return {'read_only': True, 'write_only': False}
        elif field_name in write_only_fields:
            return {'read_only': False, 'write_only': True}
        else:
            # 检查是否为主键字段，如果是，且未明确指定为可写，则默认为只读
            model_pk_field = self.Meta.model._meta.pk_attr
            if model_pk_field == field_name and field_name not in write_only_fields:
                return {'read_only': True, 'write_only': False}
            else:
                return {'read_only': False, 'write_only': False}

    async def create(self, validated_data):
        """
        根据验证后的数据进行创建，
        """
        # TODO: 获取 validated_data 中的M2M字段

        # 检查是否创建方向字段
        ModelClass = self.Meta.model
        # ConfigurationError
        # 在执行create方法时出现错误，你可以重写create方法来解决这个异常
        try:
            instance = await ModelClass.create(**validated_data)
        except Exception:
            tb = traceback.format_exc()
            msg = (
                'There is an error in executing the `%s.create()` method. '
                'You can rewrite the `%s.create()` method to solve this exception.'
                '\nOriginal exception was:\n %s' % (ModelClass.__name__, self.__class__.__name__, tb)
            )
            raise ValueError(msg)
        # TODO: 对 instance 的M2M进行绑定
        return instance

    async def update(self, instance, validated_data):
        """
        一个完整的 Update() 是允许嵌套的 validated_data 值，在值中需要拆离 一对多及多对多的关系
        多对一的关系，例如:
            validated_data = {
                'name': 'new name',
                'book': {
                    'name': 'new book name',
                },
            }
        这个时候应该自动解析为并修改 book.name
        """

        ModelClass = self.Meta.model
        try:

            for field, value in validated_data.items():
                setattr(instance, field, value)
            await instance.save()
        except Exception:
            tb = traceback.format_exc()
            msg = (
                'There is an error in executing the `%s.update()` method. '
                'You can rewrite the `%s.update()` method to solve this exception.'
                '\nOriginal exception was:\n %s' % (ModelClass.__name__, self.__class__.__name__, tb)
            )
            raise ValueError(msg)
        # TODO: 对 instance 的M2M进行绑定
        return instance

    #

    def _get_model_relational_fields(self, model_fields):
        """
        Get basic fields, non-relational fields
        :param model_fields:
        :return:
        """
        return {
            field_name: field_class
            for field_name, field_class in model_fields.items()
            if isinstance(field_class, (tortoise_fields.relational.RelationalField, tortoise_fields.relational.ReverseRelation))
        }

    # ...

    def get_relationship_field_names(self, model_fields):
        """
        提取模型字段中所有关系字段的名称。
        :param model_fields: 模型字段字典
        :return: 包含所有关系字段名称的集合
        """
        relationship_field_types = (
            tortoise_fields.relational.ForeignKeyFieldInstance,
            tortoise_fields.relational.OneToOneFieldInstance,
            tortoise_fields.relational.ManyToManyFieldInstance,
            tortoise_fields.relational.ReverseRelation,
        )
        return {field_name for field_name, field_instance in model_fields.items() if isinstance(field_instance, relationship_field_types)}

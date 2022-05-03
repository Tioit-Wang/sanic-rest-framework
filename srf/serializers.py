"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/20 13:20
@DependencyLibrary:
@MainFunction：
@FileDoc:
    qr.py
    序列化器文件
"""
import copy
import inspect
from collections import OrderedDict
from typing import Any, Mapping

from tortoise import fields as tortoise_fields
from tortoise.queryset import ValuesQuery, ValuesListQuery

from srf.constant import LIST_SERIALIZER_KWARGS, ALL_FIELDS
from srf.converter import ModelConverter
from srf.exceptions import ValidationException
from srf.fields import (empty, SkipField, Field)
from srf.helpers import BindingDict
from srf.openapi import ObjectItem, ArrayItem
from srf.utils import run_awaitable, run_awaitable_val


def set_value(dictionary, keys, value):
    """
    set_value({'a': 1}, [], {'b': 2}) -> {'a': 1, 'b': 2}
    set_value({'a': 1}, ['x'], 2) -> {'a': 1, 'x': 2}
    set_value({'a': 1}, ['x', 'y'], 2) -> {'a': 1, 'x': {'y': 2}}
    """
    if not keys:
        dictionary.update(value)
        return

    for key in keys[:-1]:
        if key not in dictionary:
            dictionary[key] = {}
        dictionary = dictionary[key]

    dictionary[keys[-1]] = value


class BaseSerializer(Field):
    """序列化器
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
        kwargs.pop('many', None)
        super().__init__(**kwargs)

    def __new__(cls, *args, **kwargs):
        if kwargs.pop('many', False):
            return cls.many_init(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """初始化多值组件"""
        # allow_empty = kwargs.pop('allow_empty', None)
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
        }
        # if allow_empty is not None:
        #     list_kwargs['allow_empty'] = allow_empty
        list_kwargs.update({
            key: value for key, value in kwargs.items()
            if key in LIST_SERIALIZER_KWARGS
        })
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', ListSerializer)
        return list_serializer_class(*args, **list_kwargs)

    async def external_to_internal(self, data: Any) -> Any:
        """对数据进行序列化转换并返回"""
        raise NotImplementedError(
            '{cls}类的 .external_to_internal 方法必须重写'.format(cls=self.__class__.__name__, )
        )

    async def internal_to_external(self, data: Any) -> Any:
        """对数据进行反序列化转换并返回"""
        raise NotImplementedError(
            '{cls}类的 .external_to_internal 方法必须重写'.format(cls=self.__class__.__name__, )
        )

    async def validate(self, attr):
        return attr

    async def run_validation(self, data):
        value = await super(BaseSerializer, self).run_validation(data)
        value = self.validate(value)
        value = await run_awaitable_val(value)
        return value

    async def update(self, instance, validated_data):
        raise NotImplementedError('`update()` 必须实现.')

    async def create(self, validated_data):
        raise NotImplementedError('`create()` 必须实现.')

    async def save(self, **kwargs):
        assert hasattr(self, '_errors'), (
            '您必须先调用`.is_valid()`，然后再调用`.save()`。'
        )

        assert not self.errors, (
            '您不能在未通过效验的序列化器上调用`.save()`。'
        )

        # Guard against incorrect use of `serializer.save(commit=False)`
        assert 'commit' not in kwargs, (
            "`commit`不是`save()`方法的有效关键字参数。"
            "如果需要在提交数据库之前访问数据，则"
            "而是检查`serializer.validated_data`."
            "如果您还可以将其他关键字参数传递给`save()`，"
            "需要在保存的模型实例上设置额外的属性。"
            "例如：'serializer.save(owner = request.user)'。"
        )

        assert not hasattr(self, '_data'), (
            '访问`serializer.data`后，您不能调用`.save()`。'
            '如果需要在提交数据库之前访问数据，请访问'
            '`serializer.validated_data`'
        )

        validated_data = dict(list(self.validated_data.items()) + list(kwargs.items()))
        if self.instance is not None:
            validated_data, self.instance = await self.before_update(validated_data, self.instance)
            self.instance = await self.update(self.instance, validated_data)
            assert self.instance is not None, (
                '`update()` 没有返回对象实例。'
            )
        else:
            validated_data, self.instance = await self.before_create(validated_data, self.instance)
            self.instance = await self.create(validated_data)
            assert self.instance is not None, (
                '`create()` 没有返回对象实例。'
            )
        return self.instance

    async def before_update(self, validated_data, instance):
        return validated_data, instance

    async def before_create(self, validated_data, instance):
        return validated_data, instance

    async def is_valid(self, raise_exception=False):
        assert hasattr(self, 'initial_data'), (
            '无法调用`.is_valid()`，因为'
            '类实例化时没有传入`data =`关键字参数'
        )

        if not hasattr(self, '_validated_data'):
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
        """对外呈现的数据"""
        assert self.instance is not None, '调用 .data 必须先传入 instance= '
        if not hasattr(self, '_data'):
            self._data = await self.internal_to_external(self.instance)
        return self._data

    @property
    def errors(self):
        """对外呈现验证过程中出现的错误"""
        if not hasattr(self, '_errors'):
            msg = '你必须先执行 .is_valid() 方法才能调用 .errors'
            raise AssertionError(msg)
        return self._errors

    @property
    def validated_data(self):
        """对内使用的验证后的数据"""
        if not hasattr(self, '_validated_data'):
            msg = '你必须先执行 .is_valid() 方法才能调用 .validated_data'
            raise AssertionError(msg)
        return self._validated_data

    def _doc_request_schema(self):

        title = f'{self.__class__.__module__}.{self.__class__.__name__}'
        _object = ObjectItem(title)
        for field_name, field in self.fields.items():
            if field.read_only:
                continue
            _object.add(field_name, field._doc_properties(), field.required)
        return _object.to_dict()

    def _doc_response_schema(self):

        title = f'{self.__class__.__module__}.{self.__class__.__name__}'
        _object = ObjectItem(title)
        for field_name, field in self.fields.items():
            if field.write_only:
                continue
            _object.add(field_name, field._doc_properties(), field.required)
        return _object.to_dict()


class SerializerMetaclass(type):

    @classmethod
    def _get_declared_fields(cls, bases, attrs):
        fields = [(field_name, attrs.pop(field_name))
                  for field_name, obj in list(attrs.items())
                  if isinstance(obj, Field)]
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
    default_error_messages = {
        'invalid': '无效数据。应该是字典，但是得到了{datatype}'
    }

    @property
    def fields(self):
        """
        单个格式为 {field_name: field_instance}.
        fields 是动态加载的 避免在导入时出现意想不到的错误
        """
        # like drf
        fields = BindingDict(self)
        for key, value in self.get_fields().items():
            fields[key] = value
        return fields

    @property
    def _writable_fields(self):
        for field in self.fields.values():
            if not field.read_only:
                yield field

    @property
    def _readable_fields(self):
        for field in self.fields.values():
            if not field.write_only:
                yield field

    def get_fields(self) -> dict:
        """
        得到所有fields
        :return:
        """
        return copy.deepcopy(self._declared_fields)

    # 序列化
    async def internal_to_external(self, data: Any) -> Any:
        """
        内转外
        :param data:
        :return:

        """
        res = OrderedDict()
        fields = self._readable_fields
        for field in fields:
            method = getattr(self, f'output_{field.field_name}', None)
            try:
                value = await field.get_internal_value(data)
            except SkipField:
                continue
            if value is not None:
                value = await field.internal_to_external(value)
            if method:
                value = await run_awaitable(method, value, data)
            res[field.field_name] = value
        return res

    #  反序列化
    async def external_to_internal(self, data: Any) -> Any:
        """
        外转内
        :param data:
        :return:
        """
        res = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields
        for field in fields:
            validate_method = getattr(self, f'validate_{field.field_name}', None)
            try:
                primitive_value = field.get_external_value(data)
                validated_value = await field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = await run_awaitable(validate_method, validated_value, data)
            except ValidationException as exc:
                errors[field.field_name] = exc.error_detail
            except SkipField:
                pass
            else:
                set_value(res, field.source_attrs, validated_value)
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


class ListSerializer(BaseSerializer):
    child = None
    many = True

    default_error_messages = {
        'not_a_list': '预期项目列表，但类型为“ {input_type}”。',
        'null': '此列表不能为空。'
    }

    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        # self.allow_empty = kwargs.pop('allow_empty', True)
        assert self.child is not None, '`child` 是必填参数。'
        assert not inspect.isclass(self.child), '`child` 尚未实例化。'
        super().__init__(*args, **kwargs)
        self.child.bind(field_name='', parent=self)

    async def get_internal_value(self, instance: Any) -> Any:
        """目的得到值"""
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
        内转外
        :param data:
        :return:
        """
        if not inspect.isawaitable(data):
            iterable = data
        elif isinstance(data, (ValuesQuery, ValuesListQuery)):
            iterable = await data
        else:
            iterable = await data.all()

        return [
            await self.child.internal_to_external(item) for item in iterable
        ]

    async def external_to_internal(self, data: Any) -> Any:
        """
        外转内
        :param data:
        :return:
        """
        if not isinstance(data, list):
            raise self.raise_error('not_a_list', input_type=type(data).__name__)

        if not self.allow_null and len(data) == 0:
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
        我们覆盖默认的`run_validation`，因为验证由验证者执行，
        而.validate（）方法应使用“non_fields_error”键被强制为错误字典。
        """
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = await self.external_to_internal(data)
        self.run_validators(value)
        value = await self.validate(value)
        return value

    async def update(self, instance, validated_data):
        raise NotImplementedError(
            '当 many=True 时，有些序列化器不支持更新操作，'
            '所以在必须使用时请继承ListSerializer并覆盖'
            '`.update()`，不提供默认实现方式')

    async def create(self, validated_data):
        return [
            await self.child.create(attrs) for attrs in validated_data
        ]

    async def save(self, **kwargs):
        """
        保存实例
        """
        # 防止错误使用`serializer.save(commit = False)`
        assert 'commit' not in kwargs, (
            "`commit`不是`save()`方法的有效关键字参数。"
            "如果需要在提交数据库之前访问数据，则"
            "而是检查`serializer.validated_data`."
            "如果您还可以将其他关键字参数传递给`save()`，"
            "需要在保存的模型实例上设置额外的属性。"
            "例如：'serializer.save(owner = request.user)'。"
        )

        validated_data = [
            {**attrs, **kwargs}
            for attrs in self.validated_data
        ]

        if self.instance is None:
            self.instance = await self.create(validated_data)
            assert self.instance is not None, (
                '`create()` 没有返回对象实例。'
            )
        else:
            self.instance = await self.update(self.instance, validated_data)
            assert self.instance is not None, (
                '`update()` 没有返回对象实例。'
            )

        return self.instance

    @property
    def _doc_request_schema(self):
        # sourcery skip: inline-immediately-returned-variable
        title = f'{self.__class__.__module__}.{self.__class__.__name__}'
        array_item = ArrayItem(title, self.child._doc_request_schema())
        return array_item

    def _doc_response_schema(self):
        title = f'{self.__class__.__module__}.{self.__class__.__name__}'
        array_item = ArrayItem(title, self.child._doc_response_schema())
        return array_item


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
        """
        单个格式为 {field_name: field_instance}.
        fields 是动态加载的 避免在导入时出现意想不到的错误
        """
        assert hasattr(self, 'Meta'), (
            '{serializer_class} 类没有 "Meta" 属性'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            '{serializer_class} 类没有 "Meta.model" 属性'.format(
                serializer_class=self.__class__.__name__
            )
        )
        if self.Meta.model._meta.abstract:
            raise ValueError('不能将ModelSerializer与抽象模型一起使用。')

        declared_fields = copy.deepcopy(self._declared_fields)
        model = getattr(self.Meta, 'model')
        depth = getattr(self.Meta, 'depth', 10)
        if depth is not None:
            assert depth >= 0, "'depth' may not be negative."
            assert depth <= 10, "'depth' may not be greater than 10."

        converter = ModelConverter(ModelSerializer)
        model_original_fields = model._meta.fields_map
        model_clean_fields = self._clean_model_field(model_original_fields)
        effective_field = self.get_effective_field(model_clean_fields)
        serializer_fields = BindingDict(self)

        for field_name, field_class in effective_field.items():
            current_field_class = converter.convert(self, field_class, **self.get_field_kws_by_meta(field_name))
            serializer_fields[field_name] = current_field_class
        serializer_fields.update(declared_fields)
        return serializer_fields

    def get_effective_field(self, model_fields) -> dict:
        """
        得到有效的字段
        :param model_fields: 模型字段
        :return:
        """
        meta_fields = getattr(self.Meta, 'fields', None)
        meta_exclude = getattr(self.Meta, 'exclude', None)
        if meta_exclude and meta_fields:
            raise ValueError(f'class ”{self.__class__.__name__}“ ’Meta.fields‘ 和 ’Meta.exclude‘ 不可以共存 ')

        if meta_exclude is not None:
            return {k: v for k, v in model_fields.items() if k not in meta_exclude}
        elif meta_fields is None or meta_fields is ALL_FIELDS:
            return model_fields
        else:
            return {k: v for k, v in model_fields.items() if k in meta_fields}

    def get_field_kws_by_meta(self, field_name):
        """
        判断当前字段是否在Meat内设置了只读或只写
        :param field_name:
        :return:
        """
        read_only_fields = getattr(self.Meta, 'read_only_fields', [])
        write_only_fields = getattr(self.Meta, 'write_only_fields', [])
        if field_name in read_only_fields and field_name in write_only_fields:
            raise ValueError(
                f'字段 {field_name} 不可用同时存在于类 ”{self.__class__.__name__}“ 的 ’Meta.read_only_fields‘ 和 ’Meta.write_only_fields‘ 属性中')

        if field_name in read_only_fields:
            return {'read_only': True, 'write_only': False}
        elif field_name in write_only_fields:
            return {'read_only': False, 'write_only': True}
        else:
            return {'read_only': False, 'write_only': False}

    def _clean_model_field(self, model_original_fields):
        """
        清除不需要的字段如 fk_id
        :param model_original_fields:
        :return:
        """
        clean_field_names = []
        field_dict = {}
        fields_map = copy.deepcopy(model_original_fields)
        basis_fields = self._get_model_basis_fields(fields_map)

        for field_name, field_class in basis_fields.items():
            if isinstance(field_class, (
                    tortoise_fields.relational.ForeignKeyFieldInstance,
                    tortoise_fields.relational.OneToOneFieldInstance)):
                clean_field_names.append(field_class.source_field)
            field_dict[field_name] = field_class

        for clean_field_name in clean_field_names:
            if clean_field_name in field_dict:
                field_dict.pop(clean_field_name)
        return field_dict

    async def create(self, validated_data):
        # sourcery skip: dict-comprehension, merge-nested-ifs
        """
        根据验证后的数据进行创建，
        """
        # raise_errors_on_nested_writes('create', self, validated_data)

        ModelClass = self.Meta.model
        ModelClassMeta = ModelClass._meta
        many_to_many = {}

        for m2m_field in ModelClassMeta.m2m_fields:
            if m2m_field in self.fields:
                if m2m_field in validated_data:
                    many_to_many[m2m_field] = validated_data.pop(m2m_field)
        try:
            instance = ModelClass()
            for attr, value in validated_data.items():
                if attr not in many_to_many:
                    setattr(instance, attr, value)
            await instance.save()
        except TypeError as exc:
            raise exc
        if many_to_many:
            for field_name, values in many_to_many.items():
                field = getattr(instance, field_name)
                for value in values:
                    await field.add(value)
        return instance

    async def update(self, instance, validated_data):
        """更新"""
        ModelClass = self.Meta.model
        ModelClassMeta = ModelClass._meta

        m2m_fields = []
        for attr, value in validated_data.items():
            if attr in ModelClassMeta.m2m_fields:
                m2m_fields.append((attr, value))
            else:
                setattr(instance, attr, value)
        await instance.save()
        for attr, values in m2m_fields:
            field = getattr(instance, attr)
            for value in values:
                value, _ = await field.remote_model.get_or_create(**value)
                await field.add(value)
        return instance

    def check_relationship(self):
        """检查关系字段 目前不能为关系字段提供自动转换功能"""

    #
    def _get_model_basis_fields(self, model_fields):
        """
        得到基础字段，非关系字段
        :param model:
        :return:
        """
        return {field_name: field_class for field_name, field_class in model_fields.items() if
                not isinstance(field_class, tortoise_fields.relational.RelationalField)}
    #
    # def _get_model_M2M_fields(self, model_fields):
    #     """
    #     得到多对多字段
    #     :param model:
    #     :return:
    #     """
    #     return {field_name: field_class for field_name, field_class in model_fields.items() if isinstance(field_class, tortoise_fields.relational.ManyToManyFieldInstance)}
    #
    # def _get_model_O2O_fields(self, model_fields):
    #     """得到一对一字段"""
    #     return {field_name: field_class for field_name, field_class in model_fields.items() if
    #             isinstance(field_class, (tortoise_fields.relational.BackwardOneToOneRelation, tortoise_fields.relational.OneToOneFieldInstance))}
    #
    # def _get_model_M2O_fields(self, model_fields):
    #     """
    #     得到多对一字段
    #     :param model:
    #     :return:
    #     """
    #     return {field_name: field_class for field_name, field_class in model_fields.items() if
    #             isinstance(field_class, tortoise_fields.relational.ForeignKeyFieldInstance)}
    #
    # def _get_model_O2M_fields(self, model_fields):
    #     """
    #     得到一对多字段
    #     :param model:
    #     :return:
    #     """
    #     return {field_name: field_class for field_name, field_class in model_fields.items() if
    #             isinstance(field_class, tortoise_fields.relational.BackwardFKRelation)}

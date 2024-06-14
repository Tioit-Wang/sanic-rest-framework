"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/5 9:44
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    converter.py
    转换器
@ChangeHistory:
    datetime action why
    example:
    2021/3/5 9:44 change 'Fix bug'EnumChoiceField
"""

import copy

from tortoise import fields

from rest_framework.constant import DEFAULT_NESTED_DEPTH
from rest_framework.fields import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    EnumChoiceField,
    FloatField,
    IntegerField,
    ManyRelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)


def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func

    return _inner


class ConverterException(Exception):
    pass


class ModelConverterBase(object):
    def __init__(
        self,
        nested_field_class,
        converters=None,
    ):
        self.nested_field_class = nested_field_class
        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters


class ModelConverter(ModelConverterBase):
    """模型转换器"""

    def convert(self, serializer, model_field, **field_kwargs):
        model = serializer.Meta.model
        read_only = field_kwargs.get('read_only', False)
        write_only = field_kwargs.get('write_only', False)
        default = model_field.default

        kwargs = {
            'read_only': read_only,
            'write_only': write_only,
            'allow_null': model_field.null,
            'description': model_field.description,
        }
        required = not model_field.null
        if read_only:
            required = False

        type_name = model_field.__class__.__name__
        if isinstance(model_field, fields.relational.RelationalField):
            nested_depth = serializer.Meta.depth if hasattr(serializer.Meta, 'depth') else DEFAULT_NESTED_DEPTH

            # kwargs['allow_empty'] = model_field.null
            kwargs['nested_depth'] = nested_depth
        elif default is not None:
            kwargs['default'] = default() if callable(default) else default
            required = False
        kwargs['required'] = required
        converter = self.converters[type_name]
        kwargs.update(field_kwargs)

        return converter(model, model_field, **kwargs)

    @converts('CharField')
    def convert_charfield(self, model, model_field, *field_args, **field_kws):
        max_length = model_field.max_length
        if max_length is not None:
            field_kws['max_length'] = max_length
        return CharField(*field_args, **field_kws)

    @converts('UUIDField', 'JSONField', 'TextField')
    def convert_textfield(self, model, model_field, *field_args, **field_kws):
        return CharField(*field_args, **field_kws)

    @converts('IntField', 'BigIntField', 'SmallIntField')
    def convert_integerfield(self, model, model_field, *field_args, **field_kws):
        return IntegerField(*field_args, **field_kws)

    @converts('BooleanField')
    def convert_booleanfield(self, model, model_field, *field_args, **field_kws):
        return BooleanField(*field_args, **field_kws)

    @converts('CharEnumFieldInstance')
    def convert_charenumfield(self, model, model_field, *field_args, **field_kws):
        field_kws['enum_type'] = model_field.enum_type
        field_kws['value_type'] = str
        return EnumChoiceField(*field_args, **field_kws)

    @converts('IntEnumFieldInstance')
    def convert_intenumfield(self, model, model_field, *field_args, **field_kws):
        field_kws['enum_type'] = model_field.enum_type
        field_kws['value_type'] = int
        return EnumChoiceField(*field_args, **field_kws)

    @converts('DecimalField')
    def convert_decimalfield(self, model, model_field, *field_args, **field_kws):
        field_kws['max_digits'] = model_field.max_digits
        field_kws['decimal_places'] = model_field.decimal_places
        return DecimalField(*field_args, **field_kws)

    @converts('DatetimeField')
    def convert_datetimefield(self, model, model_field, *field_args, **field_kws):
        # 如果DatetimeField字段包含，auto_now_add或auto_now在未明确指定未可些的情况下应该只读
        return DateTimeField(*field_args, **field_kws)

    @converts('DateField')
    def convert_datefield(self, model, model_field, *field_args, **field_kws):
        return DateField(*field_args, **field_kws)

    @converts('FloatField')
    def convert_floatfield(self, model, model_field, *field_args, **field_kws):
        return FloatField(*field_args, **field_kws)

    @converts('ManyToManyFieldInstance', 'ManyToManyRelation')
    def convert_manytomany(self, model, model_field, *field_args, **field_kws):
        """多对多"""
        nested_depth = field_kws.pop('nested_depth', DEFAULT_NESTED_DEPTH)

        class NestedSerializer(self.nested_field_class):
            class Meta:
                model = model_field.related_model
                depth = nested_depth - 1
                fields = '__all__'

        field_kws['required'] = False
        return NestedSerializer(many=True, **field_kws)

    @converts(
        'BackwardFKRelation',
    )
    def convert_backwardfkrelation(self, model, model_field, *field_args, **field_kws):
        """反向一对多"""
        field_kws.pop('nested_depth', DEFAULT_NESTED_DEPTH)
        field_kws['read_only'] = True
        field_kws['required'] = False

        child_relation_kws = copy.deepcopy(field_kws)
        child_relation_kws['queryset'] = model_field.related_model
        field_kws['queryset'] = model
        field_kws['read_only'] = True

        return ManyRelatedField(child_relation=SlugRelatedField(slug_field='pk', **child_relation_kws), **field_kws)

    @converts('ForeignKeyFieldInstance')
    def convert_foreignkeyfieldinstance(self, model, model_field, *field_args, **field_kws):
        """正向多对一"""
        field_kws.pop('nested_depth', DEFAULT_NESTED_DEPTH)
        field_kws['queryset'] = model_field.related_model
        return PrimaryKeyRelatedField(**field_kws)

    @converts('OneToOneFieldInstance')
    def convert_onetoonefieldinstance(self, model, model_field, *field_args, **field_kws):
        """正向 一对一"""
        nested_depth = field_kws.pop('nested_depth', DEFAULT_NESTED_DEPTH)

        class NestedSerializer(self.nested_field_class):
            class Meta:
                model = model_field.related_model
                depth = nested_depth - 1
                fields = '__all__'

        return NestedSerializer(**field_kws)

    @converts('BackwardOneToOneRelation')
    def convert_backwardonetoonerelation(self, model, model_field, *field_args, **field_kws):
        """反向一对一"""
        nested_depth = field_kws.pop('nested_depth', DEFAULT_NESTED_DEPTH)

        class NestedSerializer(self.nested_field_class):
            class Meta:
                model = model_field.related_model
                depth = nested_depth - 1
                fields = '__all__'

        return NestedSerializer(**field_kws)

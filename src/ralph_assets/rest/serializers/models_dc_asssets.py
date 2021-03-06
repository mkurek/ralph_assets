# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from rest_framework import serializers

from ralph_assets.models_dc_assets import (
    DataCenter,
    Rack,
    RackAccessory,
    RackOrientation,
)
from ralph_assets.models import Asset


TYPE_EMPTY = 'empty'
TYPE_ACCESSORY = 'accessory'
TYPE_ASSET = 'asset'
TYPE_PDU = 'pdu'


class CoreDeviceMixin(object):
    def get_core_url(self, obj):
        """
        Return the URL to device in core.
        """
        device_core_id = obj.device_info.ralph_device_id
        return reverse('search', kwargs={
            'details': 'info', 'device': device_core_id
        })


class RelatedAssetSerializer(CoreDeviceMixin, serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    slot_no = serializers.CharField(source='device_info.slot_no')
    url = serializers.CharField(source='url')
    core_url = serializers.SerializerMethodField('get_core_url')

    class Meta:
        model = Asset
        fields = ('id', 'model', 'barcode', 'sn', 'slot_no', 'url', 'core_url')


class AssetSerializer(CoreDeviceMixin, serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    category = serializers.CharField(source='model.category.name')
    height = serializers.FloatField(source='model.height_of_device')
    layout = serializers.CharField(source='model.get_layout_class')
    url = serializers.CharField(source='url')
    core_url = serializers.SerializerMethodField('get_core_url')
    position = serializers.IntegerField(source='device_info.position')
    children = RelatedAssetSerializer(source='get_related_assets')
    _type = serializers.SerializerMethodField('get_type')

    def get_type(self, obj):
        return TYPE_ASSET

    class Meta:
        model = Asset
        fields = (
            'id', 'model', 'category', 'height', 'layout', 'barcode', 'sn',
            'url', 'core_url', 'position', 'children', '_type',
        )


class RackAccessorySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='accessory.name')
    _type = serializers.SerializerMethodField('get_type')

    def get_type(self, obj):
        return TYPE_ACCESSORY

    class Meta:
        model = RackAccessory
        fields = ('position', 'remarks', 'type', '_type')


class PDUSerializer(serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    orientation = serializers.IntegerField(source='get_orientation_desc')
    url = serializers.CharField(source='url')

    def get_type(self, obj):
        return TYPE_PDU

    class Meta:
        model = Asset
        fields = ('model', 'sn', 'orientation', 'url')


class RackSerializer(serializers.ModelSerializer):
    free_u = serializers.IntegerField(source='get_free_u', read_only=True)
    orientation = serializers.CharField(source='get_orientation_desc')

    class Meta:
        model = Rack
        fields = (
            'id', 'name', 'data_center', 'server_room', 'max_u_height',
            'visualization_col', 'visualization_row', 'free_u', 'description',
            'orientation',
        )

    def update(self):
        orientation = self.data['orientation']
        self.object.orientation = RackOrientation.id_from_name(orientation)
        return self.save(**self.data)


class DCSerializer(serializers.ModelSerializer):
    rack_set = RackSerializer()

    class Meta:
        model = DataCenter
        fields = ('id', 'name', 'visualization_cols_num',
                  'visualization_rows_num', 'rack_set')
        depth = 1

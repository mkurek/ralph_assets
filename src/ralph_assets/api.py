#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from django.conf import settings
from django.contrib.auth.models import User
from tastypie import fields
from tastypie.authentication import ApiKeyAuthentication
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from tastypie.throttle import CacheThrottle

from ralph.discovery.models import Device
from ralph.urls import LATEST_API
from ralph_assets.models import (
    Asset,
    AssetManufacturer,
    AssetModel,
    AssetOwner,
    AssetSource,
    AssetStatus,
    AssetType,
    DeviceInfo,
    Licence,
    LicenceType,
    Service,
    SoftwareCategory,
    Warehouse,
)

THROTTLE_AT = settings.API_THROTTLING['throttle_at']
TIMEFRAME = settings.API_THROTTLING['timeframe']
EXPIRATION = settings.API_THROTTLING['expiration']
SAVE_PRIORITY = 10


class ChoicesField(fields.ApiField):
    """A Field to convert lck.django.choices.Choices field int representation
    to human readable version"""

    def __init__(self, choices_class, field_name=None, *args, **kwargs):
        self.choices_class = choices_class
        self.field_name = field_name
        super(ChoicesField, self).__init__(*args, **kwargs)

    def dehydrate(self, bundle, **kwargs):
        field_name = self.field_name or self.instance_name
        field_value = getattr(bundle.obj, field_name)
        if field_value:
            return self.choices_class.from_id(field_value).name
        else:
            return None


class LinkedField(fields.ApiField):
    """A field representing an linked resource object"""

    def __init__(self, field_name, resource_name, *args, **kwargs):
        self.field_name = field_name
        self.resource_name = resource_name
        super(LinkedField, self).__init__(*args, **kwargs)

    def dehydrate(self, bundle, **kwargs):
        obj = getattr(bundle.obj, self.field_name)
        if obj:
            return LATEST_API.canonical_resource_for(
                self.resource_name
            ).get_resource_uri(obj)
        else:
            return None


class AssetsField(fields.RelatedField):
    """A field representing an assigned assets to user.
    Filtered by Asset.owner field"""

    is_m2m = True

    def __init__(self, *args, **kwargs):
        args = (
            'ralph_assets.api.AssetsResource',
            self.get_attribute_name(),
        )
        super(AssetsField, self).__init__(*args, **kwargs)

    def dehydrate(self, bundle, **kwargs):
        assets = Asset.objects.filter(owner=bundle.obj)
        return [
            self.dehydrate_related(bundle, self.get_related_resource(asset))
            for asset in assets
        ]

    def get_attribute_name(self):
        return 'assets'


class AssetManufacturerResource(ModelResource):
    class Meta:
        queryset = AssetManufacturer.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class AssetModelResource(ModelResource):
    category = fields.CharField(attribute='category', null=True)
    manufacturer = fields.CharField(attribute='manufacturer', null=True)

    class Meta:
        queryset = AssetModel.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )
        filtering = {
            'name': ALL,
        }


class AssetOwnerResource(ModelResource):
    class Meta:
        queryset = AssetOwner.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class LicenceTypeResource(ModelResource):
    class Meta:
        queryset = LicenceType.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class ServiceResource(ModelResource):
    class Meta:
        queryset = Service.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class SoftwareCategoryResource(ModelResource):
    class Meta:
        queryset = SoftwareCategory.objects.all()
        authentication = ApiKeyAuthentication()
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class UserResource(ModelResource):
    user_username = fields.CharField(attribute="username")

    class Meta:
        queryset = User.objects.all()
        excludes = ['username', ]
        list_allowed_methods = ['get']
        filtering = {
            'user_username': ALL,
        }


class WarehouseResource(ModelResource):
    class Meta:
        queryset = Warehouse.objects.all()
        list_allowed_methods = ['get']
        filtering = {
            'user_username': ALL,
        }


class LicenceResource(ModelResource):
    asset_type = ChoicesField(AssetType)
    licence_type = fields.ForeignKey(LicenceTypeResource, 'licence_type')
    manufacturer = fields.ForeignKey(
        AssetManufacturerResource, 'manufacturer', null=True,
    )
    property_of = fields.ForeignKey(
        AssetOwnerResource, 'property_of', null=True,
    )
    software_category = fields.ForeignKey(
        SoftwareCategoryResource, 'software_category', full=True,
    )

    class Meta:
        queryset = Licence.objects.all()
        authentication = ApiKeyAuthentication()
        filtering = {
            'number_bought': ALL,
            'sn': ALL,
            'niw': ALL,
            'invoice_date': ALL,
            'valid_thru': ALL,
            'order_no': ALL,
            'price': ALL,
            'accounting_id': ALL,
            'asset_type': ALL,
            'provider': ALL,
            'invoice_no': ALL,
            'manufacturer': ALL_WITH_RELATIONS,
            'licence_type': ALL_WITH_RELATIONS,
            'property_of': ALL_WITH_RELATIONS,
            'software_category': ALL_WITH_RELATIONS,
        }
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )


class SimpleDeviceResource(ModelResource):
    class Meta:
        queryset = Device.objects.all()
        fields = ['id', 'barcode', 'sn', 'name']
        filtering = {
            'id': ALL,
        }


class DeviceInfoResource(ModelResource):
    ralph_device = fields.ForeignKey(
        SimpleDeviceResource, 'ralph_device', full=True,
    )

    class Meta:
        queryset = DeviceInfo.objects.all()
        list_allowed_methods = ['get']
        filtering = {
            'ralph_device': ALL_WITH_RELATIONS,
        }
        excludes = ["cache_version", "created", "deleted", "modified"]


class AssetsResource(ModelResource):
    asset_type = ChoicesField(AssetType, 'type')
    licences = fields.ToManyField(LicenceResource, 'licences', full=True)
    manufacturer = fields.ForeignKey(
        AssetManufacturerResource, 'manufacturer', null=True,
    )
    model = fields.ForeignKey(AssetModelResource, 'model', full=True)
    owner = fields.ForeignKey(UserResource, 'owner', null=True)
    service_name = fields.ForeignKey(
        ServiceResource, 'service_name', null=True,
    )
    source = ChoicesField(AssetSource)
    status = ChoicesField(AssetStatus)
    user = fields.ForeignKey(UserResource, 'user', null=True)
    warehouse = fields.ForeignKey(WarehouseResource, 'warehouse')
    linked_device = LinkedField(
        field_name='linked_device', resource_name='dev', null=True,
    )
    venture = LinkedField(
        field_name='venture', resource_name='venture', null=True,
    )
    service = fields.ForeignKey(
        'ralph.discovery.api.ServiceCatalogResource',
        'service',
        null=True,
    )
    device_environment = fields.ForeignKey(
        'ralph.discovery.api.DeviceEnvironmentResource',
        'device_environment',
        null=True,
    )
    device_info = fields.ForeignKey(
        DeviceInfoResource, 'device_info', null=True, full=True,
    )

    class Meta:
        queryset = Asset.objects.all()
        authentication = ApiKeyAuthentication()
        filtering = {
            'barcode': ALL,
            'delivery_date': ALL,
            'deprecation_rate': ALL,
            'device_environment': ALL_WITH_RELATIONS,
            'device_info': ALL_WITH_RELATIONS,
            'force_deprecation': ALL,
            'hostname': ALL,
            'id': ALL,
            'invoice_date': ALL,
            'invoice_no': ALL,
            'location': ALL,
            'model': ALL_WITH_RELATIONS,
            'niw': ALL,
            'order_no': ALL,
            'owner': ALL_WITH_RELATIONS,
            'price': ALL,
            'production_use_date': ALL,
            'production_year': ALL,
            'provider': ALL,
            'provider_order_date': ALL,
            'remarks': ALL,
            'request_date': ALL,
            'service': ALL_WITH_RELATIONS,
            'service_name': ALL_WITH_RELATIONS,
            'slots': ALL,
            'sn': ALL,
            'source': ALL,
            'status': ALL,
            'support_period': ALL,
            'support_price': ALL,
            'support_type': ALL,
            'support_void_reporting': ALL,
            'type': ALL,
            'user': ALL_WITH_RELATIONS,
            'warehouse': ALL_WITH_RELATIONS,
        }
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )

    def get_object_list(self, request):
        # Workaround for RegionMiddleware
        # Resource.queryset is evaluated at module load
        return Asset.objects.all()


class UserAssignmentsResource(ModelResource):
    is_m2m = True
    licences = fields.ToManyField(
        LicenceResource,
        'licence_set',
        full=True,
    )
    assets = AssetsField(AssetsResource, full=True)
    # Workaround to filter by username. Username is reserved to authentication
    # api user.
    user_username = fields.CharField(attribute="username")

    class Meta:
        queryset = User.objects.all()
        resource_name = 'user_assignments'
        authentication = ApiKeyAuthentication()
        excludes = [
            'username', 'password', 'date_joined', 'is_staff', 'is_superuser',
        ]
        filtering = {
            'user_username': ALL,
        }
        list_allowed_methods = ['get']
        throttle = CacheThrottle(
            throttle_at=THROTTLE_AT,
            timeframe=TIMEFRAME,
            expiration=EXPIRATION,
        )

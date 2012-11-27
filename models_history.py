#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
from django.db import models as db
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from ralph.assets.history import field_changes

from ralph.assets.models_assets import Asset, DeviceInfo, PartInfo, OfficeInfo


class AssetHistoryChange(db.Model):
    """Represent a single change of a device or one of its components."""

    date = db.DateTimeField(verbose_name=_("date"), default=datetime.now)
    asset = db.ForeignKey(
        'Asset', verbose_name=_("asset"), null=True,
        blank=True, default=None, on_delete=db.SET_NULL
    )
    device_info = db.ForeignKey(
        'DeviceInfo', verbose_name=_("device_info"), null=True,
        blank=True, default=None, on_delete=db.SET_NULL
    )
    part_info = db.ForeignKey(
        'PartInfo', verbose_name=_("part_info"), null=True,
        blank=True, default=None, on_delete=db.SET_NULL
    )
    office_info = db.ForeignKey(
        'OfficeInfo', verbose_name=_("office_info"), null=True,
        blank=True, default=None, on_delete=db.SET_NULL
    )
    user = db.ForeignKey(
        'auth.User', verbose_name=_("user"), null=True,
        blank=True, default=None, on_delete=db.SET_NULL
    )
    field_name = db.CharField(max_length=64, default='')
    old_value = db.CharField(max_length=255, default='')
    new_value = db.CharField(max_length=255, default='')
    comment = db.TextField(null=True)

    class Meta:
        verbose_name = _("history change")
        verbose_name_plural = _("history changes")

    def __unicode__(self):
        return "'{}'.{} = '{}' -> '{}' by {} on {} ({})".format(
            self.asset, self.field_name, self.old_value, self.new_value,
            self.user, self.date, self.id
        )


@receiver(post_save, sender=Asset, dispatch_uid='ralph.history_assets')
def asset_post_save(sender, instance, raw, using, **kwargs):
    """A hook for creating ``HistoryChange`` entries when a asset changes."""
    for field, orig, new in field_changes(instance, ignore={}):
        update_releated_fields(instance)
        AssetHistoryChange(
            asset=instance,
            field_name=field,
            old_value=unicode(orig),
            new_value=unicode(new),
            user=instance.saving_user,
            comment=instance.save_comment,
        ).save()


@receiver(post_save, sender=DeviceInfo, dispatch_uid='ralph.history_assets')
def device_info_post_save(sender, instance, raw, using, **kwargs):
    """
    A hook for creating ``HistoryChange`` entries when a DeviceInfo changes.
    """
    for field, orig, new in field_changes(instance, ignore={}):
        AssetHistoryChange(
            device_info=instance,
            field_name=field,
            old_value=unicode(orig),
            new_value=unicode(new),
            user=instance.saving_user,
            comment=instance.save_comment,
        ).save()


@receiver(post_save, sender=PartInfo, dispatch_uid='ralph.history_assets')
def part_info_post_save(sender, instance, raw, using, **kwargs):
    """
    A hook for creating ``HistoryChange`` entries when a PartInfo changes.
    """
    for field, orig, new in field_changes(instance, ignore={}):
        AssetHistoryChange(
            part_info=instance,
            field_name=field,
            old_value=unicode(orig),
            new_value=unicode(new),
            user=instance.saving_user,
            comment=instance.save_comment,
        ).save()


@receiver(post_save, sender=OfficeInfo, dispatch_uid='ralph.history_assets')
def office_info_post_save(sender, instance, raw, using, **kwargs):
    """A hook for creating ``HistoryChange`` entries when a Office changes."""
    for field, orig, new in field_changes(instance, ignore={}):
        AssetHistoryChange(
            office_info=instance,
            field_name=field,
            old_value=unicode(orig),
            new_value=unicode(new),
            user=instance.saving_user,
            comment=instance.save_comment,
        ).save()


def update_releated_fields(instance):
    if instance.device_info:
        try:
            dev_info = AssetHistoryChange.objects.all().filter(
                device_info_id=instance.device_info.id
            )
            for item in dev_info:
                item.asset_id = instance.id
                item.save()
        except AssetHistoryChange.DoesNotExist:
            pass
    if instance.office_info:
        try:
            office_info = AssetHistoryChange.objects.all().filter(
                office_info_id=instance.office_info.id
            )
            for item in office_info:
                item.asset_id = instance.id
                item.save()
        except AssetHistoryChange.DoesNotExist:
            pass
    if instance.part_info:
        try:
            part_info = AssetHistoryChange.objects.all().filter(
                part_info_id=instance.part_info.id
            )
            for item in part_info:
                item.asset_id = instance.id
                item.save()
        except AssetHistoryChange.DoesNotExist:
            pass
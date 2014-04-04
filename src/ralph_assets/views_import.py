# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.contrib.formtools.wizard.views import SessionWizardView
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.fields import CharField, DecimalField, TextField
from django.db.models.fields.related import RelatedField
from django.shortcuts import render
from django.template.defaultfilters import slugify
from lck.django.common.models import Named

from ralph_assets.forms_import import (
    ColumnChoiceField,
    get_model_by_name,
    get_amendment_model,
)
from ralph_assets.models_assets import (
    MODE2ASSET_TYPE,
    CreatableFromString,
    Sluggy,
)
from ralph_assets.models_util import add_problem, ProblemSeverity
from ralph_assets.views import AssetsBase
from ralph_assets.models import Asset


class XlsUploadView(SessionWizardView, AssetsBase):
    """The wizard view for xls/csv upload."""

    template_name = 'assets/xls_upload_wizard.html'
    file_storage = FileSystemStorage(location=settings.FILE_UPLOAD_TEMP_DIR)
    sidebar_selected = 'xls upload'
    mainmenu_selected = 'dc'

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        form = super(XlsUploadView, self).get_form(step, data, files)
        if step == 'column_choice':
            names_per_sheet, update_per_sheet, add_per_sheet =\
                self.get_cleaned_data_for_step('upload')['file']
            model = self.get_cleaned_data_for_step('upload')['model']
            form.model_reflected = model
            form.update = any(update_per_sheet.values())
            for name_list in names_per_sheet.values():
                for name in name_list:
                    form.fields[slugify(name)] = ColumnChoiceField(
                        model=model,
                        mode=self.mode,
                        label=name,
                    )
        elif step == 'confirm':
            names_per_sheet, _, _ =\
                self.get_cleaned_data_for_step('upload')['file']
            mappings = {}
            all_names = set(sum((
                [slugify(n) for n in name_list]
                for name_list in names_per_sheet.values()
            ), []))
            for k, v in self.get_cleaned_data_for_step(
                'column_choice'
            ).items():
                if k in all_names and v != '':
                    mappings[k] = v
            self.storage.data['mappings'] = mappings
        return form

    def get_context_data(self, form, **kwargs):
        data = super(XlsUploadView, self).get_context_data(form, **kwargs)
        if self.steps.current == 'confirm':
            names_per_sheet, update_per_sheet, add_per_sheet =\
                self.get_cleaned_data_for_step('upload')['file']
            mappings = self.storage.data['mappings']
            all_columns = list(mappings.values())
            all_column_names = all_columns
            data_dicts = {}
            for sheet_name, sheet_data in update_per_sheet.items():
                for asset_id, asset_data in sheet_data.items():
                    data_dicts.setdefault(asset_id, {})
                    for key, value in asset_data.items():
                        data_dicts[asset_id][mappings[key]] = value
            update_table = []
            for asset_id, asset_data in data_dicts.items():
                row = [asset_id]
                for column in all_columns:
                    row.append(asset_data.get(column, ''))
                update_table.append(row)
            add_table = []
            for sheet_name, sheet_data in add_per_sheet.items():
                for asset_data in sheet_data:
                    asset_data = dict(
                        (mappings[slugify(k)], v)
                        for (k, v) in asset_data.items()
                        if slugify(k) in mappings
                    )
                    row = []
                    for column in all_columns:
                        row.append(asset_data.get(column, ''))
                    add_table.append(row)
            data['all_columns'] = all_columns
            data['all_column_names'] = all_column_names
            data['update_table'] = update_table
            data['add_table'] = add_table
        return data

    def _get_field_value(self, field_name, value):
        """Transform a pure string into the value to be put into the field."""
        if '.' in field_name:
            Model = self.AmdModel
            _, field_name = field_name.split('.', 1)
        else:
            Model = self.Model
        field, _, _, _ = Model._meta.get_field_by_name(
            field_name
        )
        if not value:
            if (
                isinstance(field, (TextField, CharField)) and
                field_name != 'imei'
            ):
                return ''
            else:
                return
        if isinstance(field, DecimalField):
            if value.count(',') == 1 and '.' not in value:
                value = value.replace(',', '.')
        if field.choices:
            value_lower = value.lower().strip()
            for k, v in field.choices:
                if value_lower == v.lower().strip():
                    value = k
                    break

        if (
            isinstance(value, basestring) and
            isinstance(field, RelatedField) and
            issubclass(field.rel.to, (Named, User, Sluggy))
        ):
            try:
                if issubclass(field.rel.to, User):
                    value = field.rel.to.objects.get(username__iexact=value)
                elif issubclass(field.rel.to, Sluggy):
                    value = field.rel.to.objects.get(slug=value)
                else:
                    value = field.rel.to.objects.get(name__iexact=value)
            except field.rel.to.DoesNotExist:
                if issubclass(field.rel.to, CreatableFromString):
                    value = field.rel.to.create_from_string(
                        asset_type=MODE2ASSET_TYPE[self.mode],
                        s=value
                    )
                    value.save()
                else:
                    raise
        return value

    @transaction.commit_on_success
    def done(self, form_list):
        mappings = self.storage.data['mappings']
        names_per_sheet, update_per_sheet, add_per_sheet =\
            self.get_cleaned_data_for_step('upload')['file']
        failed_assets = []
        errors = {}
        model = self.get_cleaned_data_for_step('upload')['model']
        self.Model = get_model_by_name(model)
        if model == 'ralph_assets.asset':
            amd_field, amd_model = get_amendment_model(self.mode)
            self.AmdModel = get_model_by_name(amd_model)
        else:
            amd_field = amd_model = self.AmdModel = None
        for sheet_name, sheet_data in update_per_sheet.items():
            for asset_id, asset_data in sheet_data.items():
                try:
                    asset = self.Model.objects.get(pk=asset_id)
                except ObjectDoesNotExist:
                    failed_assets.append(asset_id)
                    continue
                try:
                    for key, value in asset_data.items():
                        setattr(
                            asset, mappings[key],
                            self._get_field_value(mappings[key], value)
                        )
                    asset.save()
                except Exception as exc:
                    errors[asset_id] = repr(exc)
        for sheet_name, sheet_data in add_per_sheet.items():
            for asset_data in sheet_data:
                not_found_messages = []
                kwargs = {}
                amd_kwargs = {}
                for key, value in asset_data.items():
                    field_name = mappings.get(slugify(key))
                    if field_name is None:
                        continue
                    try:
                        value = self._get_field_value(field_name, value)
                    except ObjectDoesNotExist:
                        not_found_messages.append(
                            'Cannot find value for {}. '
                            'Resource {} not found.'.format(
                                key,
                                value,
                            )
                        )
                        value = None
                    if amd_field and field_name.startswith(
                        amd_field + '.'
                    ):
                        _, field_name = field_name.split('.', 1)
                        amd_kwargs[field_name] = value
                    else:
                        kwargs[field_name] = value
                try:
                    asset = self.Model(**kwargs)
                    if self.AmdModel is not None:
                        amd_model_object = self.AmdModel(**amd_kwargs)
                        amd_model_object.save()
                        setattr(asset, amd_field, amd_model_object)
                    if isinstance(asset, Asset):
                        asset.type = MODE2ASSET_TYPE[self.mode]
                    else:
                        asset.asset_type = MODE2ASSET_TYPE[self.mode]
                    asset.save()
                except Exception as exc:
                    errors[tuple(asset_data.values())] = repr(exc)
                else:
                    for message in not_found_messages:
                        add_problem(asset, ProblemSeverity.correct_me, message)
        ctx_data = self.get_context_data(None)
        ctx_data['failed_assets'] = failed_assets
        ctx_data['errors'] = errors
        return render(
            self.request,
            'assets/xls_upload_wizard_done.html',
            ctx_data
        )
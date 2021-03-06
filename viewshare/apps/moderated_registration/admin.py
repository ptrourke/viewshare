from django.conf.urls import patterns, url
from django.contrib import admin
from . import models

from django.shortcuts import get_object_or_404, render
from registration.admin import RegistrationAdmin
from django.utils.translation import ugettext_lazy as _

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
import csv
from django.http import HttpResponse
from registration.models import RegistrationProfile


class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ('value',)
    ordering = ('value',)
admin.site.register(models.OrganizationType, OrganizationTypeAdmin)


def organization(obj):
    return obj.user.get_profile().organization
organization.short_description = _("Organization")


def org_type(obj):
    return obj.user.get_profile().org_type
org_type.short_description = _("Organization Type")


def org_state(obj):
    return obj.user.get_profile().location
org_state.short_description = _("Location")


def reason(obj):
    return obj.user.get_profile().about
reason.short_description = _("Reason for joining")


'''
Added by ptrourke to track registration dates of new users.
'''
def date_joined(obj):
    return obj.user.date_joined.strftime('%m/%d/%Y %H:%M')

date_joined.short_description=_("Registered")


class ModeratedRegistrationAdmin(RegistrationAdmin):

    csv_file_name = "registration_profiles.csv"

    export_fields = ('user',
                     'is_approved',
                     'activation_key',
                     date_joined,
                     organization,
                     org_type,
                     org_state,
                     reason)

    list_display = list(export_fields)
    list_filter = ('is_approved', 'user__is_active')

    actions = ['approve_users', 'reject_users', 'export_as_csv']

    def get_actions(self, request):
        actions = super(ModeratedRegistrationAdmin, self).get_actions(request)
        for key in actions.iterkeys():
            if key not in self.actions:
                del actions[key]
        return actions

    def reject_users(self, request, queryset):

        for profile in queryset:
            if not profile.is_approved:
                profile.user.delete()
    reject_users.short_description = _("Reject Users")

    def approve_users(self, request, queryset):
        for profile in queryset:
            self.model.objects.approve_profile(profile)
    approve_users.short_description = _("Approve Users")

    def export_as_csv(self, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        fields = self.export_fields
        field_names = []
        for field in fields:
            if hasattr(field, 'short_description'):
                field_names += [unicode(field.short_description)]
            else:
                field_names += [field]

        mimetype = "text/csv"
        content_disposition = 'attachment; filename=%s' % self.csv_file_name

        response = HttpResponse(content_type=mimetype)
        response['Content-Disposition'] = content_disposition

        writer = csv.writer(response)
        writer.writerow(list(field_names))
        for obj in queryset:
            row = []
            for field in fields:
                if isinstance(field, basestring):
                    row += [unicode(getattr(obj, field))]
                else:
                    row += [unicode(field(obj))]

            writer.writerow(row)
        return response
    export_as_csv.short_description = "Export User Registration " \
                                      "Profiles as CSV"

    def approval_view(self, request, id,
                      template_name="registration/admin_approval.html"):
        ds = self.model.objects.select_related('user', 'user__profile')
        registration_profile = get_object_or_404(ds, id=id)

        args = getattr(request, request.method)
        ds = models.ViewShareRegistrationProfile.objects
        if "reject" in args:
            ds.reject_profile(registration_profile)
            return HttpResponseRedirect("../../")
        elif "approve" in args:
            ds.approve_profile(registration_profile)
        return render(request,
                      template_name,
                      {'profile': registration_profile})

    def change_view(self, request, object_id, extra_context=None):
        approve_url = reverse('admin:approve_users', kwargs={"id": object_id})
        return HttpResponseRedirect(approve_url)

    def get_urls(self):
        urls = super(ModeratedRegistrationAdmin, self).get_urls()

        return patterns('',
            url(r'^(?P<id>[\d]+)/moderate/$$',
                self.admin_site.admin_view(self.approval_view),
                name="approve_users"),
        ) + urls


admin.site.unregister(RegistrationProfile)
admin.site.register(models.ViewShareRegistrationProfile,
    ModeratedRegistrationAdmin)

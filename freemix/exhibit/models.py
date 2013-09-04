import json
import logging
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction as db_tx
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django_extensions.db.fields.json import JSONField
from django_extensions.db.models import (TitleSlugDescriptionModel,
                                         TimeStampedModel)


TX_STATUS = {
    "pending": 1,
    "scheduled": 2,
    "running": 3,
    "success": 4,
    "failure": 5,
    "cancelled": 6,
}

#-----------------------------------------------------------------------------#
# Exhibit Property Types
#-----------------------------------------------------------------------------#

VALUE_TYPES = {
    "text": "text",
    "url": "URL",
    "image": "image",
    "date": "date/time",
    "location": "location",
    "number": "number"
}


class Canvas(TitleSlugDescriptionModel):
    """
    A reference to a template that contains the HTML for an Exhibit canvas
    """

    location = models.CharField(_('location'), unique=True, max_length=100,
                                help_text=_("Example: "
                                            "'exhibit/canvas/"
                                            "three-column.html'"))

    thumbnail = models.URLField(_('thumbnail'))

    enabled = models.BooleanField(_('enabled'), null=False, default=True)

    def get_html(self):
        return render_to_string(self.location, {})

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Canvases"



def create_default_exhibit_profile():
    return {
        "facets": {},
        "views": {
            "views": [{
                "id": str(uuid.uuid4()),
                "type": "list",
                "name": "List"
            }]
        },
        "lenses": []
    }

class Exhibit(TimeStampedModel):

    profile = JSONField()

    canvas = models.ForeignKey(Canvas)

    owner = models.ForeignKey(User, null=True)

    slug = models.SlugField(editable=False, blank=True)

    is_draft = models.BooleanField(default=True, editable=False)

    class Meta:
        unique_together = ('owner', 'slug', 'is_draft')

    def update_from_profile(self, profile):
        self.profile = profile
        self.save()

    def natural_key(self):
        return self.owner, self.slug, self.is_draft

    def get_draft(self):
        if self.is_draft:
            return self.draftexhibit
        return self.publishedexhibit.get_draft()


class PublishedExhibit(Exhibit):
    """
    A published exhibit with a title and slug for display to end users
    """

    is_public = models.BooleanField(default=True)
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True, null=True)

    @models.permalink
    def get_absolute_url(self):
        return ('exhibit_display', (), {
            'owner': self.owner.username,
            'slug': self.slug})

    def __unicode__(self):
        return self.title

    def get_draft(self):
        try:
            return self.draftexhibit
        except ObjectDoesNotExist:
            pass
        draft = DraftExhibit.objects.create(parent=self,
                                            slug=self.slug,
                                            profile=self.profile,
                                            canvas=self.canvas,
                                            owner=self.owner,
                                            is_draft=True)
        draft.save()

        from freemix.exhibit.serializers import ExhibitPropertyListSerializer
        data = ExhibitPropertyListSerializer(self, queryset=self.properties).data
        out = ExhibitPropertyListSerializer(draft, data=data)
        out.save()

        for t in  (PropertyData.objects
                    .filter(exhibit_property__exhibit=self)
                    .values_list("exhibit_property__name", "json")):
            p = draft.properties.get(name=t[0])
            PropertyData(exhibit_property=p, json=json.loads(t[1])).save()
        return draft

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.is_draft = True
        super(PublishedExhibit, self).save(force_insert=force_insert,
                                       force_update=force_update,
                                       using=using,
                                       update_fields=update_fields)

    class Meta:
        ordering = ('-modified', )


class DraftExhibit(Exhibit):
    """
    A draft exhibit for editing.  Modifications to a `DraftExhibit` will
    not be visible to end users.  If `parent` is populated, the draft should
    be a copy of the reference `PublishedExhibit`.  Publishing the draft will
    move the contents of the `DraftExhibit` into the `PublishedExhibit` and the
    draft will be deleted.  If `parent` is null, a new `PublishedExhibit` will
    be created on publication.
    """

    parent = models.OneToOneField(PublishedExhibit,
                                  null=True,
                                  blank=True)

    @models.permalink
    def get_absolute_url(self):
        return ('exhibit_edit', (), {
            'owner': self.owner.username,
            'slug': self.slug})

    def publish(self):
        self.parent.canvas=self.canvas
        self.parent.profile=self.profile
        self.parent.properties.all().delete()
        self.parent.modified = self.modified
        self.parent.save()
        self.properties.update(exhibit=self.parent)

        self.delete()

    class Meta:
        ordering = ('-modified', )

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.is_draft = True
        super(DraftExhibit, self).save(force_insert=force_insert,
                                       force_update=force_update,
                                       using=using,
                                       update_fields=update_fields)

    def save_basic_profile(self):
        self.profile = {
            "facets": {},
            "views": {
                "views": [{
                    "id": str(uuid.uuid4()),
                    "type": "list",
                    "name": "List",
                    "lens": {
                        "type": "list",
                        "properties": [p.name for p in self.properties.all()]
                    }
                }],
            },
            "default_lens":{
                "type": "list",
                "properties":  [p.name for p in self.properties.all()]
            },

        }
        self.save()

    def get_draft(self):
        return self


def get_data_url(t):
    """
    Does on a reverse on the url represented in the provided tuple
    """
    if t[3]:
        key = "exhibit_property_data"

    key = "draft_exhibit_property_data" if t[3] else "exhibit_property_data"
    return reverse(key, kwargs={
        "owner": t[0],
        "slug": t[1],
        "property": t[2]
    })


class ExhibitPropertyManager(models.Manager):
    """
    Utility methods for the filtered properties on a particular exhibit
    """
    use_for_related_fields = True

    def get_data_urls(self):
        """
        Return a list of data URLs for each property
        """

        qs = self.get_query_set().exclude(data=None)
        qs = qs.values_list("exhibit__owner__username",
                            "exhibit__slug",
                            "name",
                            "exhibit__is_draft")
        return [get_data_url(t) for t in qs]


class ExhibitProperty(models.Model):
    """
    The Base class for defining individual properties in an exhibit
    dataset.  The properties defined in this class should be adequate
    for reference in published exhibits and basic properties.
    """

    default_manager = ExhibitPropertyManager()

    classname = models.CharField(max_length=32, editable=False, null=True)

    exhibit = models.ForeignKey(Exhibit,
                                related_name="properties")

    label = models.CharField(_('label'), max_length=255)

    name = models.CharField(_('name'), max_length=255)

    value_type = models.CharField(choices=[(k, v) for k, v in
                                           VALUE_TYPES.iteritems()],
                                  default="text",
                                  max_length=10)

    class Meta:
        unique_together = ('exhibit', 'name')

    def natural_key(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.classname is None:
            self.classname = self.__class__.__name__
        return super(ExhibitProperty, self).save(*args, **kwargs)

    def get_concrete(self):
        if self.classname == "ExhibitProperty":
            return self
        return self.__getattribute__(self.classname.lower())

    def is_concrete(self):
        return self.classname == self.__class__.__name__

    def get_properties_url(self):
        return reverse("exhibit_property_list", kwargs={
            "owner": self.owner,
            "slug": self.slug
        })


class CompositeProperty(ExhibitProperty):
    """
    Enhanced property that is derived from other properties.  This
    covers both date/time and location derivations.  An ordered list of
    source properties is defined using the PropertyReference model.
    """

    composite = models.ManyToManyField(ExhibitProperty,
                                       through='PropertyReference',
                                       related_name="+")


class PropertyReference(models.Model):
    """
    A reference to a property used in the derivation of a composite property.
        `derived`: the composite property
        `source`: The referenced property
        `order`: The referenced property's position in the list of sources
    """

    derived = models.ForeignKey('CompositeProperty', related_name="properties")

    source = models.ForeignKey(ExhibitProperty)

    order = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("derived", "source", )
        ordering = ("order", )


class ShreddedListProperty(ExhibitProperty):
    """
    Abstract Base class for properties that derive a list from another property
    """
    source = models.ForeignKey(ExhibitProperty, related_name="+")

    class Meta:
        abstract = True


class DelimitedListProperty(ShreddedListProperty):
    """
    Enhanced list property that is split based on a string delimiter
    """
    delimiter = models.TextField(_("delimiter"))


class PatternListProperty(ShreddedListProperty):
    """
    Enhanced list property this is split based on a regular expression
    """

    pattern = models.TextField(_("pattern"))


class PropertyData(TimeStampedModel):
    """
    The data for a particular property in the format:
    ```
        [
            {
                "id": <id>,
                "label": <label>,
                "<property name>": <property value>
            },
            ...
        ]
    ```
    """

    exhibit_property = models.OneToOneField(ExhibitProperty,
                                            related_name="data")
    json = JSONField()


class DataTransaction(TimeStampedModel):
    """
    Abstract base class to handle potentially long-running data work such as
    Akara transformations and augmentations.
    """
    status = models.IntegerField(
            choices=[(v, k) for k, v in TX_STATUS.iteritems()],
            default=TX_STATUS["pending"])
    is_complete = models.BooleanField(default=False)

    class meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        Give our transaction access to logging.
        """
        super(DataTransaction, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def is_expired(self):
        raise NotImplementedError()

    def is_ready(self):
        return self.status in (TX_STATUS["success"], TX_STATUS["cancelled"])

    @models.permalink
    def get_absolute_url(self):
        """
        Return a URL to get status updates about this transaction
        """
        raise NotImplementedError()

    def start_transaction(self):
        """
        Start the asyncronous task for this transaction.
        """
        raise NotImplementedError()

    def schedule(self):
        with db_tx.commit_manually():
            try:
                self.status = TX_STATUS["scheduled"]
                self.save()
                db_tx.commit()
            except Exception as ex:
                self.failure(ex.message)
            else:
                self.start_transaction()

    def run(self):
        with db_tx.commit_manually():
            try:
                self.status = TX_STATUS["running"]
                self.save()
                self.do_run()
                db_tx.commit()
            except Exception as ex:
                self.failure(ex.message)
        return self

    def failure(self, message):
        self.logger.error("Error for transaction %s: %s" % (self.tx_id, message))
        self.status = TX_STATUS["failure"]
        self.result = {"message": message}
        self.save()

    def success(self):
        self.status = TX_STATUS["success"]
        self.save()

    def complete(self):
        self.is_complete = True
        self.result = None
        self.save()

    def cancel(self):
        self.status = TX_STATUS["cancelled"]
        self.result = None
        self.is_complete = True
        self.save()

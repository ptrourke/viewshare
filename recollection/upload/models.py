from django.db import models
from freemix.dataset.models import DataSource, URLDataSourceMixin, FileDataSourceMixin
from django.utils.translation import ugettext_lazy as _
from freemix.transform.views import AkaraTransformClient
from recollection.upload import conf



class URLDataSource(URLDataSourceMixin, DataSource):
    """Generic URL data source
    """

class FileDataSource(FileDataSourceMixin, DataSource):
    """Generic File data source
    """

class ContentDMDataSource(URLDataSourceMixin, DataSource):
    """Data source for loading data from a particular CONTENTdm site based on collection name or query.
    """

    collection = models.CharField(_("Collection"),
                                  max_length=255,
                                  null=True,
                                  blank=True,
                                  help_text=_("Collection names begin with the <strong>/</strong> character"))

    query = models.CharField(_("Search term"),
                             max_length=255,
                             null=True,
                             blank=True)

    limit = models.IntegerField(_("Limit"),
                                help_text=_("The maximum number of records to load"),
                                default="100",
                                choices=((100, "100"),
                                         (200, "200"),
                                         (300, "300"),
                                         (400, "400")))


    # Data transform
    transform = AkaraTransformClient(conf.AKARA_CONTENTDM_URL)

    def get_transform_params(self):
        p =  {'site': self.url,
                'limit': self.limit}
        if self.collection:
            p['collection']=self.collection
        if self.query:
            p['query'] = self.query
        return p

    def get_transform_body(self):
        return None


class ModsMixin(models.Model):
    """Data source for loading XMLMODS data.
    """
    diagnostics = models.BooleanField(_("Verify Data"),
                                      help_text=_("<a class='verify_data_help' href='#load-info-verify-data'>What's This?</a>"))

    class Meta:
        abstract=True
    
    def get_transform_params(self):
        p = {}
        if self.diagnostics:
            p['diagnostics'] = "yes"
        return p


class ModsURLDataSource(ModsMixin, URLDataSourceMixin, DataSource):
    """Load XMLMODS from a URL
    """

class ModsFileDataSource(ModsMixin, FileDataSourceMixin, DataSource):
    """Load XMLMODS from an uploaded file
    """
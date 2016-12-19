from django.db import models
from django.utils.translation import ugettext_lazy as _


class GeturlBlackList(models.Model):
    """
    Model used for store a blacklist of invalid URL's for geturl component
    """

    black_url = models.CharField(_('Black url'),
                                 max_length=300)
                                 

    
    class Meta:
        verbose_name = _('Geturl Black List')

    def __str__(self):
        return self.black_url             

    def __unicode__(self):
        return self.black_url



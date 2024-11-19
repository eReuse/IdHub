from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.constants import (
    STR_SM_SIZE,
    STR_SIZE,
    STR_EXTEND_SIZE,
)

from user.models import User, Institution
# from device.models import Device
# from evidence.models import Annotation


class LotTag(models.Model):
    name = models.CharField(max_length=STR_SIZE, blank=False, null=False)
    owner = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class DeviceLot(models.Model):
    lot = models.ForeignKey("Lot", on_delete=models.CASCADE)
    device_id = models.CharField(max_length=STR_EXTEND_SIZE, blank=False, null=False)


class Lot(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=STR_SIZE, blank=True, null=True)
    code = models.CharField(max_length=STR_SIZE, blank=True, null=True)
    description = models.CharField(max_length=STR_SIZE, blank=True, null=True)
    closed = models.BooleanField(default=False)
    owner = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.ForeignKey(LotTag, on_delete=models.CASCADE)

    def add(self, v):
        if DeviceLot.objects.filter(lot=self, device_id=v).exists():
            return
        DeviceLot.objects.create(lot=self, device_id=v)
        
    def remove(self, v):
        for d in DeviceLot.objects.filter(lot=self, device_id=v):
            d.delete()


class LotAnnotation(models.Model):
    class Type(models.IntegerChoices):
        SYSTEM= 0, "System"
        USER = 1, "User"
        DOCUMENT = 2, "Document"

    created = models.DateTimeField(auto_now_add=True)
    lot  = models.ForeignKey(Lot, on_delete=models.CASCADE)
    owner = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    type =  models.SmallIntegerField(choices=Type) 
    key = models.CharField(max_length=STR_EXTEND_SIZE)
    value = models.CharField(max_length=STR_EXTEND_SIZE)

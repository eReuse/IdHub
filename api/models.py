from django.db import models
from user.models import User


class Token(models.Model):
    tag = models.CharField(max_length=50)
    token = models.UUIDField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

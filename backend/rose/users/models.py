from django.contrib.auth.models import User
from django.db import models
from datetime import datetime

class UserLoginInformations(models.Model):
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    daily_login_count = models.PositiveIntegerField(default=0)
    last_login_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "User Login Information"
        verbose_name_plural = "User Login Informations"

    def __str__(self):
        return f"{self.user.username}"

    def increment_daily_login_count(self, ip):
        self.last_login_date = datetime.now()
        self.daily_login_count += 1
        self.last_login_ip = ip
        self.save()

    def get_last_login_info(self):
        return {
            'last_login_date': self.last_login_date,
            'daily_login_count': self.daily_login_count
        }
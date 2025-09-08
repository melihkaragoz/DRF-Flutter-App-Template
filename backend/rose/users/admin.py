from django.contrib import admin
from .models import UserLoginInformations


@admin.register(UserLoginInformations)
class UserLoginInformationsAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_login_ip', 'daily_login_count', 'last_login_date')
    search_fields = ('user__username', 'last_login_ip')
    list_filter = ('daily_login_count',)

from django.contrib import admin
from .models import Profile

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cliente')
    search_fields = ('user', 'cliente')
    list_filter = ('user', 'cliente')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('cliente',)
    list_display_links = ('user',)
    ordering = ('user',)
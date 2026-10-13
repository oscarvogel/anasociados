from django.contrib import admin
from .models import AreasProfile, Profile, UsuarioIngreso, UsuarioMenuAcceso

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
    
@admin.register(AreasProfile)
class AreasProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'area')
    search_fields = ('user', 'area')
    list_filter = ('user', 'area')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('area',)
    list_display_links = ('user',)
    ordering = ('user',)


@admin.register(UsuarioIngreso)
class UsuarioIngresoAdmin(admin.ModelAdmin):
    list_display = ('user', 'fecha_hora')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('fecha_hora',)
    ordering = ('-fecha_hora',)


@admin.register(UsuarioMenuAcceso)
class UsuarioMenuAccesoAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu_nombre', 'fecha_hora')
    search_fields = ('user__username', 'menu_nombre', 'menu_codigo', 'path')
    list_filter = ('menu_nombre', 'fecha_hora')
    ordering = ('-fecha_hora',)
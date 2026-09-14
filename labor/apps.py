from django.apps import AppConfig


class LaborConfig(AppConfig):
    name = 'labor'
    verbose_name = 'Labor'

    def ready(self):
        _patch_jazzmin_format_html()
    
    
def _patch_jazzmin_format_html():
    """
    django-jazzmin calls format_html() with no args for prebuilt HTML
    fragments (e.g. jazzmin_paginator_number), which Django 5.1+ rejects
    with TypeError. Restore the old permissive behavior for jazzmin only.
    """
    from django.utils.safestring import mark_safe
    from django.utils.html import format_html as _format_html

    def format_html_compat(format_string, *args, **kwargs):
        if not (args or kwargs):
            return mark_safe(format_string)
        return _format_html(format_string, *args, **kwargs)

    try:
        import jazzmin.templatetags.jazzmin as jazzmin_tags
        jazzmin_tags.format_html = format_html_compat
    except ImportError:
        pass
    
    

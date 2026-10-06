from django.apps import AppConfig


class IdhubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'idhub'

    def ready(self):
        import requests_cache

        cache_rules = {
            '*.w3.org': 86400,
            '*.w3id.org': 86400,
            'w3c-ccg.github.io': 86400,
            'idhub.pangea.org': 86400,
            'localhost*': 3600,
            '*': requests_cache.DO_NOT_CACHE
        }

        requests_cache.install_cache(
            'idhub_global_cache',
            backend='memory',
            urls_expire_after=cache_rules,
            allowable_methods=('GET',)
        )

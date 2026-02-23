from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OffermanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "offerman"
    verbose_name = _("Catálogo de Produtos")

    def ready(self):
        from django.contrib.admin.views.autocomplete import AutocompleteJsonView

        _original_serialize = AutocompleteJsonView.serialize_result

        def serialize_result(self, obj, to_field_name):
            result = _original_serialize(self, obj, to_field_name)
            if hasattr(obj, "base_price_q"):
                result["base_price_q"] = obj.base_price_q
            return result

        AutocompleteJsonView.serialize_result = serialize_result

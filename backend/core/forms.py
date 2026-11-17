from django import forms


class BootstrapFormMixin:
    """Adds Bootstrap 5 CSS classes to every widget (idempotent)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            existing = widget.attrs.get("class", "")
            if css not in existing.split():
                widget.attrs["class"] = f"{existing} {css}".strip()

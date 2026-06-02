from gi.repository import Gtk, Adw
from config_panel_constants import get_nested, set_nested


class RowBuilderMixin:

    def _entry_row(self, title: str, keys: list[str], config_src=None) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        cfg = config_src if config_src is not None else self._config
        val = get_nested(cfg, keys, "")
        row.set_text(str(val) if val else "")
        def on_changed(r, k=keys, c=cfg):
            set_nested(c, k, r.get_text())
            self._mark_unsaved()
        row.connect("changed", on_changed)
        return row

    def _switch_row(self, title: str, keys: list[str], subtitle: str = "", config_src=None) -> Adw.SwitchRow:
        row = Adw.SwitchRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        cfg = config_src if config_src is not None else self._config
        row.set_active(bool(get_nested(cfg, keys, False)))
        def on_toggle(r, _p, k=keys, c=cfg):
            set_nested(c, k, r.get_active())
            self._mark_unsaved()
        row.connect("notify::active", on_toggle)
        return row

    def _combo_row(self, title: str, keys: list[str], choices: list[str], config_src=None) -> Adw.ComboRow:
        row = Adw.ComboRow(title=title)
        store = Gtk.StringList()
        for c in choices:
            store.append(c)
        row.set_model(store)
        cfg = config_src if config_src is not None else self._config
        val = get_nested(cfg, keys, choices[0] if choices else "")
        if val in choices:
            row.set_selected(choices.index(val))
        def on_changed(r, _p, k=keys, ch=choices, c=cfg):
            idx = r.get_selected()
            if 0 <= idx < len(ch):
                set_nested(c, k, ch[idx])
                self._mark_unsaved()
        row.connect("notify::selected", on_changed)
        return row

    def _spin_row(self, title: str, keys: list[str],
                  min_val=0, max_val=9_999_999, step=1, subtitle: str = "", config_src=None) -> Adw.SpinRow:
        cfg = config_src if config_src is not None else self._config
        adj = Gtk.Adjustment(
            value=float(get_nested(cfg, keys, 0) or 0),
            lower=min_val, upper=max_val, step_increment=step,
        )
        row = Adw.SpinRow(title=title, adjustment=adj)
        if subtitle:
            row.set_subtitle(subtitle)
        def on_changed(r, k=keys, c=cfg):
            set_nested(c, k, int(r.get_value()))
            self._mark_unsaved()
        row.connect("changed", on_changed)
        return row

    def _combo_row_direct(self, title: str, choices: list[str], current: str,
                          on_change, subtitle: str = "") -> Adw.ComboRow:
        row = Adw.ComboRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)

        if not choices:
            choices = ["No options found"]
            row.set_sensitive(False)

        store = Gtk.StringList()
        for c in choices:
            store.append(c)
        row.set_model(store)

        selected = 0
        if current in choices:
            selected = choices.index(current)
        row.set_selected(selected)

        def on_selected(r, _p, ch=choices):
            idx = r.get_selected()
            if 0 <= idx < len(ch):
                on_change(ch[idx])
                self._mark_unsaved()

        row.connect("notify::selected", on_selected)
        return row

from template_loader import get_template


def test_templates_render_with_included_js():
    get_template.cache_clear()
    for name in ("clan.html", "market.html", "battles.html"):
        rendered = get_template(name)
        assert f"<!-- Template {name} not found -->" not in rendered
        assert "not found -->" not in rendered
        assert "<script>" in rendered
        assert "</script>" in rendered

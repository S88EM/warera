"""
WarEra Clan Combat Intelligence Dashboard.
Loads standalone HTML dashboard from api/templates/clan.html.
"""

from template_loader import get_template

# Backwards compatibility: exports the HTML string loaded from template
CLAN_DASHBOARD_HTML = get_template("clan.html")

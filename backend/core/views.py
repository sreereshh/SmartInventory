from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from reports.services import dashboard_data


@login_required
def dashboard(request):
    data = dashboard_data()
    chart_data = {
        "sales_labels": [d["label"] for d in data["sales"]["last_7_days"]],
        "sales_values": [float(d["total"]) for d in data["sales"]["last_7_days"]],
        "status_labels": [s.title() for s in data["sales"]["orders_by_status"].keys()],
        "status_values": list(data["sales"]["orders_by_status"].values()),
        "category_labels": [c["category"] for c in data["inventory"]["stock_by_category"]],
        "category_units": [c["units"] for c in data["inventory"]["stock_by_category"]],
    }
    return render(request, "dashboard.html", {"d": data, "chart_data": chart_data})

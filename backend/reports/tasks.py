from celery import shared_task
from django.core.cache import cache
import concurrent.futures
import httpx

from .services.nhtsa    import fetch_nhtsa
from .services.vinaudit import fetch_vinaudit
from .services.scoring  import calculate_risk_score


@shared_task
def fetch_vehicle_report(vin: str) -> dict:
    cache_key = f'report:{vin}'
    cached    = cache.get(cache_key)
    if cached:
        return cached

    with concurrent.futures.ThreadPoolExecutor() as pool:
        nhtsa_f   = pool.submit(fetch_nhtsa, vin)
        history_f = pool.submit(fetch_vinaudit, vin)

    nhtsa   = nhtsa_f.result()
    history = history_f.result()

    report = {
        'vin':                    vin,
        'vehicle':                nhtsa.get('vehicle'),
        'recalls':                nhtsa.get('recalls', []),
        'accident_count':         history.get('accident_count', 0),
        'accidents':              history.get('accidents', []),
        'owner_count':            history.get('owner_count'),
        'owners':                 history.get('owners', []),
        'odometer':               history.get('odometer', []),
        'last_reported_odometer': history.get('last_reported_odometer'),
        'title_flags':            history.get('title_flags', []),
        'market_value': {
            'fair':   history.get('estimated_value'),
            'source': 'VINAudit',
        } if history.get('estimated_value') else None,
        'risk_score': calculate_risk_score(history, nhtsa),
        'data_sources': {
            'history': 'VINAudit' if history.get('success') else 'unavailable',
            'vehicle': 'NHTSA',
            'recalls': 'NHTSA',
        },
    }

    cache.set(cache_key, report)
    return report


@shared_task
def check_new_recalls_and_notify():
    """Runs nightly. Checks for new NHTSA recalls and pushes notifications."""
    from .models import VehicleReport, ReportLookup
    from users.models import PushToken

    for report in VehicleReport.objects.all():
        fresh     = fetch_nhtsa(report.vin)
        new_count = len(fresh.get('recalls', []))
        old_count = report.open_recall_count

        if new_count > old_count:
            new_recalls = fresh['recalls'][old_count:]
            lookups     = ReportLookup.objects.filter(report=report).select_related('user')
            v           = report.raw_data.get('vehicle', {})
            car_name    = f"{v.get('year', '')} {v.get('make', '')} {v.get('model', '')}".strip()

            for lookup in lookups:
                tokens = PushToken.objects.filter(
                    user=lookup.user
                ).values_list('token', flat=True)
                for token in tokens:
                    _send_push(
                        token=token,
                        title=f"New recall on your {car_name or 'vehicle'}",
                        body=f"{new_recalls[0].get('component', 'Safety issue')} — tap for details.",
                        data={'vin': report.vin},
                    )

            report.open_recall_count       = new_count
            report.raw_data['recalls']     = fresh['recalls']
            report.save(update_fields=['open_recall_count', 'raw_data'])


def _send_push(token: str, title: str, body: str, data: dict):
    try:
        httpx.post('https://exp.host/--/api/v2/push/send', json={
            'to':    token,
            'title': title,
            'body':  body,
            'data':  data,
            'sound': 'default',
        }, timeout=5)
    except Exception:
        pass

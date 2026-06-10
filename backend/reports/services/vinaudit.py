import requests
from decouple import config

BASE_URL = 'https://api.vinaudit.com/query.php'


def fetch_vinaudit(vin: str) -> dict:
    try:
        resp = requests.get(BASE_URL, params={
            'key':     config('VINAUDIT_API_KEY', default=''),
            'vin':     vin,
            'format':  'json',
            'include': 'accidents,owners,titles,odometer,salvage,recalls',
        }, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if not data.get('success'):
            return _empty(error=data.get('message', 'No data returned'))
        return _normalize(data)
    except requests.Timeout:
        return _empty(error='VINAudit timed out')
    except requests.RequestException as e:
        return _empty(error=str(e))


def _normalize(data: dict) -> dict:
    attributes = data.get('attributes', {})
    records    = data.get('records', [])

    accidents = [
        {
            'date':            r.get('date'),
            'state':           r.get('state'),
            'odometer':        r.get('odometer'),
            'type':            r.get('accidentType'),
            'severity':        r.get('severity'),
            'airbag_deployed': r.get('airbagDeployed', False),
            'damage_areas':    r.get('damageAreas', []),
        }
        for r in records if r.get('type') == 'accident'
    ]

    owners = [
        {
            'sequence':                r.get('ownerSequence'),
            'entity_type':             r.get('entityType'),
            'state':                   r.get('state'),
            'acquired':                r.get('dateAcquired'),
            'sold':                    r.get('dateSold'),
            'estimated_length_months': r.get('estimatedLengthMonths'),
        }
        for r in records if r.get('type') == 'owner'
    ]

    odometer = [
        {'date': r.get('date'), 'miles': r.get('odometer'), 'source': r.get('source')}
        for r in records if r.get('type') == 'odometer'
    ]

    title_flags = []
    flag_map = {
        'salvageTitle':     'salvage',
        'floodDamage':      'flood',
        'lemonStatus':      'lemon',
        'frameDamage':      'frame_damage',
        'odometerRollback': 'odometer_rollback',
        'theftRecovered':   'theft_recovered',
        'rentalVehicle':    'rental',
    }
    for attr_key, flag in flag_map.items():
        if attributes.get(attr_key):
            title_flags.append(flag)

    return {
        'success':                True,
        'accident_count':         len(accidents),
        'accidents':              accidents,
        'owner_count':            attributes.get('ownerCount') or len(owners),
        'owners':                 owners,
        'odometer':               odometer,
        'title_flags':            title_flags,
        'last_reported_odometer': attributes.get('lastOdometer'),
        'estimated_value':        attributes.get('estimatedValue'),
        'error':                  None,
    }


def _empty(error: str = None) -> dict:
    return {
        'success':                False,
        'accident_count':         0,
        'accidents':              [],
        'owner_count':            None,
        'owners':                 [],
        'odometer':               [],
        'title_flags':            [],
        'last_reported_odometer': None,
        'estimated_value':        None,
        'error':                  error,
    }

import requests
from typing import Optional

DECODE_URL = 'https://api.nhtsa.gov/vehicles/decodevinvalues/{vin}?format=json'
RECALL_URL = 'https://api.nhtsa.gov/recalls/recallsByVehicle'


def fetch_nhtsa(vin: str) -> dict:
    vehicle = _decode_vin(vin)
    recalls = _fetch_recalls(
        make=vehicle.get('make'),
        model=vehicle.get('model'),
        year=vehicle.get('year'),
    ) if vehicle else []
    return {'vehicle': vehicle, 'recalls': recalls}


def _decode_vin(vin: str) -> Optional[dict]:
    try:
        resp = requests.get(DECODE_URL.format(vin=vin), timeout=6)
        resp.raise_for_status()
        r = resp.json().get('Results', [{}])[0]

        def val(key):
            return r.get(key) or None

        displacement = val('DisplacementL')
        fuel         = val('FuelTypePrimary')
        engine       = f"{displacement}L {fuel}" if displacement else None

        return {
            'make':          val('Make'),
            'model':         val('Model'),
            'year':          val('ModelYear'),
            'trim':          val('Trim'),
            'body_style':    val('BodyClass'),
            'engine':        engine,
            'drive_type':    val('DriveType'),
            'transmission':  val('TransmissionStyle'),
            'plant_country': val('PlantCountry'),
            'errors':        val('ErrorText'),
        }
    except requests.RequestException:
        return None


def _fetch_recalls(make: str, model: str, year: str) -> list:
    if not all([make, model, year]):
        return []
    try:
        resp = requests.get(RECALL_URL, params={
            'make': make, 'model': model, 'modelYear': year,
        }, timeout=6)
        resp.raise_for_status()
        return [
            {
                'id':          r.get('NHTSACampaignNumber'),
                'component':   r.get('Component'),
                'summary':     r.get('Summary'),
                'consequence': r.get('Conequence'),
                'remedy':      r.get('Remedy'),
                'date':        r.get('ReportReceivedDate'),
            }
            for r in resp.json().get('results', [])
        ]
    except requests.RequestException:
        return []

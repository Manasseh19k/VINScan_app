def calculate_risk_score(history: dict, nhtsa: dict) -> int:
    score = 100

    for accident in history.get('accidents', []):
        severity = (accident.get('severity') or '').lower()
        if 'severe'   in severity: score -= 25
        elif 'moderate' in severity: score -= 15
        else:                       score -= 8
        if accident.get('airbag_deployed'): score -= 10

    flag_penalties = {
        'salvage':          30,
        'flood':            25,
        'lemon':            20,
        'frame_damage':     20,
        'odometer_rollback':25,
        'theft_recovered':  15,
        'rental':            5,
    }
    for flag in history.get('title_flags', []):
        score -= flag_penalties.get(flag, 5)

    score -= len(nhtsa.get('recalls', [])) * 5

    owners = history.get('owner_count') or 1
    if owners > 3:
        score -= (owners - 3) * 5

    if _has_odometer_rollback(history.get('odometer', [])):
        score -= 20

    return max(0, min(100, score))


def _has_odometer_rollback(readings: list) -> bool:
    miles = [r['miles'] for r in readings if r.get('miles')]
    for i in range(1, len(miles)):
        if miles[i] < miles[i - 1]:
            return True
    return False

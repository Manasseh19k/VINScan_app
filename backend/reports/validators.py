TRANSLITERATION = {
    'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,
    'J':1,'K':2,'L':3,'M':4,'N':5,'P':7,'R':9,
    'S':2,'T':3,'U':4,'V':5,'W':6,'X':7,'Y':8,'Z':9,
}
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def validate_vin(vin: str) -> tuple[bool, str]:
    v = vin.upper().strip()
    if len(v) != 17:
        return False, 'VIN must be exactly 17 characters'
    if any(c in v for c in 'IOQ'):
        return False, 'VIN cannot contain I, O, or Q'
    total = 0
    for i, char in enumerate(v):
        val = int(char) if char.isdigit() else TRANSLITERATION.get(char)
        if val is None:
            return False, f'Invalid character: {char}'
        total += val * WEIGHTS[i]
    remainder  = total % 11
    check_char = 'X' if remainder == 10 else str(remainder)
    if v[8] != check_char:
        return False, 'VIN failed checksum validation'
    return True, ''


def decode_vin(vin: str) -> dict:
    return {
        'wmi':               vin[:3],
        'vds':               vin[3:9],
        'vis':               vin[9:],
        'model_year_code':   vin[9],
        'plant_code':        vin[10],
        'sequential_number': vin[11:],
    }

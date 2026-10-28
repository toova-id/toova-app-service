import csv

from odoo.modules.module import get_module_resource


_STATE_CODES = {
    '11': 'AC', '12': 'SU', '13': 'SB', '14': 'RI', '15': 'JA', '16': 'SS', '17': 'BE', '18': 'LA',
    '19': 'BB', '21': 'KR', '31': 'JK', '32': 'JB', '33': 'JT', '34': 'YO', '35': 'JI', '36': 'BT',
    '51': 'BA', '52': 'NB', '53': 'NT', '61': 'KB', '62': 'KT', '63': 'KS', '64': 'KI', '65': 'KU',
    '71': 'SA', '72': 'ST', '73': 'SN', '74': 'SG', '75': 'GO', '76': 'SR', '81': 'MA', '82': 'MU',
    '91': 'PA', '92': 'PB', '93': 'PS', '94': 'PT', '95': 'PE', '96': 'PD',
}
_LEVELS = {1: 'province', 2: 'regency', 3: 'district', 4: 'village'}


def post_init_hook(cr, registry):
    path = get_module_resource('indonesia_regions', 'data', 'regions.csv')
    with open(path, encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    cr.execute("SELECT id, code FROM res_country_state WHERE country_id = (SELECT id FROM res_country WHERE code = 'ID')")
    state_by_code = {code: state_id for state_id, code in cr.fetchall()}
    values = []
    for row in rows:
        province_code = row['code'].split('.')[0]
        values.append((
            row['code'], row['name'], _LEVELS[int(row['level'])], row['postal_code'] or None,
            state_by_code.get(_STATE_CODES[province_code]),
        ))
    cr.executemany('''INSERT INTO managed_indonesia_region
        (code, name, level, postal_code, state_id, active, create_uid, write_uid, create_date, write_date)
        VALUES (%s, %s, %s, %s, %s, TRUE, 1, 1, NOW(), NOW())
        ON CONFLICT (code) DO UPDATE SET
        name = EXCLUDED.name, level = EXCLUDED.level, postal_code = EXCLUDED.postal_code,
        state_id = EXCLUDED.state_id, active = TRUE, write_date = NOW()''', values)
    cr.execute('SELECT id, code FROM managed_indonesia_region')
    ids = {code: region_id for region_id, code in cr.fetchall()}
    parent_values = [(ids.get(row['parent_code']), row['code']) for row in rows if row['parent_code']]
    cr.executemany('UPDATE managed_indonesia_region SET parent_id = %s WHERE code = %s', parent_values)

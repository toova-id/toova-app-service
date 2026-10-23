#!/usr/bin/env python3
import tempfile
from pathlib import Path

from prune_translations import prune

with tempfile.TemporaryDirectory() as directory:
    i18n = Path(directory, 'addons', 'x', 'i18n')
    i18n_extra = Path(directory, 'addons', 'x', 'i18n_extra')
    i18n.mkdir(parents=True)
    i18n_extra.mkdir(parents=True)
    for name in ('id.po', 'fr.po', 'x.pot'):
        i18n.joinpath(name).write_text(name)
    i18n_extra.joinpath('fr.po').write_text('fr')
    removed = prune(directory, {'id'}, apply=True)
    assert sorted(path.name for path in removed) == ['fr.po', 'fr.po']
    assert i18n.joinpath('id.po').exists()
    assert i18n.joinpath('x.pot').exists()
    assert not i18n_extra.joinpath('fr.po').exists()
print('translation pruning self-check passed')

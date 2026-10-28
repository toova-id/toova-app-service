# -*- coding: utf-8 -*-
from odoo.modules.module import runtime_role_enabled

from . import models
if runtime_role_enabled('http', 'realtime'):
    from . import controllers

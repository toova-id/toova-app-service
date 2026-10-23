# -*- coding: utf-8 -*-
from odoo.modules.module import runtime_role_enabled

if runtime_role_enabled('http'):
    from . import controllers
from . import models
from . import wizard

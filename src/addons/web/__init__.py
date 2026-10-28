# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.modules.module import runtime_role_enabled

if runtime_role_enabled('http'):
    from . import controllers
from . import models

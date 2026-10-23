def migrate(cr, version):
    """Remove publisher telemetry left by earlier mail versions."""
    cr.execute("""
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'mail'
           AND name = 'ir_cron_module_update_notification'
           AND model = 'ir.cron'
    """)
    row = cr.fetchone()
    if not row:
        return

    cr.execute("SELECT ir_actions_server_id FROM ir_cron WHERE id = %s", row)
    action = cr.fetchone()
    cr.execute("DELETE FROM ir_cron WHERE id = %s", row)
    if action:
        cr.execute("DELETE FROM ir_act_server WHERE id = %s", action)
        cr.execute("DELETE FROM ir_actions WHERE id = %s", action)
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'mail'
           AND name IN (
               'ir_cron_module_update_notification',
               'ir_cron_module_update_notification_ir_actions_server'
           )
    """)

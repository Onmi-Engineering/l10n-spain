# Copyright 2026 ACCON (migración invermed v15 -> 19)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
"""Pre-migrate: limpia datos de referencia v15 que chocan con los CSV v19.

l10n_es_aeat es la dependencia común de todos los módulos mod1xx (111, 115,
123, 303, 347, 349, 390) y de l10n_es_aeat_sii_oca, así que corre ANTES que
cualquiera de ellos cargue sus propios datos -- el lugar correcto para
limpiar de una vez lo que rompe la carga en cascada.

MTEPRETTI: ver migration_v19/HANDOFF.md items 6, 7, 9, 19 del repo invermed
para el detalle de cada uno de estos tres problemas.
"""


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return cr.fetchone()[0] is not None


def migrate(cr, version):
    # (1) mapas AEAT que solapan entre datos v15 y los CSV v19 (choca al
    # cargar cualquier mod1xx, ej. mod123: "The dates of the record overlap
    # with an existing record."). Se chequea que cada tabla exista antes de
    # tocarla: el pre-migrate corre ANTES de que Odoo cree/actualice el
    # esquema, así que alguna de estas puede no existir todavía en esta
    # base puntual (ej. si es una tabla nueva de v19 o si nunca se llegó a
    # crear en v15 por no tener datos).
    for table in (
        "l10n_es_aeat_map_tax_line_tax",
        "l10n_es_aeat_map_tax_line",
        "l10n_es_aeat_map_tax",
    ):
        if _table_exists(cr, table):
            cr.execute("DELETE FROM %s" % table)  # noqa: S608 (nombre fijo, no input externo)

    cr.execute(
        """
        DELETE FROM ir_model_data WHERE model IN (
            'l10n.es.aeat.map.tax',
            'l10n.es.aeat.map.tax.line',
            'l10n.es.aeat.map.tax.line.tax'
        );
        """
    )

    # (2) res_partner.not_in_mod347 (boolean v15 -> jsonb company_dependent
    # en v19, vía l10n_es_aeat_mod347). Sin partners marcados True en el
    # momento de escribir esto; si eso cambiara, habría que respaldar antes
    # de dropear (ver migration_v19/03_snapshot_not_in_mod347.sql).
    cr.execute("ALTER TABLE res_partner DROP COLUMN IF EXISTS not_in_mod347;")

    # (3) vistas que referencian el campo eliminado invoice_jobs_ids
    # (desapareció de l10n_es_aeat_sii_oca en v19).
    cr.execute(
        """
        DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN (
            SELECT id FROM ir_ui_view WHERE arch_db::text LIKE '%invoice_jobs_ids%'
        );
        DELETE FROM ir_ui_view WHERE arch_db::text LIKE '%invoice_jobs_ids%';
        """
    )

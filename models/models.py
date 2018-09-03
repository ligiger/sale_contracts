# -*- coding: utf-8 -*-

from odoo import models, fields, api

# Definition von Mengenkontrakt -----------------------------
class kontrakt_kontrakt(models.Model):
    _name = 'kontrakt.kontrakt'

    name = fields.Char()
    date_create = fields.Datetime('Erstelldatum', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")
    
    date_accepted = fields.Datetime('Bestätigt am:', readonly="true")
    accepted_by = fields.Many2one('res.users', string="Bestätigt durch", readonly="true")

    product_id = fields.Many2one('product.product', string="Produkt", required="true", index=True)

    abrufe = fields.Many2many('kontrakt.abruf', 'kontrakt_abruf_rel', 'kontrakt_kontrakt_id', 'kontrakt_abruf_id', string='Abrufe', copy=False)

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('confirmed', 'Bestätigt'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft')
    
    description = fields.Html('Beschreibung')
    analysis = fields.Html('Problemanalyse')

    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)

    @api.depends('value')
    def _value_pc(self):
        self.value2 = float(self.value) / 100

    @api.one
    def confirm(self):
        self.write({'state': 'confirmed'})
        self.write({'date_accepted': fields.Datetime.now()})
        #self.write({'accepted_by': self.env.user})

# Definition von Abruf ------------------------------
class kontrakt_abruf(models.Model):
    _name = "kontrakt.abruf"

    @api.one
    def confirm(self):
        self.write({'state': 'active'})    

    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")

    kontrakt_product_id = fields.Many2one('product.product', string="Produkt", readonly="true", index=True)

    positionen = fields.Many2many('kontrakt.position', 'kontrakt_position_rel', 'kontrakt_abruf_id', 'kontrakt_position_id', string='Abrufpositionen', copy=False)

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft')

# Definition von Position ---------------------------
class kontrakt_position(models.Model):
    _name = "kontrakt.position"

    @api.one
    def confirm(self):
        self.write({'state': 'active'})

    name = fields.Char()
    delivery_date = fields.Date('Lieferdatum:', required="true", track_visibility="onchange")
    amount_planned = fields.Integer('Geplante Menge', required="true", track_visibility="onchange")
    amount_done = fields.Integer('Belieferte Menge', tracking="onchange")

    abruf_product_id = fields.Many2one('product.product', string="Produkt", readonly="true", index=True)

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft')
    
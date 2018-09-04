# -*- coding: utf-8 -*-

from collections import defaultdict
import math

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare

# Definition von Mengenkontrakt -----------------------------
class kontrakt_kontrakt(models.Model):
    """ Manufacturing Orders """
    _name = 'kontrakt.kontrakt'
    _description = 'Vertragsverwaltung'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    date_create = fields.Datetime('Erstelldatum', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")
    
    date_accepted = fields.Datetime('Bestätigt am:', readonly="true")
    accepted_by = fields.Many2one('res.users', string="Bestätigt durch", readonly="true")

    product_id = fields.Many2one('product.product', string="Produkt", required="true", index=True, store=True)

    amount_ordered = fields.Integer('Bestellte Menge', required="true", track_visibility="onchange")
    amount_delivered = fields.Integer('Gelieferte Menge', readonly="true")

    abrufe = fields.Many2many('kontrakt.abruf', 'kontrakt_abruf_rel', 'kontrakt_kontrakt_id', 'kontrakt_abruf_id', string='Abrufe', copy=False)

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('confirmed', 'Bestätigt'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft', track_visibility="onchange")
    
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
        self.write({'accepted_by': self.env['res.users'].browse(self.env.uid).id})
    
    @api.one
    def done(self):
        self.write({'state': 'done'})
    
    @api.one
    def edit(self):
        self.write({'state': 'draft'})

# Definition von Abruf ------------------------------
class kontrakt_abruf(models.Model):
    """ Kontrakt Abrufe """
    _name = "kontrakt.abruf"
    _description = 'Abrufe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.one
    def confirm(self):
        self.write({'state': 'active'})
    
    @api.one
    def done(self):
        self.write({'state': 'done'})
    
    @api.one
    def edit(self):
        self.write({'state': 'draft'})

    #@api.model
    #def default_get(self, vals):
    #    context = dict(self.env.context)
    #    contract = context.get('name', False)
    #    print 'contract'    

    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")

    parent_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Kontrakt", index=True, store=True)

    kontrakt_product_id = fields.Many2one('product.product', string="Produkt", index=True, store=True)

    amount_ordered = fields.Integer('Bestellte Menge', required="true", track_visibility="onchange")
    amount_delivered = fields.Integer('Gelieferte Menge', readonly="true")

    positionen = fields.Many2many('kontrakt.position', 'kontrakt_position_rel', 'kontrakt_abruf_id', 'kontrakt_position_id', string='Abrufpositionen', copy=False, track_visibility='onchange')

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft', track_visibility="onchange")

# Definition von Position ---------------------------
class kontrakt_position(models.Model):
    """ Kontrakt Positionen """
    _name = "kontrakt.position"
    _description = 'Positionen'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.one
    def confirm(self):
        self.write({'state': 'active'})
    
    @api.one
    def done(self):
        self.write({'state': 'done'})
    
    @api.one
    def edit(self):
        self.write({'state': 'draft'})

    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now, readonly="true")
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")
    delivery_date = fields.Date('Lieferdatum:', required="true", track_visibility="onchange")
    amount_planned = fields.Integer('Geplante Menge', required="true", track_visibility="onchange")
    amount_done = fields.Integer('Belieferte Menge', track_visibility="onchange")

    abruf_product_id = fields.Many2one('product.product', string="Produkt", index=True, store=True)

    parent_abruf = fields.Many2one('kontrakt.abruf', string="Abruf", index=True, store=True)

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft', track_visibility="onchange")

class Picking(models.Model):
    _inherit = "stock.picking"

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true')

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true') 
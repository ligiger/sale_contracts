# -*- coding: utf-8 -*-

from collections import defaultdict
import math

from odoo import api, fields, exceptions, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare
import xlrd
from xlrd import open_workbook
import os
from os.path import join, dirname, abspath
import datetime

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

    #abrufe = fields.Many2many('kontrakt.abruf', 'kontrakt_abruf_rel', 'kontrakt_kontrakt_id', 'kontrakt_abruf_id', string='Abrufe', copy=False)
    abrufe = fields.One2many('kontrakt.abruf', 'parent_kontrakt', string="Abrufe", copy=False, track_visibility='onchange')

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

    def add_follower_id(self, res_id, model, partner_id):
        follower_id = False
        reg = {
        'res_id': res_id,
        'res_model': model,
        'partner_id': partner_id
        }
        try:
            follower_id = self.env['mail.followers'].create(reg)
        except:
            # This partner is already following this record
            return False
        return follower_id

    def remove_follower_id(self, res_id, model, partner_id):
        env = self.env['mail.followers']
        domain = [('partner_id', '=', partner_id), ('res_id', '=', res_id), ('res_model', '=', model)]
        try:
            env.search(domain).unlink()
            return True
        except:
            # The record was either not found, or the unlink operation was not allowed by the current user
            return False

    #@api.model
    #def default_get(self, vals):
    #    context = dict(self.env.context)
    #    contract = context.get('name', False)
    #    print 'contract'    

    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")

    parent_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Kontrakt", index=True, store=True, readonly="true")

    kontrakt_product_id = fields.Many2one(related='parent_kontrakt.product_id', string="Produkt", readonly="true")

    amount_ordered = fields.Integer('Bestellte Menge', required="true", track_visibility="onchange")
    amount_delivered = fields.Integer('Gelieferte Menge', readonly="true")

    #positionen = fields.Many2many('kontrakt.position', 'kontrakt_position_rel', 'kontrakt_abruf_id', 'kontrakt_position_id', string='Abrufpositionen', copy=False, track_visibility='onchange')
    positionen = fields.One2many('kontrakt.position', 'parent_abruf', string="Abrufpositionen", copy=False, track_visibility='onchange')

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
    
    @api.onchange('amount_done')
    def on_change_amount_done(self):
        for record in self:
            if record.amount_done == record.amount_planned and record.state== 'active':
                record.state = 'done'
                record.amount_done = record.amount_planned
            #print self.state

    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now, readonly="true")
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")
    delivery_date = fields.Date('Lieferdatum:', required="true", track_visibility="onchange")
    amount_planned = fields.Integer('Geplante Menge', required="true", track_visibility="onchange")
    amount_done = fields.Integer('Belieferte Menge', track_visibility="onchange", store=True)


    parent_abruf = fields.Many2one('kontrakt.abruf', string="Abruf", index=True, store=True, readonly="true")
    abruf_product_id = fields.Many2one(related='parent_abruf.kontrakt_product_id', string="Produkt", readonly="true")

    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='draft', track_visibility="onchange")

class spediteur(models.Model):
    """ Spediteure """
    _name = "spediteur"
    _description = 'Speditionen'

    name = fields.Char(string="Name der Spedition")
    abholung = fields.Boolean(string="Abholung")


class forecast(models.Model):
    """ Lieferforecast """
    _name = "forecast"
    _description = 'Lieferforecast'

    _sql_constraints = [
        ('bestellung_key_unique', 
        'unique(bestellung,position,due_date)',
        'Die Bestellung ist nicht Einzigartig!')
    ]

    bestellung = fields.Char(string="Bestellung")
    position = fields.Char(string="Position")
    lieferant = fields.Char(string="Lieferant")
    art_nr = fields.Char(string="Artikelnummer")
    art_name = fields.Char(string="Artikelname")
    due_date = fields.Date(string="Zieldatum")
    menge_bestellt = fields.Integer(string="Menge Bestellt")
    menge_erhalten = fields.Integer(string="Menge Erhalten (VMS)")
    current_date = fields.Date(string="Current Time", default= fields.datetime.now())
    creation_date = fields.Date(string="Creation date", default= fields.datetime.now())
    bemerkungen = fields.Html(string="Bemerkung")

    state = fields.Selection([
        ('new', 'Neu'),
        ('wait', 'Warteschlange'),
        ('done', 'Abgeschlossen'),
        ('deleted', 'Gelöscht'),
        ], default='wait', track_visibility="onchange")

    @api.multi
    def write(self, values):
        if values.get('menge_erhalten') == self.menge_bestellt:
            #raise UserError("Neu:")
            values['state'] = 'done'

        return super(forecast, self).write(values)

    @api.multi
    def check_updates(self):
        #it is meta object of ir.attachment
        #file_obj = self.session.pool.get('impexp.file')
        #f = file_obj.browse(self.session.cr, self.session.uid, file_id)
        #data_file = b64decode(f.attachment_id.datas)
        #raise exceptions.ValidationError("Error! Panel")
        filepath = r'C:\Users\Admin\Desktop\Terminliste\Kopie_LGI.xlsx'
        #a_dir = 'C:/Users/Admin/Desktop/Terminliste'
        new = 0
        deleted = 0

        wb = open_workbook(filepath)
        #sheet = wb.sheet_by_index(1)
        for sheet in wb.sheets():
            data = [[0 for x in range(sheet.ncols)] for y in range(sheet.nrows)] 
            for row in xrange(2, sheet.nrows):
                #data_row = []
                for col in range(sheet.ncols):
                    value = (sheet.cell(row, col).value)
                    #data_row.append(value)
                    data[row][col] = value
                '''date_float = data_row[6]
                bestellung = int(data_row[0])
                position = int(data_row[1])
                duedate = datetime.datetime(*xlrd.xldate_as_tuple(data_row[6], wb.datemode))

                if self.search_count([('bestellung', '=', bestellung),('position', '=', position),('due_date', '=', duedate)]) == 0:
                    new = new + 1
                    
                    #raise UserError(duedate)
                    dataset = {
                                'bestellung' : bestellung,
                                'position' : position,
                                'lieferant' : data_row[2],
                                'art_nr' : data_row[3],
                                'art_name' : data_row[5],
                                'due_date' : duedate,
                                'menge_bestellt' : data_row[7],
                            }
                    self.env['forecast'].create(dataset)
                    self.env.cr.commit()'''

            for zeile in xrange(2, sheet.nrows):
                date_float = data[zeile][6]
                bestellung = int(data[zeile][0])
                position = int(data[zeile][1])
                duedate = datetime.datetime(*xlrd.xldate_as_tuple(date_float, wb.datemode))

                if self.search_count([('bestellung', '=', bestellung),('position', '=', position),('due_date', '=', duedate)]) == 0:
                    dataset = {
                                'bestellung' : bestellung,
                                'position' : position,
                                'lieferant' : data[zeile][2],
                                'art_nr' : data[zeile][3],
                                'art_name' : data[zeile][5],
                                'due_date' : duedate,
                                'menge_bestellt' : data[zeile][7],
                                'state' : 'new',
                            }
                    new = new + 1
                    self.env['forecast'].create(dataset)
                    self.env.cr.commit()

            records = self.env['forecast'].search([])
            rec = 0

            for record in records:
                rec_bestellung = record.bestellung
                rec_position = record.position
                rec_date = record.due_date
                found = False
                rec = rec+1
                record.write({'current_date' : fields.datetime.now()})
                self.env.cr.commit()

                for zeile in xrange(2, sheet.nrows):
                    date_float = data[zeile][6]
                    bestellung = int(data[zeile][0])
                    position = int(data[zeile][1])
                    duedate = datetime.datetime(*xlrd.xldate_as_tuple(date_float, wb.datemode)).date()

                    #raise UserError(zeile)
                    #raise UserError("%s, " % bestellung + "%s, " % position + "%s\n" % duedate + "%s, " %rec_bestellung + "%s, " % rec_position + "%s" % rec_date) 
                    #if (rec_bestellung == bestellung) and (rec_position == position) and (rec_date == duedate):
                    if rec_bestellung == str(bestellung) and rec_position == str(position) and rec_date == str(duedate) and self.state !='wait':
                        #raise UserError("%s, " % bestellung + "%s, " % position + "%s\n" % duedate + "%s, " %rec_bestellung + "%s, " % rec_position + "%s" % rec_date)
                        found = True
                        if record.state == 'new':
                            record.write({'state': 'wait'})
                            self.env.cr.commit()

                if found == False and record.state =='wait':
                    record.write({'state': 'deleted'})
                    #self.search([('id', '=', record.id)]).write({'state': 'deleted'})
                    self.env.cr.commit()
                    deleted = deleted + 1

        #raise UserError(data)           
        raise UserError("Neu: %s" % new + " Deleted: %s" % deleted + "Recs Walked: %s" %rec)

class Picking(models.Model):
    _inherit = "stock.picking"

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true')
    geag_spediteur = fields.Many2one('spediteur', string="Spedition")
    geag_wird_abgeholt = fields.Boolean(string="Wird abgeholt", related='geag_spediteur.abholung', readonly='true')

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true') 
'''
    @api.multi
    def write(self, vals):
        res = super(MrpProduction, self).write(vals) # Save the form
        stage_followers = self.env['mymodule.stage_followers'].search([('stage', '=', self.state)])
        anz = 0
        for i in stage_followers:
            #self.add_follower_id(self, 'kontrakt.abruf', i['user'])
            reg = {
                'res_id': self.id,
                'res_model': 'mrp.production',
                'partner_id': i['user'].id
            }
            try:
                follower_id = self.env['mail.followers'].create(reg)
                raise UserError('OK')
            except:
                # This partner is already following this record
            #    raise UserError('FAIL')
                return False
            anz = anz + 1
        # Message posting is optional. Add_follower_id will still make the partner follow the record
        #raise UserError(anz)
        messages = "Whatever you want to put in the message box."
        if messages:
            self.message_post(body=messages, partner_ids=self.message_follower_ids)
        return res
'''
'''
class stage_followers(models.Model):
    _name = 'mymodule.stage_followers'
    user = fields.Many2one('res.partner', required=True, string='User')
    beschreibung = fields.Char("Beschreibung")
    stage = fields.Selection(selection=[('draft', 'Entwurf'),
        ('active', 'Aktiv'),
        ('confirmed','Bestätigt'),
        ('done', 'Abgeschlossen'),
        ('cancel', 'Abgebrochen'),
        ], default='initial', string='Stage')
'''
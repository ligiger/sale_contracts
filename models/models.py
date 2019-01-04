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
import shutil

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

    @api.one
    def refresh(self):
        zahl = 0
        for position in self.abrufe:
            zahl = zahl + position.amount_delivered
        self.write({'amount_delivered': zahl})

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

    #new task 12.12.2018
    @api.one
    def refresh(self):
        zahl = 0
        for position in self.positionen:
            zahl = zahl + position.amount_done
        self.write({'amount_delivered': zahl})

    @api.multi
    def write(self, values):
        if values.get('amount_delivered') == self.amount_ordered and self.state != 'draft':
            #raise UserError("Neu:")
            values['state'] = 'done'

        return super(kontrakt_abruf, self).write(values)

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
    
    # work to do here!!
    @api.multi
    def write(self, values):
        if values.get('amount_done') == self.amount_planned and self.state != 'draft':
            #raise UserError("Neu:")
            values['state'] = 'done'

        return super(kontrakt_position, self).write(values)

    #@api.onchange('amount_done')
    #def close_item(self, values):
    #    done = values.get('amount_done')
    #    if self.state != 'draft' and self.amount_planned == self.amount_done:  
    #        self.state = 'done'
    #        raise UserError(done)
    #        self.amount_done = self.def_delivered
                #record.state = 'done'


    name = fields.Char()
    create_date = fields.Datetime('Erstelldatum', default=fields.Datetime.now, readonly="true")
    created_by = fields.Many2one('res.users', string="Erstellt durch", default=lambda self: self.env.user, readonly="true")
    delivery_date = fields.Date('Lieferdatum:', required="true", track_visibility="onchange")
    amount_planned = fields.Integer('Geplante Menge', required="true", track_visibility="onchange")
    amount_done = fields.Integer('Belieferte Menge', track_visibility="onchange")
    def_delivered = fields.Integer('Gelieferte Menge', readonly="true", store= True, track_visibility="onchange")


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
    current_date = fields.Date(string="Current Date", default= fields.datetime.now())
    creation_date = fields.Date(string="Creation date", default= fields.datetime.now())
    bemerkungen = fields.Html(string="Bemerkung")
    days_due = fields.Integer(string="Days Overdue")

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
    def update_time(self):
        records = self.env['forecast'].search([])
        
        result=[]
        for record in records:
            record.write({'current_date' : fields.datetime.now()})
            self.env.cr.commit()
            chkin_dt = datetime.datetime.strptime(record.due_date, '%Y-%m-%d')
            chkout_dt = datetime.datetime.strptime(record.current_date, '%Y-%m-%d')
            duedays = chkout_dt - chkin_dt
            record.write({'days_due' : duedays.days})
            self.env.cr.commit()
        return result

    @api.multi
    def name_get(self):
        result=[]
        for record in self:
            name = '%s-%s-%s' % (record.bestellung ,record.position, record.due_date)
            result.append((record.id, name))
        return result

    @api.multi
    def check_updates(self):
        #it is meta object of ir.attachment
        #file_obj = self.session.pool.get('impexp.file')
        #f = file_obj.browse(self.session.cr, self.session.uid, file_id)
        #data_file = b64decode(f.attachment_id.datas)
        #raise exceptions.ValidationError("Error! Panel")
        #filepath = r'C:\Users\Admin\Desktop\Terminliste\Kopie_LGI.xlsx'
        #a_dir = r'O:\B10. Prozessdaten\B_Kernprozesse\3_Auftragsplanung\VMS Lieferforecast\Terminliste\neu'
        #dest_folder = r'O:\B10. Prozessdaten\B_Kernprozesse\3_Auftragsplanung\VMS Lieferforecast\Terminliste\done'
        a_dir = r'C:\Users\Admin\Desktop\Terminliste\neu'
        dest_folder = r'C:\Users\Admin\Desktop\Terminliste\done'
        new = 0
        deleted = 0
        rec = 0

        for filename in os.listdir(a_dir):
            filepath = os.path.join(a_dir, filename)
            dest_path = os.path.join(dest_folder, filename)

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

            wb.release_resources()
            shutil.move(filepath, dest_path)  
        self.update_time()
        raise UserError("Neu: %s" % new + " Deleted: %s" % deleted + "Recs Walked: %s" %rec)

class Picking(models.Model):
    _inherit = "stock.picking"

    geag_forecast_item = fields.Many2one('forecast', string="Geplante Lieferung")
    geag_forecast_bestellung = fields.Char (string="Bestellnummer", store=True, related='geag_forecast_item.bestellung', readonly='true')
    geag_forecast_position = fields.Char(string="Position", store=True, related='geag_forecast_item.position', readonly='true')
    geag_forecast_lieferant = fields.Char(string="Lieferant", store=True, related='geag_forecast_item.lieferant', readonly='true')
    geag_forecast_plandatum = fields.Date(string="Plandatum", store=True, related='geag_forecast_item.due_date', readonly='true')

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true')
    geag_spediteur = fields.Many2one('spediteur', string="Spedition")
    geag_wird_abgeholt = fields.Boolean(string="Wird abgeholt", related='geag_spediteur.abholung', readonly='true')

    geag_migo_nr = fields.Char(string="Migo Nummer")
    geag_sap_ok = fields.Boolean(string="SAP gebucht")
    geag_operator = fields.Many2one('res.users', string="Sachbearbeiter", default=lambda self: self.env.user)
    geag_notes = fields.Html(string="Bemerkungen")

    geag_typ = fields.Selection([
        ('std', 'VMS Standard'),
        ('special', 'Allgemein'),
        ], string="Auftragstyp", default='std', track_visibility="onchange")

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    geag_kontrakt = fields.Many2one('kontrakt.kontrakt', string="Mengenkontrakt")
    geag_abruf = fields.Many2one('kontrakt.abruf', string="Abruf")
    geag_position = fields.Many2one('kontrakt.position', string="Position")
    geag_delivery_date = fields.Date(string="Lieferdatum", store=True, related='geag_position.delivery_date', readonly='true')

    product_dmr = fields.Many2one('dmr', string="Device Master Record", required=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    checked_date = fields.Datetime('Geprüft am', readonly = True)
    checked_by = fields.Many2one('res.users', string="Geprüft durch", readonly = True)
    spec_notes = fields.Text('Spezielle Bedingungen')

    @api.one
    def validate(self):
        self.write({'checked_date': fields.Datetime.now()})
        self.write({'checked_by': self.env['res.users'].browse(self.env.uid).id})

    @api.multi
    def sales_number_update(self):
        #sequence_obj = self.pool.get('ir.sequence')
        seq_id = self.env['ir.sequence'].search([('code', '=', 'sale.order')])         
        if seq_id:
            seq_id.write({'number_next': 1})
        return None

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    geag_pos = fields.Integer('Position')

class DeviceMasterRecord(models.Model):
    """Device Master Records"""
    _name = "dmr"

    name = fields.Char(string="Name")
    version = fields.Char(string="Version")

    date_create = fields.Datetime('Erstelldatum', readonly=True)
    created_by = fields.Many2one('res.users', string="Erstellt durch", readonly="true")
    
    date_validiert = fields.Datetime('Validiert am:', readonly="true")
    validiert_by = fields.Many2one('res.users', string="Validiert durch", readonly="true")

    date_obsolete = fields.Datetime('Obsolet am:', readonly="true")
    obsolete_by = fields.Many2one('res.users', string="Obsolidiert durch", readonly="true")

    product_id = fields.Many2one('product.product', string="Produkt", required="true", index=True, store=True)

    #dokumente = fields.One2many('ir.attachment', 'res_model', string="Mitgeltende Dokumente", copy=True, track_visibility='onchange')
    dokumente = fields.Many2many('ir.attachment', 'dmr_document_rel', 'dmr_id', 'ir_attachment_id', string='Mitgeltende Dokumente', copy=True, track_visibility='onchange')

    
    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('erstellt', 'Erstellt'),
        ('valid', 'Validiert'),
        ('cancel', 'Obsolet'),
        ], default='draft', track_visibility="onchange")

    @api.one
    def confirm(self):
        self.write({'state': 'erstellt'})
        self.write({'date_create': fields.Datetime.now()})
        self.write({'created_by': self.env['res.users'].browse(self.env.uid).id})

    @api.one
    def validate(self):
        self.write({'state': 'valid'})
        self.write({'date_validiert': fields.Datetime.now()})
        self.write({'validiert_by': self.env['res.users'].browse(self.env.uid).id})
    
    @api.one
    def obsolete(self):
        self.write({'state': 'cancel'})
        self.write({'date_obsolete': fields.Datetime.now()})
        self.write({'obsolete_by': self.env['res.users'].browse(self.env.uid).id})
    
    @api.multi
    def name_get(self):
        result=[]
        for record in self:
            name = '[%s] - %s' % (record.version ,record.name)
            result.append((record.id, name))
        return result

class DMRDocument(models.Model):
    """Device Master Record Document"""
    _name = "dmr.document"

    name = fields.Char(string="Name")
    version = fields.Char(string="Version")
    product_id = fields.Many2one('product.product', string="Produkt", required="true", index=True, store=True)
    document = fields.Binary(string="Document")

class IrAttachment(models.Model):

    _inherit = 'ir.attachment'

    version = fields.Char(string="Version")
    #product_id = fields.Many2one('product.product', string="Produkt", required="true", index=True, store=True)
    product_id = fields.Many2many('product.product', 'attachment_product_rel', 'attachment_id', 'product_id', string='Relevante Produkte', copy=True)
    geag_sequence = fields.Integer()



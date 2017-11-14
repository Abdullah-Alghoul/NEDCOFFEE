# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import time
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
from openerp import netsvc

class report_mrp_planning(osv.osv_memory):
    _name = 'report.mrp.planning'
    _columns = {
              'workcenter_id': fields.many2one('mrp.workcenter', 'Nguồn Lưc Tham Gia', required=True),
              'from_date': fields.datetime('Từ Ngày(Giờ)', required=True),
              'to_date': fields.datetime('Đến Ngày(Giờ)', required=True),
              'congdoan_id': fields.many2one('mrp.congdoan', 'Công Đoạn', required=True),
              'congdoan': fields.selection([
                ('thoi', 'Thổi'),
                ('chia', 'Chia'),
                ('ghep', 'Ghép'),
                ('in', 'In'),
                ('tui', 'Làm túi')], 'Công đoạn'),
              }
    _defaults = { 
        'from_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'to_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }      
    
    def onchange_condgoan(self, cr, uid, ids, workcenter_id, context=None):
        if not workcenter_id:
            return
        workcenter_obj = self.pool.get('mrp.workcenter').browse(cr, uid, workcenter_id)
        return {'value': {'congdoan': workcenter_obj.type}}
    
    def onchange_workcenter(self, cr, uid, ids, congdoan_id, workcenter_id, context=None):
        domain = {}
        congdoan_obj = self.pool.get('mrp.congdoan').browse(cr, uid, congdoan_id)
        if congdoan_obj.type == 'in':
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('type', '=', 'in')])
            if workcenter_ids:
                domain.update({'workcenter_id':[('id', '=', workcenter_ids)]})
        if congdoan_obj.type in ('ghep', 'ghep2', 'ghep3', 'ghep4'):
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('type', '=', 'ghep')])
            if workcenter_ids:
                domain.update({'workcenter_id':[('id', '=', workcenter_ids)]})
        if congdoan_obj.type == 'chia':
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('type', '=', 'chia')])
            if workcenter_ids:
                domain.update({'workcenter_id':[('id', '=', workcenter_ids)]})
        if congdoan_obj.type == 'tui':
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('type', '=', 'tui')])
            if workcenter_ids:
                domain.update({'workcenter_id':[('id', '=', workcenter_ids)]})
        if congdoan_obj.type == 'thoi':
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('type', '=', 'thoi')])
            if workcenter_ids:
                domain.update({'workcenter_id':[('id', '=', workcenter_ids)]})
        return {'domain':domain}
    
    def print_inphieu(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'report.mrp.planning'
        datas['form'] = self.read(cr, uid, ids)[0]
        congdoan = datas['form'] and datas['form']['congdoan']
        if congdoan and congdoan == 'thoi':
            report_name = 'trapaco_report_khsx_cd_thoi'
        if congdoan and congdoan == 'chia':
            report_name = 'trapaco_report_khsx_cd_chia'
        if congdoan and congdoan == 'in':
           report_name = 'trapaco_report_khsx_cd_in'
        if congdoan and congdoan == 'ghep':
            report_name = 'trapaco_report_khsx_cd_ghep'
        if congdoan and congdoan == 'tui':
            report_name = 'trapaco_report_khsx_cd_tui'
        return {'type': 'ir.actions.report.xml', 'report_name': report_name , 'datas': datas} 

report_mrp_planning()

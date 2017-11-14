# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models, tools
from lxml import etree

# class RecruitmentSource(models.Model):
#     _inherit = "hr.recruitment.source"
#     
#     quizz_score = fields.Float(related='response_id.quizz_score', string="Score", readonly=True)

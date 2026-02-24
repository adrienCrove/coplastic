# -*- coding: utf-8 -*-
# from odoo import http


# class CoplasticReport(http.Controller):
#     @http.route('/coplastic_report/coplastic_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/coplastic_report/coplastic_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('coplastic_report.listing', {
#             'root': '/coplastic_report/coplastic_report',
#             'objects': http.request.env['coplastic_report.coplastic_report'].search([]),
#         })

#     @http.route('/coplastic_report/coplastic_report/objects/<model("coplastic_report.coplastic_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('coplastic_report.object', {
#             'object': obj
#         })


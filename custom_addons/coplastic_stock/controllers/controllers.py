# -*- coding: utf-8 -*-
# from odoo import http


# class CoplasticStock(http.Controller):
#     @http.route('/coplastic_stock/coplastic_stock', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/coplastic_stock/coplastic_stock/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('coplastic_stock.listing', {
#             'root': '/coplastic_stock/coplastic_stock',
#             'objects': http.request.env['coplastic_stock.coplastic_stock'].search([]),
#         })

#     @http.route('/coplastic_stock/coplastic_stock/objects/<model("coplastic_stock.coplastic_stock"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('coplastic_stock.object', {
#             'object': obj
#         })


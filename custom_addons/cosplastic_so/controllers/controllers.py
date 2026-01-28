# -*- coding: utf-8 -*-
# from odoo import http


# class CosplasticSo(http.Controller):
#     @http.route('/cosplastic_so/cosplastic_so', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cosplastic_so/cosplastic_so/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('cosplastic_so.listing', {
#             'root': '/cosplastic_so/cosplastic_so',
#             'objects': http.request.env['cosplastic_so.cosplastic_so'].search([]),
#         })

#     @http.route('/cosplastic_so/cosplastic_so/objects/<model("cosplastic_so.cosplastic_so"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cosplastic_so.object', {
#             'object': obj
#         })


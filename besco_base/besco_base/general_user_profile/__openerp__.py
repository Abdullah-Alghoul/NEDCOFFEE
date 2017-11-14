# -*- coding: utf-8 -*-

{
    "name" : "User Profile Integration",
    "version" : "0.1",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    "category": 'General 80',
    "description": """
        Integrates the profile management to the current relationship
            between users and groups.
    """,
    'website': 'http://www.letruongthanh.com',
    'init_xml': [],
    "depends" : ["base",'properties'],
    'data': [
                   "security/syn_user_profile_security.xml",
                   "property_data.xml",
                   "profile_view.xml",
                   'wizard/update_profile.xml',
    ],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'active': False,
#    'post_objects': ['post.user.profile'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

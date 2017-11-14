.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Multicurrency revaluation
=========================

This module was written to extend the functionality of the accounting module to
support the multicurrency.

Installation
============

To install this module, you need to:

* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Multicurrency revaluation" in your addons
* install the module

Configuration
=============

Due to the various legislation according the country, in the Company settings
you can set the way you want to generate revaluation journal entries.

The user that can access to the edition of the 'Provision B.S loss account' and
'Provision P&L accounts' need to be in the security group
'Additional provisioning entries posting'.

You also need to tick the box "Allow multi currencies" in the menu Settings/
Configuration/ Invoicing to be able to select the currency on the account you
want to revaluate.

Please, find below advised account settings for 3 countries:

For UK (Revaluation)
--------------------
(l10n_uk Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [7700]  [7700]
  Provision B.S account  [    ]  [    ]
  Provision P&L account  [    ]  [    ]

For CH (Provision)
------------------
(l10n_ch Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [    ]  [    ]
  Provision B.S account  [2331]  [2331]
  Provision P&L account  [3906]  [4906]

For FR
------
(l10n_fr Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [ 476]  [ 477]
  Provision B.S account  [1515]  [    ]
  Provision P&L account  [6865]  [    ]

Usage
=====

The *Multicurrency revaluation* module allows you generate automatically
multicurrency revaluation journal entries.

Main Features
-------------

* A checkbox *Allow currency revaluation* on accounts.
* A wizard to generate the revaluation journal entries. It adjusts account
balance having *Allow currency revaluation* checked.


Credits
=======

Contributors
------------

* Le Truong Thanh (thanh.lt@besco.vn)


Maintainer
----------

.. image:: http://besco.vn/logo.png
   :target: http://besco.vn

This module is maintained by the BESCO Consulting.

#!/usr/bin/env python2

# python setup.py sdist --format=zip,gztar

from setuptools import setup
import os
import sys
import platform
import imp
import argparse

version = imp.load_source('version', 'lib/version.py')

if sys.version_info[:3] < (2, 7, 0):
    sys.exit("Error: Electrum requires Python version >= 2.7.0...")

data_files = []

if platform.system() in ['Linux', 'FreeBSD', 'DragonFly']:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root=', dest='root_path', metavar='dir', default='/')
    opts, _ = parser.parse_known_args(sys.argv[1:])
    usr_share = os.path.join(sys.prefix, "share")
    if not os.access(opts.root_path + usr_share, os.W_OK) and \
       not os.access(opts.root_path, os.W_OK):
        if 'XDG_DATA_HOME' in os.environ.keys():
            usr_share = os.environ['XDG_DATA_HOME']
        else:
            usr_share = os.path.expanduser('~/.local/share')
    data_files += [
        (os.path.join(usr_share, 'applications/'), ['electrum-twist.desktop']),
        (os.path.join(usr_share, 'pixmaps/'), ['icons/electrum-twist.png'])
    ]

setup(
    name="Electrum-twist",
    version=version.ELECTRUM_VERSION,
    install_requires=[
        'slowaes>=0.1a1',
        'ecdsa>=0.9',
        'pbkdf2',
        'requests',
        'qrcode',
        'protobuf',
        'dnspython',
        'jsonrpclib',
    ],
    packages=[
        'electrum_twist',
        'electrum_twist_gui',
        'electrum_twist_gui.qt',
        'electrum_twist_plugins',
        'electrum_twist_plugins.audio_modem',
        'electrum_twist_plugins.cosigner_pool',
        'electrum_twist_plugins.email_requests',
        'electrum_twist_plugins.exchange_rate',
        'electrum_twist_plugins.hw_wallet',
        'electrum_twist_plugins.keepkey',
        'electrum_twist_plugins.labels',
        'electrum_twist_plugins.ledger',
        'electrum_twist_plugins.plot',
        'electrum_twist_plugins.trezor',
        'electrum_twist_plugins.virtualkeyboard',
    ],
    package_dir={
        'electrum_twist': 'lib',
        'electrum_twist_gui': 'gui',
        'electrum_twist_plugins': 'plugins',
    },
    package_data={
        'electrum_twist': [
            'www/index.html',
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/electrum.mo',
        ]
    },
    scripts=['electrum-twist'],
    data_files=data_files,
    description="Lightweight twist Wallet",
    author="TWISTproject",
    license="MIT Licence",
    url="https://twist.network",
    long_description="""Lightweight twist Wallet"""
)

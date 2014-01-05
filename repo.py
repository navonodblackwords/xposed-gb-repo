#!/usr/bin/env python
#fileencoding: utf-8
#Author: Liu DongMiao <liudongmiao@gmail.com>
#Created  : TIMESTAMP
#Modified : TIMESTAMP

import os
import gzip
import json
import time
import urllib
from hashlib import md5
from xml.dom import minidom

TMPDIR = '/tmp'
# path for downloaed xposed module
XPOSED = '/tmp/xposed'
# path for aapt binary
AAPT = '/home/thom/bin/aapt'
# path ofr web directory
WEBDIR = '/var/www/piebridge'
# path for http url
HTTP = 'http://piebridge.me/'
# original repo.xml.gz
REPO_XML_GZ = 'http://dl.xposed.info/repo.xml.gz'

BACKPORTED = (
    'biz.bokhorst.xprivacy',
    'de.robv.android.xposed.installer',
    'de.robv.android.xposed.mods.appsettings',
    'uk.co.villainrom.pulser.allowlongsms',
)

REPLACE = (
    ('github.com/M66B/XPrivacy', 'github.com/liudongmiao/XPrivacy'),
    ('github.com/rovo89/XposedInstaller', 'github.com/liudongmiao/XposedInstaller'),
    ('github.com/rovo89/XposedAppSettings', 'github.com/liudongmiao/XposedAppSettings'),
)

def get_nodes_value(node, key):
    raise BaseException("not support")

def get_node_value(node, key):
    values = node.getElementsByTagName(key)
    if not values.length:
        return None
    elif values.length == 1:
        value = values[0]
        if not value.hasChildNodes() or len(value.childNodes) == 0:
            return None
        elif len(value.childNodes) > 1:
            raise BaseException("not support")
        else:
            return value.firstChild.nodeValue
    else:
        return get_nodes_value(node, key)

def get_apk(download, md5sum):
    if not download or not md5sum:
        return None

    basename = os.path.join(XPOSED, os.path.basename(download))
    if os.path.isfile(basename):
        if md5sum != md5(open(basename, "rb").read()).hexdigest():
            raise SystemExit("md5 fail")
            os.remove(basename)

    if not os.path.isfile(basename):
        urllib.urlretrieve(download, basename)

    if md5sum != md5(open(basename, "rb").read()).hexdigest():
        raise SystemExit("md5 fail")
        os.remove(basename)
        return None

    return basename

def check_sdk(basename):
    sdk = 0
    if not basename or not os.path.isfile(basename):
        return (sdk, {})

    version = {}
    for line in os.popen('%s d badging %s' % (AAPT, basename)).readlines():
        if line.startswith('sdkVersion:'):
            try:
                sdk = int(line.strip()[12:-1])
            except:
                sdk = 0
        elif line.startswith('package:'):
            items = line.split("'")
            while items:
                item = items.pop(0)
                if item.endswith('name='):
                    version['package'] = items.pop(0)
                elif item.endswith('versionCode='):
                    version['code'] = items.pop(0)
                elif item.endswith('versionName='):
                    version['name'] = items.pop(0)

    return (sdk, version)

def check_version(package, code=None):
    if not package:
        return None
    if code:
        code = '_v' + code
    else:
        code = ''
    basename = os.path.join(WEBDIR, package + code + ".apk")
    if not basename or not os.path.isfile(basename):
        return None

    info = basename + ".json"
    mtime = os.stat(basename).st_mtime
    if os.path.isfile(info):
        version = json.loads(open(info).read())
        if version.get('mtime', 0) >= mtime:
            return version

    version = {}
    for line in os.popen('%s d badging %s' % (AAPT, basename)).readlines():
        if line.startswith('application-label:'):
            version['label'] = line.strip()[19:-1]
        elif line.startswith('package:'):
            items = line.split("'")
            while items:
                item = items.pop(0)
                if item.endswith('name='):
                    version['package'] = items.pop(0)
                elif item.endswith('versionCode='):
                    version['code'] = items.pop(0)
                elif item.endswith('versionName='):
                    version['name'] = items.pop(0)

    version['md5sum'] = md5(open(basename, 'rb').read()).hexdigest()
    newpath = '%s_%s.apk' % (basename[:-4], version['md5sum'][:6])
    if os.path.exists(newpath):
        os.remove(newpath)
    os.symlink(os.path.basename(basename), newpath)
    version['download'] = '%s%s' % (HTTP, os.path.basename(newpath))
    version['mtime'] = mtime

    with open(info, 'w') as w:
        w.write(json.dumps(version))

    return version

def remove_node(node, key=None):
    if not key:
        node.parentNode.removeChild(node)
    else:
        for child in node.childNodes:
            if child.nodeName == key:
                child.parentNode.removeChild(child)

def back_ported(doc, module):
    package = module.getAttribute("package")

    # add back-ported author
    authors = get_node_value(module, 'author') + ', liudongmiao(GB)'
    remove_node(module, 'author')
    author = doc.createElement('author')
    author.appendChild(doc.createTextNode(authors))
    module.appendChild(author)

    updated = False
    for child in module.childNodes:
        if child.nodeName != 'version':
            continue
        code = get_node_value(child, 'code')
        if not code:
            child.parentNode.removeChild(child)
            continue
        meta = check_version(package, code)
        if not meta:
            child.parentNode.removeChild(child)
            continue
        if not updated:
            updated = True
            label = meta.get('label')
            if label:
                remove_node(module, 'name')
                name = doc.createElement('name')
                name.appendChild(doc.createTextNode(meta.get('label')))
                module.appendChild(name)
            module.setAttribute("updated", str(int(meta.get('mtime', time.time()))))
        # remove_node(module, 'version')
        # version = doc.createElement('version')
        for tag in ('name', 'code', 'download', 'md5sum'):
            remove_node(child, tag)
            node = doc.createElement(tag)
            node.appendChild(doc.createTextNode(meta.get(tag)))
            child.appendChild(node)
    # module.appendChild(version)

def check_repo():
    repo_xml_gz = os.path.join(TMPDIR, 'repo.xml.gz')
    urllib.urlretrieve(REPO_XML_GZ, repo_xml_gz)
    repoxml = gzip.open(repo_xml_gz, 'rb').read()
    doc = minidom.parseString(repoxml)
    for module in doc.getElementsByTagName("module"):
        package = module.getAttribute("package")
        versions = module.getElementsByTagName("version")
        if not versions:
            module.parentNode.removeChild(module)
            continue
        version = versions[0]
        code = get_node_value(version, "code")
        md5sum = get_node_value(version, "md5sum")
        download = get_node_value(version, "download")
        basename = get_apk(download, md5sum)
        sdk, meta = check_sdk(basename)
        package = meta.get('package', package)
        if sdk > 0 and sdk < 11:
            pass
        elif package in BACKPORTED:
            back_ported(doc, module)
        else:
            module.parentNode.removeChild(module)
        module.setAttribute('package', package)
    doc.normalize()
    content = doc.toxml()
    for x, y in REPLACE:
        content = content.replace(x, y)

    oldpath = os.path.join(TMPDIR, 'repo.gb.xml')
    if os.path.isfile(oldpath):
        oldxml = open(oldpath, 'rb').read()
        if md5(oldxml).hexdigest() == md5(content).hexdigest():
            raise SystemExit()

    with open(oldpath, 'wb') as w:
        w.write(content)

    with open(os.path.join(WEBDIR, 'repo.gb.xml'), 'w') as w:
        w.write(content)

    tmppathgz = os.path.join(TMPDIR, 'repo.gb.xml.gz')
    with gzip.open(tmppathgz, 'wb') as w:
        w.write(content)
    os.rename(tmppathgz, os.path.join(WEBDIR, 'repo.gb.xml.gz'))

check_repo()

# vim: set sta sw=4 et:

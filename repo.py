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

FRAMEWORK = 'de.robv.android.xposed.installer'

BACKPORTED = (
    'biz.bokhorst.xprivacy',
    'de.robv.android.xposed.mods.appsettings',
    'uk.co.villainrom.pulser.allowlongsms',
    'com.gzplanet.xposed.xperiaphonevibrator',
    'de.robv.android.xposed.mods.playstorefix',
    'com.zst.xposed.removeusbstoragewarning',
    # 'com.mohammadag.kitkattoastbackport',
)

REPLACE = (
    ('github.com/M66B/XPrivacy', 'github.com/liudongmiao/XPrivacy'),
    ('github.com/rovo89/XposedInstaller', 'github.com/liudongmiao/XposedInstaller'),
    ('github.com/rovo89/XposedAppSettings', 'github.com/liudongmiao/XposedAppSettings'),
    ('github.com/itandy/xperia_phone_vibrator', 'github.com/liudongmiao/xperia_phone_vibrator'),
    ('github.com/rovo89/AllAppsInPlayStore', 'github.com/liudongmiao/AllAppsInPlayStore'),
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
    if not download:
        return None

    downloadname = os.path.basename(download)
    if not downloadname.endswith(".apk"):
        downloadname = md5(downloadname).hexdigest() + ".apk"

    if not os.path.isdir(XPOSED):
        os.mkdir(XPOSED)
    basename = os.path.join(XPOSED, os.path.basename(downloadname))

    if os.path.isfile('%s.json' % basename):
        # skip md5sum if json file is found
        return basename

    if os.path.isfile(basename):
        if md5sum and md5sum != md5(open(basename, "rb").read()).hexdigest():
            os.remove(basename)

    if not os.path.isfile(basename):
        urllib.urlretrieve(download, basename)

    if md5sum and md5sum != md5(open(basename, "rb").read()).hexdigest():
        os.remove(basename)
        return None

    return basename

def check_sdk(basename):
    sdk = 0
    if not basename or not os.path.isfile(basename):
        return (sdk, {})

    version = {}
    cache = '%s.json' % basename
    if os.path.exists(cache):
        try:
            version = json.loads(open(cache).read())
            return (version['sdk'], version)
        except:
            pass

    for line in os.popen('%s d badging %s' % (AAPT, basename)).readlines():
        if line.startswith('sdkVersion:'):
            try:
                sdk = int(line.strip()[12:-1])
            except:
                sdk = 0
            version['sdk'] = sdk
        elif line.startswith('maxSdkVersion:'):
            try:
                maxsdk = int(line.strip()[15:-1])
            except:
                maxsdk = 0
            version['maxsdk'] = sdk
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

    with open('%s.tmp' % cache, 'w') as w:
        w.write(json.dumps(version))

    os.rename('%s.tmp' % cache, cache);

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
    check_repo_sdk(0)
    check_repo_sdk(10)
    check_repo_sdk(15)
    check_repo_sdk(16)
    check_repo_sdk(17)
    check_repo_sdk(18)
    check_repo_sdk(19)

def check_repo_sdk(api):
    repo_xml_gz = os.path.join(TMPDIR, 'repo.xml.gz')
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
        minsdk, meta = check_sdk(basename)
        package = meta.get('package', package)
        maxsdk = meta.get('maxsdk', 0)
        if package == FRAMEWORK:
            back_ported(doc, module)
        elif api == 0:
            pass
        elif api >= minsdk and (maxsdk == 0 or api <= maxsdk):
            pass
        elif api == 10 and package in BACKPORTED:
            back_ported(doc, module)
        else:
            module.parentNode.removeChild(module)
        module.setAttribute('package', package)
    doc.normalize()
    content = doc.toxml().encode('utf8')
    for x, y in REPLACE:
        content = content.replace(x, y)

    oldpath = os.path.join(TMPDIR, 'repo.%s.xml' % api)
    if os.path.isfile(oldpath):
        oldxml = open(oldpath, 'rb').read()
        if md5(oldxml).hexdigest() == md5(content).hexdigest():
            raise SystemExit()

    with open(oldpath, 'wb') as w:
        w.write(content)

    tmppath = os.path.join(TMPDIR, 'repo.%s.xml.tmp' % api)
    with open(tmppath, 'w') as w:
        w.write(content)
    os.rename(tmppath, os.path.join(WEBDIR, 'repo.%s.xml' % api))

    tmppathgz = os.path.join(TMPDIR, 'repo.%s.xml.gz' % api)
    with gzip.open(tmppathgz, 'wb') as w:
        w.write(content)
    os.rename(tmppathgz, os.path.join(WEBDIR, 'repo.%s.xml.gz' % api))

check_repo()

# vim: set sta sw=4 et:

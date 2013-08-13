# Create your views here.
from os.path import realpath
import requests
import os
import json

from zipfile import ZipFile, ZIP_DEFLATED
from django.http import Http404, HttpResponse

from vpr_content.models import Material, MaterialFile, MaterialExport
from vpr_content.models import listMaterialFiles, MaterialExport
from vpr_content.models import getLatestMaterial, getMaterialLatestVersion
from vpr_content import models

from django.conf import settings

ZIP_HTML_FILE = 'index.html'
MTYPE_MODULE = 1
MTYPE_COLLECTION = 2

def requestMaterialPDF(material):
    """ Create the zip package and post it to vpt in order to 
        receive the PDF genereated.
        After receiving the file exported, an entry of export
        material will be created (as MaterialExport)

    """
    EXPORT_TYPE = 'pdf'

    # prepare the post data
    mzip = open(zipMaterial(material), 'rb')
    payload = {'token': '', 
               'cid': '',
               'output': EXPORT_TYPE}

    export_url = settings.VPT_URL + 'export'
    files = {'file': (mzip.name.split('/')[-1], mzip.read())}

    try:
        res = None
        res = requests.post(export_url, files=files, data={})

        # receive and save to file (PDF)
        if res.status_code == 200:
            export_path = material.material_id + '-' + str(material.version)
            export_path += '.pdf'
            export_path = os.path.join(settings.EXPORT_DIR, export_path)
            with open(export_path, 'wb') as ofile:
                ofile.write(res.content)
                export_path= os.path.realpath(ofile.name)

            # create material export record
            try:
                me_obj = MaterialExport.objects.get(
                    material_id = material.material_id,
                    version     = material.version)
            except:
                me_obj = MaterialExport()
                me_obj.material_id = material.material_id
                me_obj.version = material.version
            me_obj.path = export_path
            me_obj.file_type = EXPORT_TYPE
            me_obj.save()
        else:
            raise
    except:
        import pdb;pdb.set_trace()
        print '[ERR] Exporting to PDF failed. Error occurs when calling the VPT export'
        if res: 
            print '\t' + res.content.replace('\n', '\n\t') + '\n'
    finally:
        # delete the temp ZIP
        mzip.close()
        os.remove(mzip.name) 


def zipMaterial(material):
    """ Collects all material info and put it into a ZIP file.
        Full path of the zip file will be returned to the caller.
    """
    mid = material.material_id
    version = material.version
    mtype = material.material_type
    
    # init the zip package
    zip_path = os.path.join(
        settings.TEMP_DIR,
        'm-'+str(mid)+'-'+str(version)+'.zip'
        )
    zf = ZipFile(zip_path, 'w', ZIP_DEFLATED) 

    # check if module or collection
    if mtype == MTYPE_MODULE:
        # read all material files, and put into the zip package
        mfids = listMaterialFiles(mid, version)
        for mfid in mfids:
            mf = MaterialFile.objects.get(id=mfid)
            zf.writestr(mf.name, mf.mfile.read()) 
            mf.mfile.close()

        # add material text content
        raw_content = material.text
        try:
            raw_content = raw_content.encode('utf-8')
        except:
            raw_content = raw_content.decode('utf-8').encode('utf-8')
        zf.writestr(ZIP_HTML_FILE, raw_content)

    elif mtype == MTYPE_COLLECTION:

        # get list of all contained materials    
        all_materials = getNestedMaterials(material)

        # load materials into ZIP
        for cid in range(len(all_materials)):
            m_id = all_materials[cid][0]
            m_version = all_materials[cid][1]
            m_title = all_materials[cid][2]
            if m_version is None:
                m_version = getMaterialLatestVersion(m_id)
            mfids = listMaterialFiles(m_id, m_version)
            m_object = Material.objects.get(material_id=m_id)
            for mfid in mfids:
                mf = MaterialFile.objects.get(id=mfid)
                zf.writestr(m_id+'/'+mf.name, mf.mfile.read())
                mf.mfile.close()
            zf.writestr(m_id+'/'+ZIP_HTML_FILE, m_object.text)

        # generate chapters.txt
        try:
            index_content = eval(material.text)
            index_content.id = material.material_id
            index_content.title = material.title
        except:
            # another way
            index_content = '{"id":"%s", "title":"%s",' % (material.material_id, material.title)
            index_content += material.text[material.text.index('{')+1:]
        zf.writestr('collection.json', index_content)

        # generate collection json file
        
    zf.close()
    return realpath(zf.filename)


def getNestedMaterials(material):
    """Returns list of material IDs of children inside collection material"""
    materials = []
    try:
        # get all material IDs and versions
        nodes = eval(material.text)['content']
        for node in nodes:
            materials.extend(extractMaterialInfo(node))
    except:
        pass
    return materials
    

def extractMaterialInfo(node):
    """(recursively) Returns material IDs and version found"""
    found = []
    try:
        # extract current node
        mid = node['id']
        mver = node.get('version', None)
        mtitle = node['title']
        found.append((mid, mver, mtitle))

        # extract child nodes
        if node.get('content', []):
            for child_node in node['children']:
                found.extend(extractMaterialInfo(child_node))
    except:
        # where is the error?
        print "Error when getting collection modules"
        pass
    return found
        

def getMaterialPDF(request, *args, **kwargs):
    """ Check and return the PDF file of given material if exist
    """
    mid = kwargs.get('mid', None)
    version = kwargs.get('version', None)
   
    if not version:
        version = getMaterialLatestVersion(mid)
    try:
        export_obj = MaterialExport.objects.get(material_id=mid,
                                                version=version)
        with open(export_obj.path, 'rb') as pdf:
            data = pdf.read()
        return HttpResponse(data, mimetype='application/pdf')

    except MaterialExport.DoesNotExist:
        material = Material.objects.get(material_id=mid,
                                        version=version)
        requestMaterialPDF(material)
        return HttpResponse('Material PDF is being generated...',
                            status=102)
    except IOError:
        export_obj.delete()
        material = Material.objects.get(material_id=mid,
                                        version=version)
        requestMaterialPDF(material)
        return HttpResponse('Material PDF is being generated...',
                            status=102) 
    except:
        raise Http404
    

def getMaterialFile(request, *args, **kwargs):
    """Return request for downloading material file"""
    mfid = kwargs.get('mfid', None)

    try:
        mfile = MaterialFile.objects.get(id=mfid)  
        data = mfile.mfile.read()
        mime_type = mfile.mime_type
        mfile.mfile.close()
        return HttpResponse(data, mimetype=mime_type)
    except:
        raise Http404


def handlePersonAvatar(request, *args, **kwargs):
    """Returns the avatar image of specific person"""
    pid = kwargs.get('pk', None)
    delete = request.GET.get('delete', None) 
    try:
        person = models.Person.objects.get(id=pid)  
        if not delete: 
            data = person.avatar.read()
            person.avatar.close()
            return HttpResponse(data, mimetype='image/jpeg')    # oh dear
        elif delete == '1':
            person.avatar.delete() 
            return HttpResponse('Person avatar deleted', status=200)
    except:
        raise Http404


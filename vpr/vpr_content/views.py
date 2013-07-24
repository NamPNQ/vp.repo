# from django.http import HttpResponse, HttpRequest
# from django.core import urlresolvers
# from rest_framework import generics
# from rest_framework.decorators import api_view
# from rest_framework.reverse import reverse
from django.http import Http404
from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from hashlib import md5
from datetime import datetime
from rest_framework import mixins
from haystack.query import SearchQuerySet 

import os
import mimetypes

from vpr_api.models import APIRecord
from vpr_api.decorators import api_token_required
from vpr_api.utils import APILogger
from vpr_log.logger import get_logger
from vpr_storage.views import zipMaterial, requestMaterialPDF

import models
import serializers


logger = get_logger('api')
apilog = APILogger() 

mimetypes.init()


def raise404(request, message=''):
    """Record failed API call and raise 404 exception"""
    apilog.record(request, 404)
    raise Http404(message)


def dispatchModuleCalls(request):
    """ Analyze the requests and call the appropriate function
    """
    # analyze the URL
    path = splitPath(path)
    if request.method == 'POST':
        params = request.POST
        params['path'] = path
        if len(path) > 1:
            checkInModule(params)
        else:
            createModule(params)
    elif request.method == 'GET':
        # check if getting metadata or download
        if 'content' in request.GET:
            download = request.GET['content']
        if download:
            downloadModule(request)
        else:    
            getModuleMetadata(request)
    elif request.method == 'DELETE':
        # check for permission
        user = request.user
        if user.is_superuser:
            deleteModule(request)
        else:
            pass


def splitPath(path):
    """ Return necessary elements in path
        
        >>> path = '/hello/from/paris/'
        >>> splitPath(path)
        ['hello', 'from', 'paris']

    """
    path = path.split('/')
    path = [item for item in path if len(item)>0]
    return path


# CATEGORY CALLS

class CategoryList(generics.ListCreateAPIView):
    """docstring for AuthorList"""
    model = models.Category
    serializer_class = serializers.CategorySerializer
    paginate_by = None

    @api_token_required
    def get(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.list(request, *args, **kwargs)        
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def post(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.create(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    """docstring for CategoryDetail"""
    model = models.Category
    serializer_class = serializers.CategorySerializer

    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(self.object)

        # check if request for counting
        if request.GET.get('count', None) == '1':
            cid = kwargs.get('pk', None)
            serializer.data['material'] = models.countAssignedMaterial(cid)

        return Response(serializer.data)

    @api_token_required
    def get(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.retrieve(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def put(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.update(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def delete(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.destroy(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


# EDITOR CALLS

class EditorList(generics.ListCreateAPIView):
    """docstring for EditorList"""
    model = models.Editor
    serializer_class = serializers.EditorSerializer

    @api_token_required
    def get(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.list(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def post(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.create(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


class EditorDetail(generics.RetrieveUpdateDestroyAPIView):
    """docstring for EditorDetail"""
    model = models.Editor
    serializer_class = serializers.EditorSerializer

    @api_token_required
    def get(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.retrieve(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def put(self, request, *args, **kwargs):
        """docstring for get"""
        return self.update(request, *args, **kwargs)

    @api_token_required
    def delete(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.destroy(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


# PERSON

class PersonList(generics.ListCreateAPIView):
    """docstring for PersonList"""
    model = models.Person
    serializer_class = serializers.PersonSerializer

    @api_token_required
    def get(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.list(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def post(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.create(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


class PersonDetail(generics.RetrieveUpdateDestroyAPIView):
    """docstring for PersonDetail"""
    model = models.Person
    serializer_class = serializers.PersonSerializer

    @api_token_required
    def get(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.retrieve(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def put(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.update(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def delete(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.destroy(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


# MODULE

class MaterialList(generics.ListCreateAPIView):
    """ Return list of material or create a new one
    """
    model = models.Material
    serializer_class = serializers.MaterialSerializer
    br_fields = ('categories', 'authors', 'editor_id', 
                 'language', 'material_type')

    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.DATA)
        if serializer.is_valid():

            # this call consumes a lot of queries and time
            self.pre_save(serializer.object)
            self.object = serializer.save()

            # add the attached image manually
            self.object.image = request.FILES.get('image', None)
            self.object.save()

            # next, add all other files submitted
            material_id = self.object.material_id
            material_version = self.object.version 
            for key in request.FILES.keys():
                if key == 'image': continue
                mfile = models.MaterialFile()
                mfile.material_id = material_id 
                mfile.version = material_version
                file_content = request.FILES.get(key, None)
                mfile.mfile = file_content 
                mfile.mfile.close()
                mfile.name = request.FILES[key].name
                mfile.description = request.DATA.get(key+'_description', '')
                mfile.mime_type = mimetypes.guess_type(
                    os.path.realpath(mfile.mfile.name))[0] or ''
                mfile.save()
            
            # add original record if having
            if request.DATA.get('original_id', ''):
                orgid = models.OriginalID()
                orgid.material_id = material_id
                orgid.original_id = request.DATA.get('original_id')
                orgid.save()

            # (module/collection) create the zip package and post to vpt
            if request.DATA.get('export-now', 0):
                requestMaterialPDF(self.object) 

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_token_required
    def list(self, request, *args, **kwargs):
        """ Customized function for listing materials with same ID
        """
        try: 
            m_objects = self.model.objects
            if kwargs.get('mid', None):
                self.object_list = m_objects.filter(material_id=kwargs['mid'])
            else:
                self.object_list = m_objects.all()

            # do the filtering
            browse_on = {}
            fields = [item for item in request.GET if item in self.br_fields]
            [browse_on.update({item:request.GET[item]}) for item in fields]
            self.object_list = self.object_list.filter(**browse_on)

            # continue with sorting
            sort_fields = request.GET.get('sort_on', '')
            if sort_fields:
                self.object_list = self.object_list.order_by(sort_fields)
        except:
            raise404(request) 

        # Default is to allow empty querysets.  This can be altered by setting
        # `.allow_empty = False`, to raise 404 errors on empty querysets.
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            error_args = {'class_name': self.__class__.__name__}
            raise404(request, self.empty_error % error_args)

        # Pagination size is set by the `.paginate_by` attribute,
        # which may be `None` to disable pagination.
        page_size = self.get_paginate_by(self.object_list)
        if page_size:
            packed = self.paginate_queryset(self.object_list, page_size)
            paginator, page, queryset, is_paginated = packed
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list)

        # silly steps: remove heavy data from response
        try:
            for res in range(len(serializer.data['results'])):
                serializer.data['results'][res]['text'] = ''
        except:
            # should we shout anything?
            pass

        response = Response(serializer.data)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def post(self, request, *args, **kwargs):
        """Old post method with decorator"""
        response = self.create(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response 


    #def get(self, request, *args, **kwargs):
    #    """docstring for get"""
    #    return Response({'a':'b'})

class MaterialDetail(generics.RetrieveUpdateDestroyAPIView, mixins.CreateModelMixin):
    """
    Return material data, update/check-in it or delete it
    """
    model = models.Material
    serializer_class = serializers.MaterialSerializer

    def get_object(self, material_id, version='', request=None):
        """ Customized get_object() function, used for Material objects
            which will be get by ID and version.
        """
        try:
            args = {'material_id':material_id}
            # get latest or specific version
            object = self.model.objects
            if version:
                args['version'] = version
                object = object.get(**args)
            else:
                object = models.getLatestMaterial(material_id)
            return object 
        except:
            raise404(request, 404)

    def retrieve(self, request, *args, **kwargs):
        """ Customized to the Material objects """
        self.object = self.get_object(material_id=kwargs.get('mid', ''),
                                      version=kwargs.get('version', ''),
                                      request=request)

        serializer = self.get_serializer(self.object)

        response = Response(serializer.data)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def get(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.retrieve(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def put(self, request, *args, **kwargs):
        """ Check in a material  """
        try: 
            serializer = self.get_serializer(data=request.DATA)
            response = None
            if serializer.is_valid():
                # check if valid editor or new material will be created
                sobj = serializer.object
                last_material = models.getLatestMaterial(sobj.material_id)
                last_editor = ""
                try:    
                    last_editor = last_material.editor_id
                except AttributeError:
                    pass 
                # new material will have new ID
                if sobj.editor_id != last_editor:
                    sobj.material_id = models.generateMaterialId()
                    sobj.version = 1
                else:
                    try:
                        sobj.version = last_material.version + 1
                    except AttributeError:
                        sobj.version = 1
                self.pre_save(sobj)
                self.object = serializer.save()
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)            

            apilog.record(request, response.status_code)
            return response
        except: 
            raise404(request)

    @api_token_required
    def destroy(self, request, *args, **kwargs):
        """ Delete the material """
        try:
            self.object = self.get_object(material_id=kwargs.get('mid', ''),
                                          version=kwargs.get('version', ''))
            self.object.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            apilog.record(request, response.status_code)
            return response
        except:
            raise404(request)


class GeneralSearch(generics.ListAPIView):
    """docstring for Search"""
    model = models.Material

    @api_token_required
    def list(self, request, *args, **kwargs):
        """docstring for list"""
        keywords = request.GET.get('kw', '')
        try:
            limit = request.GET.get('on', '')

            # branching for the person case
            if limit.lower() == 'p':  
                self.serializer_class = serializers.PersonSerializer
                allow_models = [models.Person,]                                
            else: 
                self.serializer_class = serializers.IndexMaterialSerializer
                allow_models = [models.Material]

            results = SearchQuerySet().models(*allow_models)
            results = results.filter(content=keywords)
            self.object_list = [obj.object for obj in results] 
        except:
            raise404(request)

        # Default is to allow empty querysets.  This can be altered by setting
        # `.allow_empty = False`, to raise 404 errors on empty querysets.
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            error_args = {'class_name': self.__class__.__name__}
            raise404(self.empty_error % error_args)

        # Pagination size is set by the `.paginate_by` attribute,
        # which may be `None` to disable pagination.
        page_size = self.get_paginate_by(self.object_list)
        if page_size:
            packed = self.paginate_queryset(self.object_list, page_size)
            paginator, page, queryset, is_paginated = packed
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list)

        response = Response(serializer.data) 
        apilog.record(request, response.status_code)
        return response


class MaterialFiles(generics.ListCreateAPIView):
    """View for listing and creating MaterialFile"""
    model = models.MaterialFile
    serializer_class = serializers.MaterialFileSerializer
    
    def get_object(self, mfid, version='', request=None):
        """ Customized get_object() function, used for Material objects
            which will be get by ID and version.
        """
        try:
            object = self.model.objects.get(id=mfid)
            return object 
        except:
            raise404(request, 404)

    def retrieve(self, request, *args, **kwargs):
        """ Customized to the Material objects """
        self.object = self.get_object(mfid=kwargs.get('mfid', ''),
                                      request=request)

        serializer = self.get_serializer(self.object)

        response = Response(serializer.data)
        apilog.record(request, response.status_code)
        return response

    @api_token_required
    def get(self, request, *args, **kwargs):
        """docstring for get"""
        response = self.retrieve(request, *args, **kwargs)
        apilog.record(request, response.status_code)
        return response


@api_view(['GET'])
def listMaterialFiles(request, *args, **kwargs):
    """Lists all files attached to the specific material, except the material image
    """
    material_id = kwargs.get('mid', None)
    version = kwargs.get('version', None)
    # why possibly version gets nothing as value?
    if not version:
        version = models.getMaterialLatestVersion(material_id)
    file_ids = models.listMaterialFiles(material_id, version)

    return Response(file_ids)   

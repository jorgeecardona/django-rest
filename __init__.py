import logging
import traceback

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.db.models.query import QuerySet
from django.db.models import Model
from django.db.models.base import ModelBase
from django.conf.urls.defaults import url


def url_rest(regexp, get = None, post = None, put = None, delete = None):

    methods = {}
    if get:
        methods['GET'] = get
        
    if post:
        methods['POST'] = post

    if put:
        methods['PUT'] = put

    if delete:
        methods['DELETE'] = delete

    return url(regexp, 'core.rest.dispatcher', methods)


def dispatcher(request, GET=None, POST=None, DELETE=None, PUT=None, **kwords):

    if request.method == 'GET' and type(GET) is str:

        # Get the base name and the internal module from the name
        name, internal = GET.rsplit(".",1)
        
        # Import the base bame
        module = __import__(name, fromlist=["*"])        
        
        # Get the internal module
        view = getattr(module, internal)

        if callable(view):
            return view(request, **kwords)        

    if request.method == 'POST' and  type(POST) is str:

        # Get the base name and the internal module from the name
        name, internal = POST.rsplit(".",1)
        
        # Import the base bame
        module = __import__(name, fromlist=["*"])        
        
        # Get the internal module
        view = getattr(module, internal)

        if callable(view):
            return view(request, **kwords)        

    if request.method == 'PUT' and  type(PUT) is str:

        request.method = 'POST'
        request._load_post_and_files()
        request.method = 'PUT'
        request.PUT = request.POST

        # Get the base name and the internal module from the name
        name, internal = PUT.rsplit(".",1)
        
        # Import the base bame
        module = __import__(name, fromlist=["*"])        
        
        # Get the internal module
        view = getattr(module, internal)

        if callable(view):
            return view(request, **kwords)        

    if request.method == 'DELETE' and  type(DELETE) is str:

        # Get the base name and the internal module from the name
        name, internal = DELETE.rsplit(".",1)
        
        # Import the base bame
        module = __import__(name, fromlist=["*"])        
        
        # Get the internal module
        view = getattr(module, internal)

        if callable(view):
            return view(request, **kwords)

    return HttpResponse("Error")

class Error(Exception):
    """
    Rest Error
    ==========

    This class is used to create a rest response with an error.
    """
    pass


class IncorrectMethod(Exception):
    pass

class IncorrectResult(Exception):
    pass

def from_entity_to_dict(entity, fields = None, add_to_dict = None):
    """
    This function pass a model entity to a dict, based on a list of fields
    and a callback function that compute extra (key,value) pairs.
    """
    if fields is None:
        if isinstance(entity, dict):
            first = entity.items()
        else:
            first = entity.__dict__.items()
    else:
        first = [(field, getattr(entity, field)) for field in fields if hasattr(entity, field)]
        
    if callable(add_to_dict):
        first += add_to_dict(entity).items()

    return dict(first)

def retrieve(fields = None, add_to_dict = None, timestamp = None, mimetype = "text/html", auth=None):
    def dec(f):
        def new_f(request, *args, **kwords):

            # Call the function, it suppose to return a QueryDict
            try:
                result = f(request, *args, **kwords)
            except Exception, e:
                # Create a response with an error code but with the error message.
                logging.error(e)
                logging.error(traceback.print_exc())
                return HttpResponse(e, status=400)                
            
            # IF image return it as is.
            # TODO: Check a formal way to change actions in contextual way.
            if mimetype == "image/png":
                return HttpResponse(result, mimetype=mimetype)

            # Check for the result type
            if not isinstance(result, (Model, QuerySet, dict)):
                raise IncorrectResult("Incorrect result returned by retrieve.")

            # Order by date 
            # TODO: why am i doing this??
            if isinstance(result, QuerySet) and isinstance(timestamp, (str, unicode)):
                result = result.order_by(timestamp)
                
            # As this is a retrive select only the oldest
            if isinstance(result, QuerySet):
                result = result[0]
                    
            # Select the right fields
            result_list = from_entity_to_dict(result, fields, add_to_dict)
                
            # Serialize the object
            result_string = simplejson.dumps(result_list)

            # Return the string                
            return HttpResponse(result_string, mimetype = mimetype)

        return new_f
    return dec

def list_(fields = None, add_to_dict = None, timestamp = None, collection = None, mimetype = "text/html"):
    def dec(f):
        def new_f(request, *args, **kwords):

            if request.method == 'GET':
                
                # Call the function, it suppose to return a QuerySet or a list, 
                try:
                    result = f(request, *args, **kwords)
                except Exception, e:
                    # Create a response with an error code but with the error message.
                    logging.error(e)
                    logging.error(traceback.print_exc())
                    return HttpResponse(simplejson.dumps([]), status=400)
                
                
                # Check for the result type
                if type(result) is not QuerySet:
                    raise IncorrectResult("Incorrect result returned by retrieve.")

                # Order by date
                if type(result) is QuerySet and type(timestamp) is str:
                    result = result.order_by(timestamp)
                                               
                # Select the right fields
                result_list = [from_entity_to_dict(entity, fields, add_to_dict) for entity in result]
                
                # Serialize the object
                result_string = simplejson.dumps(result_list)

                # Return the string
                return HttpResponse(result_string, mimetype = mimetype)
            else:
                raise IncorrectMethod("Incorrect retrieve methd, use only GET.")

        return new_f
    return dec

from django.forms import Form

def create(form = None, collection=None, create_method=None, fields = None, add_to_dict = None, mimetype = "text/html"):
    def dec(f):
        def new_f(request, *args, **kwords):

            if type(form) is not Form:
                pass

            if type(collection) is None:
                pass

            try:
                result = f(request, *args, **kwords)
            except Exception, e:
                logging.error(e)
                logging.error(traceback.print_exc())
                return  HttpResponseBadRequest('')
                
            if result is None:
                res = HttpResponse('')
                res.status_code = 400
                return res
            
            # Check for the result type
            if not isinstance(result, (Model, list)):
                raise IncorrectResult("Incorrect result returned by retrieve.")

            # Select the right fields
            if isinstance(result, list):
                result_list = [from_entity_to_dict(r, fields, add_to_dict) for r in result]
            else:
                result_list = from_entity_to_dict(result, fields, add_to_dict)
                
            # Serialize the object
            result_string = simplejson.dumps(result_list)

            # Return the string
            return HttpResponse(result_string, mimetype = mimetype)
                    
        return new_f
    return dec


def delete(collection = None):
    def dec(f):
        def new_f(request, *args, **kwords):

            try:
                result = f(request, *args, **kwords)
                result.delete()

            except Exception, e:
                # Create a response with an error code but with the error message.
                logging.error(e)
                logging.error(traceback.print_exc())
                return HttpResponse(e, status=400)

            return HttpResponse('', status=204)

        return new_f
    return dec


def update(fields = None):
    def dec(f):
        def new_f(request, *args, **kwords):

            result = f(request, *args, **kwords)

            if result is None:
                res = HttpResponse('')
                res.status_code = 400
                return res
            
            # Check for the result type
            if not isinstance(result, (Model,)):
                raise IncorrectResult("Incorrect result returned by retrieve.")

            # Select the right fields
            result_list = from_entity_to_dict(result, fields, add_to_dict)
                
            # Serialize the object
            result_string = simplejson.dumps(result_list)

            # Return the string
            return HttpResponse(result_string)
        return new_f
    return dec


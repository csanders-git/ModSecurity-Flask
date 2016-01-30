import modsecurity

# initiate ModSecurity
modsec = modsecurity.msc_init()
modsec.setConnectorInformation("ModSecurity- v0.0.1-alpha") 
rules = modsecurity.Rules()
ret = rules.load(str(rule))
ret = rules.getParserError()
assay = None

# Hook needed values
import werkzeug.serving
werkzeugRequestHandler = werkzeug.serving.WSGIRequestHandler.handle
def werkzeugRequestHandlerWrapper(*args):
    global assay
    assay = modsecurity.Assay(modsec,rules,None)
    requestHandler = args[0]
    rv = werkzeugRequestHandler(*args)
    valid = True
    if(not hasattr(requestHandler,'path')):
        valid = False
    if(not hasattr(requestHandler,'command')):        
        valid = False
    if(not hasattr(requestHandler,'request_version')):
        valid = False     
    # Call ModSecurity Process URI if we have everything
    if valid == True:
        assay.processURI(str(requestHandler.path),str(requestHandler.command),str(requestHandler.request_version))
    # Add our requests headers
    if(hasattr(requestHandler,'headers')):
        for key, value in requestHandler.headers.items():
            assay.addRequestHeader(str(key),str(value))
    return rv
werkzeug.serving.WSGIRequestHandler.handle = werkzeugRequestHandlerWrapper    

import werkzeug.wrappers
# If we are calling load_data we can possibly use it in some way
# this has a weird effect of being called multiple times
werkzeugLoadFormData = werkzeug.wrappers.BaseRequest._load_form_data
def werkzeugLoadFormDataWrapper(*args):
    global assay
    BaseRequest = args[0]
    assay.appendRequestBody(str(BaseRequest.get_data()),len(BaseRequest.get_data()))
    return werkzeugLoadFormData(*args)
werkzeug.wrappers.BaseRequest._load_form_data = werkzeugLoadFormDataWrapper

import flask.app
flaskMakeResponse = flask.app.Flask.make_response
def flaskMakeResponseWrapper(*args):
    global assay
    # werkzeug will add a date and server header after this hook.
    rv = flaskMakeResponse(*args)    
    out = rv.status.split(' ')
    code = out[0]
    code_msg = " ".join(out[1:])
    response_msg = "\n".join(rv.response)
    assay.appendResponseBody(str(response_msg),len(response_msg))
    for key,value in rv.headers:
        assay.addResponseHeader(str(key),str(value))
    return rv
flask.app.Flask.make_response = flaskMakeResponseWrapper
from django.conf import settings
from django.db import connection
from django.views.generic import TemplateView
import datetime

# debugging middleware which is extremely useful
#
# settings:
#
#   SCULPT_DUMP_SQL     whether to dump data on all SQL queries made during a request, as well as request timing

class SculptDebugMiddleware(object):

    date_request_started = None

    def process_request(self, request):
        self.date_request_started = datetime.datetime.utcnow()

    def process_response(self, request, response):
        if settings.SCULPT_DUMP_SQL or settings.SCULPT_DUMP_SESSION or settings.SCULPT_DUMP_REQUESTS:
            if self.date_request_started != None:
                elapsed_time = (datetime.datetime.utcnow() - self.date_request_started).total_seconds()
                print '==== REQUEST TIME: %s %.3fs %s' % (request.method, elapsed_time, request.META['RAW_URI'] if 'RAW_URI' in request.META else request.META['PATH_INFO'])

        if settings.SCULPT_DUMP_SQL:
            print '==== SQL QUERIES ===='
            for i in range(len(connection.queries)):
                q = connection.queries[i]

                print '%4d %8s %s' % (i+1, q['time'], q['sql'])
                print '--------'

            print '====================='

        if settings.SCULPT_DUMP_SESSION:
            import json
            print '==== SESSION ========'
            print json.dumps(request.session._session)
            print '====================='

        return response

# a simple view that dumps the request;
# use with the dump-request template
# NOTE: this automatically disables itself if you
# aren't running in DEBUG mode; you can override
# this, but then YOU MUST TAKE CARE to disable this
# in your production environment
class DebugTemplateView(TemplateView):
    template_name = "sculpt_debug/dump_request.html"
    always_enabled = False

    def get_context_data(self, **kwargs):
        kwargs = super(DebugTemplateView, self).get_context_data(**kwargs)
        if self.always_enabled or settings.DEBUG:
            kwargs['data'] = {
                    'request': self.request,
                    'settings': settings,
                }
        return kwargs

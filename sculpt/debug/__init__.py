from django.conf import settings
from django.db import connection
from django.views.generic import TemplateView
import datetime

# debugging middleware which is extremely useful
#
# settings:
#
#   SCULPT_DUMP_REQUESTS    write information about requests to stdout; useful
#                           if you're running in an environment that captures
#                           it to a place you can watch. This setting is implied
#                           if any of the other SCULPT_DUMP_* settings are on.
#
#   SCULPT_DUMP_SQL         write all SQL queries to stdout along with the time
#                           taken for the query. Note that this list is kept by
#                           Django internals, so the dump happens at the end of
#                           the request, not as each request is happening. Also,
#                           Django only records times in milliseconds, which is
#                           not all that useful; you may find it worthwhile to
#                           patch Django's timekeeping code to record times in
#                           microseconds instead.
#
#   SCULPT_DUMP_SESSION     write session data to stdout at the end of each
#                           request.
#
# Best practice is that all of these are False in production as they can reveal
# sensitive information that is not normally left in a log file.
#
class SculptDebugMiddleware(object):

    date_request_started = None

    def process_request(self, request):
        if settings.SCULPT_DUMP_SQL or settings.SCULPT_DUMP_SESSION or settings.SCULPT_DUMP_REQUESTS:
            print '==== REQUEST START: %s %s' % (request.method, request.META['RAW_URI'] if 'RAW_URI' in request.META else request.META['PATH_INFO'])
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
            print '==== SESSION ========', '(modified)' if request.session.modified else ''
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

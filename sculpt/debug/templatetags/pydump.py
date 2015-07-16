# these imports are a bit paranoid because this module needs
# to be able to run even in Jython 2.5, without the presence
# of Django, so some symbols get defined with dummy classes
# and other classes later are referenced by name (Java
# classes)
try:
    # see if we have Django first
    from django import template
    from django.conf import settings
    from django.utils.html import escape
    from django.utils.safestring import mark_safe
except ImportError:
    from sculpt.debug.django_stub import escape, settings
    template = None
    mark_safe = lambda x: x  # a no-op function
import decimal
import inspect
try:
    import json
except ImportError:
    # Jython 2.5 doesn't have json built in, install
    # Jyson instead
    from com.xhaus.jyson import JysonCodec as json
import types

if template:
    register = template.Library()

# dump a value in a viewable fashion
# NOTE: we don't use @register.filter because we need to
# conditionally decorate based on whether we can import
# Django or not
def pydump(value, trap_exceptions = True):
    # we do not want to repeatedly concatenate strings,
    # so just collect up the fragments and assemble them
    # at the last moment
    fragments = [ '<div class="sc_dbg">' ]
    
    # we want to keep track of the elements we've already
    # seen so we don't do a recursive dump; this is just
    # a stack, so we only skip it if we're referring to a
    # direct parent, rather just anywhere else in the dump
    seen_names = []
    seen_objects = []
    
    # jump into the recursive function
    pydump_core(value, '', fragments, seen_names, seen_objects, trap_exceptions)
    
    # wrap up
    fragments.append('</div>')
    return mark_safe(''.join(fragments))
    
if template:
    pydump = register.filter(pydump)
    
# recursive function that shows a value
def pydump_core(value, field_name, fragments, seen_names, seen_objects, trap_exceptions = True):

    # see if this item is in our stack
    if id(value) in seen_objects:
        i = seen_objects.index(id(value))
        fragments.append(u'(recursive array reference to level %d, element %s)' % (i+1, '.'.join(seen_names[:i+1])))
        return

    # similarly, some items may be in our prohibited list
    # and we don't want to show those
    full_class_name = value.__class__.__module__+'.'+value.__class__.__name__
    if settings.SCULPT_DEBUG_SKIP_CLASSES is not None and full_class_name in settings.SCULPT_DEBUG_SKIP_CLASSES:
        fragments.append(u'(skipping object of type %s)' % full_class_name)
        return

    # otherwise, push ourselves onto the stack in case we
    # need to recurse
    seen_names.append(field_name)
    seen_objects.append(id(value))

    # determine the parent name
    parent_name = '.'.join(seen_names)
    #print 'item:', parent_name, full_class_name

    # make a valiant attempt to display the item's contents
    try:
        # look for various container types
        # ideally, these would be abstracted out as the code for each is
        # very similar, but there are subtle differences that would be
        # hard to preserve
        if isinstance(value, set):
            #print 'set'
            fragments.append(u'<table class="sc_dbg_set"><tbody>')
            if len(value):
                i = 0
                for v in value:
                    fragments.append(u'<tr><td class="sc_dbg_value">' % { 'parent': parent_name })
                    pydump_core(v, str(i), fragments, seen_names, seen_objects, trap_exceptions)
                    fragments.append(u'</td></tr>')
                    i += 1
            else:
                fragments.append(u'<tr><td class="sc_dbg_empty" title="%(parent)s">(empty)</td></tr>' % { 'parent': parent_name })
            fragments.append(u'</tbody></table>')

        elif isinstance(value, tuple):
            #print 'tuple'
            fragments.append(u'<table class="sc_dbg_tuple"><tbody>')
            if len(value):
                for i in xrange(len(value)):
                    v = value[i]
                    fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent)s.%(key)s">%(key)s</td><td class="sc_dbg_value">' % { 'parent': parent_name, 'key': str(i) })
                    pydump_core(v, str(i), fragments, seen_names, seen_objects, trap_exceptions)
                    fragments.append(u'</td></tr>')
            else:
                fragments.append(u'<tr><td class="sc_dbg_empty" title="%(parent)s">(empty)</td></tr>' % { 'parent': parent_name })
            fragments.append(u'</tbody></table>')

        elif isinstance(value, list):
            #print 'list'
            fragments.append(u'<table class="sc_dbg_list"><tbody>')
            if len(value):
                for i in xrange(len(value)):
                    v = value[i]
                    fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent)s.%(key)s">%(key)s</td><td class="sc_dbg_value">' % { 'parent': parent_name, 'key': str(i) })
                    pydump_core(v, str(i), fragments, seen_names, seen_objects, trap_exceptions)
                    fragments.append(u'</td></tr>')
            else:
                fragments.append(u'<tr><td class="sc_dbg_empty" title="%(parent)s">(empty)</td></tr>' % { 'parent': parent_name })
            fragments.append(u'</tbody></table>')

        elif isinstance(value, dict):
            #print 'dict'
            fragments.append(u'<table class="sc_dbg_dict"><tbody>')
            if len(value):
                for k,v in value.iteritems():
                    if isinstance(k, (frozenset, tuple)):
                        # ah, we have used a set or a tuple as the key in our dict;
                        # make sure to dump that properly
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent)s.%(key)s">' % { 'parent': parent_name, 'key': str(k) })
                        pydump_core(k, '(key)', fragments, seen_names, seen_objects, trap_exceptions)
                        fragments.append(u'</td><td class="sc_dbg_value">')
                    else:
                        # something more normal; we assume we can safely convert the
                        # key to a string
                        # NOTE: this means we lose the ability to see what actual
                        # type it is
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent)s.%(key)s">%(key)s</td><td class="sc_dbg_value">' % { 'parent': parent_name, 'key': str(k) })
                    pydump_core(v, str(k), fragments, seen_names, seen_objects, trap_exceptions)
                    fragments.append(u'</td></tr>')
            else:
                fragments.append(u'<tr><td class="sc_dbg_empty" title="%(parent)s">(empty)</td></tr>' % { 'parent': parent_name })
            fragments.append(u'</tbody></table>')

        # look for various simple types
        elif isinstance(value, types.NoneType):
            fragments.append(u'<span class="sc_dbg_none" title="NoneType">None</span>')
        elif isinstance(value, (types.TypeType, types.BuiltinMethodType, types.CodeType, types.EllipsisType, types.FileType, types.FrameType, types.FunctionType, types.GeneratorType, types.LambdaType, types.MethodType, types.ModuleType, types.NotImplementedType, types.SliceType, types.TracebackType, types.UnboundMethodType, types.XRangeType)):
            fragments.append(u'<span class="sc_dbg_other">%s</span>' % value.__class__.__name__)
        elif (hasattr(types, 'BufferType') and isinstance(value, types.BufferType)) or (hasattr(types, 'GetSetDescriptorType') and isinstance(value, types.GetSetDescriptorType)):
            # these types aren't present in Jython so we test for them more carefully
            fragments.append(u'<span class="sc_dbg_other">%s</span>' % value.__class__.__name__)
        elif isinstance(value, bool):
            fragments.append(u'<span class="sc_dbg_bool" title="bool">%s</span>' % str(value))
        elif isinstance(value, int):
            fragments.append(u'<span class="sc_dbg_int" title="int">%s</span>' % str(value))
        elif isinstance(value, long):
            fragments.append(u'<span class="sc_dbg_long" title="long">%sL</span>' % str(value))
        elif isinstance(value, float):
            fragments.append(u'<span class="sc_dbg_float" title="float">%s</span>' % str(value))
        elif isinstance(value, decimal.Decimal):
            fragments.append(u'<span class="sc_dbg_decimal" title="Decimal">%s</span>' % str(value))
        elif isinstance(value, complex):
            fragments.append(u'<span class="sc_dbg_complex" title="complex">%s</span>' % str(value))
        elif isinstance(value, (str, unicode)):
            # for either string type, it's possible that the data might be
            # JSON; if so, unpack it and show it
            valid_json = False
            if len(value) and value[0] in '[{':
                try:
                    unpacked = json.loads(value)
                    fragments.append(u'<table class="sc_dbg_json"><tbody><tr><td class="sc_dbg_inside" colspan="2">')
                    pydump_core(unpacked, '(json)', fragments, seen_names, seen_objects, trap_exceptions)
                    fragments.append(u'</td></tr><tr><td class="sc_dbg_key sc_dbg_disabled">%d bytes' % len(value))
                    fragments.append(u'</td><td style="display: none;">%s' % escape(value).replace("\n", '<br>'))
                    fragments.append(u'</td></tr></tbody></table>')
                    valid_json = True
                except ValueError:
                    # we're OK with a ValueError, it means the string isn't JSON
                    pass
            
            if not valid_json:
                if isinstance(value, str):
                    fragments.append(u'<span class="sc_dbg_str" title="str">%s</span>' % escape(value))
                elif isinstance(value, unicode):
                    fragments.append(u'<span class="sc_dbg_unicode" title="unicode">%s</span>' % escape(value))

        # otherwise it's an object; walk its attributes
        # this is actually rather complicated because Python has several
        # different ways we could look into the object and find its
        # properties; dir() seems like a nice idea but it's under an
        # object's control and might include pseudo-properties that are
        # not real, so we look at __dict__ instead
        else:
            #print 'object', (value.__dict__.keys() if hasattr(value, '__dict__') else '-')
            fragments.append(u'<table class="sc_dbg_object"><tbody>')
            if hasattr(value, '__class__'):
                # title with class name, ID, and MRO
                if hasattr(value.__class__, '__mro__'):
                    _mro = str(value.__class__.__mro__)
                else:
                    # some old classes lack this
                    _mro = 'no MRO available for this class'
                fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_title" title="%(mro)s" colspan="2">%(class_name)s id:0x%(id)x</td></tr>' % { 'class_name': value.__class__.__name__, 'mro': _mro, 'id': id(value) })
                #print 'object post-MRO', (value.__dict__.keys() if hasattr(value, '__dict__') else '-')

                # method and property values: to understand how these
                # work, have a look in the Python docs for the inspect
                # module: https://docs.python.org/2/library/inspect.html

                # updated: see further explanation at safe_dir, below
                cached_fields = safe_dir(value)

                # method members (we always check)
                methods = safe_dir_filter(cached_fields, inspect.ismethod)

                # only emit methods item if we have some
                if len(methods):
                    fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_disabled">methods</td><td style="display: none;">')
                    fragments.append(u'<table class="sc_dbg_method"><tbody>')
                    for k,v in methods:
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent).%(key)s">%(key)s</td><td class="sc_dbg_value">id:0x%(id)x</td></tr>' % { 'parent': parent_name, 'key': str(k), 'id': id(v) })
                    fragments.append(u'</tbody></table>')
                    fragments.append(u'</td></tr>')
                #print 'object post-methods', (value.__dict__.keys() if hasattr(value, '__dict__') else '-')

                # property members (we always check)
                # properties can only be found by looking at the base
                # class rather than the instance (if the object is
                # an instance and not a class)
                if inspect.isclass(value):
                    test_value = value
                else:
                    test_value = value.__class__

                properties = safe_dir(test_value, lambda x: inspect.isdatadescriptor(x) and isinstance(x, property))
                
                # only emit properties item if we have some
                if len(properties):
                    fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_disabled">properties</td><td style="display: none;">')
                    fragments.append(u'<table class="sc_dbg_method"><tbody>')
                    for k,v in properties:
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent).%(key)s">%(key)s</td><td class="sc_dbg_value">id:0x%(id)x</td></tr>' % { 'parent': parent_name, 'key': str(k), 'id': id(v) })
                    fragments.append(u'</tbody></table>')
                    fragments.append(u'</td></tr>')
                #print 'object post-properties', (value.__dict__.keys() if hasattr(value, '__dict__') else '-')

                # attributes
                if hasattr(value, '__dict__'):
                    if len(value.__dict__):
                        # data members, if we have them (some classes don't)
                        for k,v in value.__dict__.iteritems():
                            #print k, k.__class__.__name__, value.__dict__.keys()
                            # special test: skip callable members, if present
                            # (normally not included in __dict__)
                            if not callable(v):
                                fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent)s.%(key)s">%(key)s</td><td class="sc_dbg_value">' % { 'parent': parent_name, 'key': str(k) })
                                pydump_core(v, str(k), fragments, seen_names, seen_objects, trap_exceptions)
                                fragments.append(u'</td></tr>')
                    else:
                        fragments.append(u'<tr><td class="sc_dbg_empty" title="%(parent)s">(empty)</td></tr>' % { 'parent': parent_name })
                else:
                    # doesn't have __dict__
                    fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_title" colspan="2">unreadable member dict</td></tr>')
            else:
                # doesn't have __class__, either a built-in or C module
                fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_title">unreadable type</td></tr>')
            fragments.append(u'</tbody></table>')

    except Exception, e:
        # bleh, something happened that we didn't expect; include the
        # generated exception instead of blowing up
        #print '%(class_name)s: %(message)s' % { 'class_name': e.__class__.__name__, 'message': str(e) }
        if trap_exceptions:
            fragments.append(u'<span class="sc_debug_error">%(class_name)s: %(message)s</span>' % { 'class_name': e.__class__.__name__, 'message': str(e) })

            # an exception during the debug display is pretty rare; go ahead
            # and spit out the backtrace to the console so we can figure it
            # out

            # sys.exc_info() returns a tuple (type, exception object, stack trace)
            # traceback.format_exception() formats the result in plain text, as a list of strings
            import sys
            import traceback
            backtrace_text = ''.join(traceback.format_exception(*sys.exc_info()))
            print backtrace_text

        else:
            # we were politely asked not to handle these, re-raise it
            raise
        
    seen_names.pop()    # can't use foo = foo[:-1] because that makes a new list and saves its reference; we need to modify the existing list
    seen_objects.pop()
    
def safe_dir(obj, predicate = None):
    '''
    "Safely" obtain a list of attributes for an
    # object.

    Python's dynamic properties are incredibly useful
    but there's a serious lack of good introspection
    tools. Python provides an inspect module which does
    introspection, but at its heart it relies on dir()
    and getattr(), both of which can be overridden by
    classes.

    Django of course overrides both of these, which
    means using Python's "proper" introspection class
    will change the object we're trying to display.
    Worse, if you have models with circular references,
    attempting to recursively introspect anything that
    touches the circular reference will trigger an
    infinite recursion loop, crashing the application.

    In particular, the trigger for this seems to be
    the use of getattr() inside the inspect.getmembers()
    method. To work around this, we access the object's
    native properties dict.

    Unfortunately, using the raw __dict__ will fail
    because it doesn't account for base class properties,
    methods, or anything else fancy. So this function
    attempts to enumerate all of those items. Like the
    inspect.getmembers() call, we accept a predicate
    which will be used to filter the results.
    '''

    # safely get all the classes we need to look at
    obj_mro = [ obj ]
    if hasattr(obj.__class__, '__mro__'):
        obj_mro.extend(obj.__class__.__mro__)
    else:
        obj_mro.extend(obj.__class__)

    # a set of attributes we will test
    found_attrs = {}

    if hasattr(obj, '__dict__'):
        for c in obj_mro:
            # if hasattr(c, '__name__'):
            #     debug_name = c.__name__
            # else:
            #     debug_name = c.__class__.__name__ + ' instance'
            # print 'MRO item:', debug_name

            if hasattr(c, '__dict__'):
                keylist = c.__dict__.keys()
                for k in keylist:
                    if k not in found_attrs:
                        try:
                            v = obj.__dict__[k]
                        except KeyError: #, AttributeError:
                            # so actually AttributeError should
                            # never happen, but it seems a few
                            # classes will actually report they
                            # have the __dict__ attribute and
                            # then throw an AttributeError when
                            # you try to access it
                            continue
                        if predicate is None or predicate(v):
                            found_attrs[k] = v
                # print len(keylist), len(c.__dict__.keys())
                # print 'before:', keylist
                # print ' after:', c.__dict__.keys()

    return sorted(found_attrs.items(), lambda a,b: cmp(a[0],b[0]))

def safe_dir_filter(cached_fields, predicate):
    # filter a cached set of fetched fields
    return [ t for t in cached_fields if predicate(t[1]) ]

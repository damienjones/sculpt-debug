# these imports are a bit paranoid because this module needs
# to be able to run even in Jython 2.5, without the presence
# of Django, so some symbols get defined with dummy classes
# and other classes later are referenced by name (Java
# classes)
try:
    # see if we have Django first
    from django import template
    from django.utils.html import escape
    from django.utils.safestring import mark_safe
except ImportError:
    from sculpt.debug.django_stub import escape
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

    # otherwise, push ourselves onto the stack in case we
    # need to recurse
    seen_names.append(field_name)
    seen_objects.append(id(value))

    # determine the parent name
    parent_name = '.'.join(seen_names)
    #print parent_name

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
            #print 'object'
            fragments.append(u'<table class="sc_dbg_object"><tbody>')
            if hasattr(value, '__class__'):
                # title with class name, ID, and MRO
                if hasattr(value.__class__, '__mro__'):
                    _mro = str(value.__class__.__mro__)
                else:
                    # some old classes lack this
                    _mro = 'no MRO available for this class'
                fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_title" title="%(mro)s" colspan="2">%(class_name)s id:0x%(id)x</td></tr>' % { 'class_name': value.__class__.__name__, 'mro': _mro, 'id': id(value) })

                # method and property values: to understand how these
                # work, have a look in the Python docs for the inspect
                # module: https://docs.python.org/2/library/inspect.html

                # method members (we always check)
                methods = inspect.getmembers(value, inspect.ismethod)

                # only emit methods item if we have some
                if len(methods):
                    fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_disabled">methods</td><td style="display: none;">')
                    fragments.append(u'<table class="sc_dbg_method"><tbody>')
                    for k,v in methods:
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent).%(key)s">%(key)s</td><td class="sc_dbg_value">id:0x%(id)x</td></tr>' % { 'parent': parent_name, 'key': str(k), 'id': id(v) })
                    fragments.append(u'</tbody></table>')
                    fragments.append(u'</td></tr>')

                # property members (we always check)
                # properties can only be found by looking at the base
                # class rather than the instance (if the object is
                # an instance and not a class)
                if inspect.isclass(value):
                    test_value = value
                else:
                    test_value = value.__class__

                properties = inspect.getmembers(test_value, lambda x: inspect.isdatadescriptor(x) and isinstance(x, property))
                
                # only emit properties item if we have some
                if len(properties):
                    fragments.append(u'<tr><td class="sc_dbg_key sc_dbg_disabled">properties</td><td style="display: none;">')
                    fragments.append(u'<table class="sc_dbg_method"><tbody>')
                    for k,v in properties:
                        fragments.append(u'<tr><td class="sc_dbg_key" title="%(parent).%(key)s">%(key)s</td><td class="sc_dbg_value">id:0x%(id)x</td></tr>' % { 'parent': parent_name, 'key': str(k), 'id': id(v) })
                    fragments.append(u'</tbody></table>')
                    fragments.append(u'</td></tr>')

                # attributes
                if hasattr(value, '__dict__'):
                    if len(value.__dict__):
                        # data members, if we have them (some classes don't)
                        for k,v in value.__dict__.iteritems():
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
        else:
            # we were politely asked not to handle these, re-raise it
            raise
        
    seen_names.pop()    # can't use foo = foo[:-1] because that makes a new list and saves its reference; we need to modify the existing list
    seen_objects.pop()
    

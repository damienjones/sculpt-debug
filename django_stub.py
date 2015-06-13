# for those times when you need a Django-like function, but
# you're running in a context that doesn't have Django (such
# as Jython/Tomcat)

def escape(value):
    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
   
# a stub class which yields None for all attributes
class FakeSettings(object):
    def __getattr__(self, attr):
        return None

settings = FakeSettings()

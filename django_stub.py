# for those times when you need a Django-like function, but
# you're running in a context that doesn't have Django (such
# as Jython/Tomcat)

def escape(value):
    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
    
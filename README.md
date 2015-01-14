sculpt-debug
============

There are a lot of great debugging frameworks for Django. This one is extremely lightweight. It consists of two parts:

* Middleware (all options enabled by settings):
    * Dump all requests to stdout.
    * Dump session to stdout after each request.
    * Dump request processing time.
* pydump template filter:
    * Recursively dump the contents of any variable.
    * Intelligent introspection of fields.
    * Color-coded display.
    * Collapse and expand.
    * Intended for looking inside complex objects.

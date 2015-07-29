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

Some of Django's objects are very, very deeply linked. Classes can be added to a blacklist that prevents expansion so that requests can complete in a reasonable amount of time.

Special Note
------------

This is not a complete project. There are no unit tests, and the only documentation is within the code itself. I don't really expect anyone else to use this code... yet. All of those things will be addressed at some point.

That said, the code _is_ being used. This started with work I did while at Caxiam (and I obtained a comprehensive license to continue with the code) so here and there are references to Caxiam that I am slowly replacing. I've done quite a bit of refactoring since then and expect to do more.


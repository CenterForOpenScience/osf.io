"""Global variables related to Django requests

Made available in a separate file so as to be importable by Flask code, before (or in the absence of) Django
"""
import threading

api_globals = threading.local()

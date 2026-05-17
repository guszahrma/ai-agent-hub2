import os

PO_HANDLE = os.getenv('PO_GITHUB_HANDLE')
if not PO_HANDLE:
    raise EnvironmentError("PO_GITHUB_HANDLE environment variable is not set. Please configure it before running.")

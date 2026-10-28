import threading

_lock = threading.Lock()
_patched = False


def patch_pypdf2():
    """Apply Odoo's PyPDF2 decompression compatibility patch once."""
    global _patched
    if _patched:
        return
    with _lock:
        if _patched:
            return
        import PyPDF2
        try:
            import zlib
            import PyPDF2.filters
        except ImportError:
            pass
        else:
            def decompress(data):
                decompressor = zlib.decompressobj()
                return decompressor.decompress(data)

            PyPDF2.filters.decompress = decompress
        _patched = True

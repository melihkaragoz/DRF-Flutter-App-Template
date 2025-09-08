import ipaddress

def get_client_ip(request):
    """
    Returns the best-effort client IP as a string (IPv4/IPv6), or '' if none.
    """
    meta = request.META

    xff = meta.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # take first public, valid IP from the comma-separated list
        for ip in (p.strip() for p in xff.split(',')):
            try:
                obj = ipaddress.ip_address(ip)
                if not (obj.is_private or obj.is_loopback or obj.is_reserved or obj.is_unspecified):
                    return ip
            except ValueError:
                continue
        # else fall back to the last valid one in the chain
        for ip in reversed([p.strip() for p in xff.split(',')]):
            try:
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue

    real_ip = meta.get('HTTP_X_REAL_IP')
    if real_ip:
        try:
            ipaddress.ip_address(real_ip)
            return real_ip
        except ValueError:
            pass

    remote = meta.get('REMOTE_ADDR', '')
    try:
        ipaddress.ip_address(remote)
        return remote
    except ValueError:
        return ''

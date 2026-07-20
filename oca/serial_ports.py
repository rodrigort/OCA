"""Serial port discovery helpers kept separate from the GUI."""


def port_score(port):
    text = " ".join(
        str(value or "") for value in (
            getattr(port, "device", ""),
            getattr(port, "description", ""),
            getattr(port, "manufacturer", ""),
            getattr(port, "product", ""),
        )
    ).lower()
    score = 0
    for marker, weight in (("open can analyzer", 50), ("virtual com", 30), ("vcom", 30), ("cdc", 20), ("usb", 10)):
        if marker in text:
            score += weight
    return score


def sorted_ports(port_objects):
    return sorted(port_objects, key=lambda port: (-port_score(port), str(port.device)))

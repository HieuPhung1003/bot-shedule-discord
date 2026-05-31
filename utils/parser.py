import re


def parse_date(text: str):
    """Parse date text → (month, day) or None."""
    text = text.strip().lower()

    # 25/7, 25-7
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})$', text)
    if m:
        return int(m.group(2)), int(m.group(1))

    # 25 tháng 7, ngày 25 tháng 7
    m = re.match(r'(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})', text)
    if m:
        return int(m.group(2)), int(m.group(1))

    # tháng 7 ngày 25
    m = re.match(r'tháng\s+(\d{1,2})\s+ngày\s+(\d{1,2})', text)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None


def parse_time(text: str):
    """Parse time text → 'HH:MM' or None."""
    text = text.strip().lower()

    # 14:30, 9:00
    m = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # 9h30, 14h00, 9h
    m = re.match(r'^(\d{1,2})h(\d{0,2})$', text)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # 9 giờ sáng, 2 giờ chiều, 9 giờ tối
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*giờ\s*(sáng|chiều|tối)?$', text)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if period == 'chiều' and h < 12:
            h += 12
        elif period == 'tối' and h < 12:
            h += 12
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # 2:30 pm, 9:00 am
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', text)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        if m.group(3) == 'pm' and h != 12:
            h += 12
        elif m.group(3) == 'am' and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    return None


def parse_duration(text: str):
    """Parse duration text → minutes (int) or None."""
    text = text.strip().lower()

    # plain number → minutes
    if re.match(r'^\d+$', text):
        return int(text)

    # X ngày / X day(s)
    m = re.match(r'^(\d+)\s*(?:ngày|day[s]?)$', text)
    if m:
        return int(m.group(1)) * 1440

    # X giờ / Xh / X hour(s)
    m = re.match(r'^(\d+)\s*(?:giờ|h|hour[s]?)$', text)
    if m:
        return int(m.group(1)) * 60

    # X phút / Xm / X min(s)
    m = re.match(r'^(\d+)\s*(?:phút|m|min[s]?)$', text)
    if m:
        return int(m.group(1))

    # Xh Ym (e.g. 1h30m)
    m = re.match(r'^(\d+)h(\d+)(?:m|phút)?$', text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    return None

def validate_phone(user_phone):
    val_phone = user_phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    if val_phone.startswith('80'):
        val_phone = '+375' + val_phone[2:]
    if not val_phone.startswith('+'):
        val_phone = '+' + val_phone
    if not val_phone[1:].isdigit():
        return False
    if len(val_phone) == 13:
        return val_phone
    else:
        return False



from aiogram.types import ReplyKeyboardMarkup


back_message = 'Назад'
cancel_message = 'Отмена'

all_right_message = 'Все верно'
not_right_message = 'Нет, начать заново'

order_menu = '🚚 индивидуальный заказ'
group_order_menu = '🚚 груповой заказ'
register_group_order_menu = '🚚 зарегистрировать груповой заказ'


def get_state_root_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(cancel_message)
    return markup


def get_start_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(order_menu)
    markup.add(group_order_menu)
    markup.add(register_group_order_menu)
    return markup


def get_confirm_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.row(all_right_message, not_right_message)
    return markup


def get_mydefault_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.row(back_message, cancel_message)
    return markup


def get_checkout_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.row(all_right_message, not_right_message, back_message, cancel_message)
    return markup

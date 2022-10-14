from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext


async def get_help(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    # button_commands = types.InlineKeyboardButton('Создать заказ', callback_data='help_o')
    button_write = types.InlineKeyboardButton('Написать', callback_data='help_w')
    button_back = types.InlineKeyboardButton('Назад', callback_data='start')  # to start command
    # button_site = types.InlineKeyboardButton('Помощь на сайте', url='https://greenwayminsk.by/faq')
    # button_call = types.InlineKeyboardButton('Позвонить', callback_data='help_c')
    markup.row(button_write)
    markup.row(button_back)
    # markup.row(button_site)
    # markup.row(button_call)
    # markup.row(button_commands)
    await message.answer('Выберите вариант', reply_markup=markup)


async def help_actions(call: types.CallbackQuery):
    await call.answer('ty')
    if call.data == 'help_w':
        await call.message.answer('Напишите сообщение')
    elif call.data == 'help_c':
        await call.message.answer('Позвоните на горячую линию: тел +375291234567')
    elif call.data == 'help_o':
        keyboard = types.ReplyKeyboardMarkup()
        commands = ['индивидуальный заказ', 'group_order', 'register_group_order']
        for com in commands:
            keyboard.add(com)
        await call.message.answer('Выберите тип заказа', reply_markup=keyboard)


async def news(message: types.Message):
    await message.answer('Новости: https://beegreen.by/')


def register_help(dp: Dispatcher):
    dp.register_message_handler(get_help, commands=['help'])
    dp.register_callback_query_handler(help_actions, lambda call: call.data.startswith('help'))
    dp.register_message_handler(news, commands=['news'])

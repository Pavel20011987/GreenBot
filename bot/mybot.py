import sys
import os

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.expanduser(BASE_DIR)
if path not in sys.path:
    sys.path.insert(0, path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "greenway.settings")
django.setup()

from bot.bot_settings import TOKEN, bot, storage, dp
from bot.keyboards.reply_keyboard import get_start_keyboard
from bot.handlers.individual_order import register_individual_order
from bot.handlers.help import register_help
from bot.handlers.group_order import register_group_order
from bot.handlers.group_order_registration import register_group_order_registration

delivery_cb = CallbackData('delivery', 'id', 'address', 'action')

order_menu = '🚚 индивидуальный заказ'
group_order_menu = '🚚 груповой заказ'
register_group_order_menu = '🚚 зарегистрировать груповой заказ'


async def set_commands(dp=dp):  # dp=dp only for arg placeholder: func gets and dp inst
    commands = [
        types.BotCommand(command='/help', description='Помощь'),
        types.BotCommand(command='/start', description='Новый заказ'),
        types.BotCommand(command='cancel', description='Отмена'),
    ]
    await dp.bot.set_my_commands(commands)
    print('commands are loaded')


@dp.message_handler(state=['*'], text=['Нет, начать заново'])
@dp.message_handler(state=['*'], commands=['cancel'])
@dp.message_handler(state=['*'], text=['Отмена'])
@dp.message_handler(state=['*'], commands=['start'])
@dp.message_handler(state=['*'], text=['start'])
async def start(message: types.Message, state: FSMContext):
    if state:
        await state.finish()
    await message.answer('Выберите действие', reply_markup=get_start_keyboard())


if __name__ == '__main__':
    register_individual_order(dp)
    register_group_order(dp)
    register_group_order_registration(dp)
    register_help(dp)
    executor.start_polling(dp, on_startup=set_commands)

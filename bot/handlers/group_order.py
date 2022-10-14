import sys
import os
import json
import requests

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from asgiref.sync import sync_to_async

import django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.expanduser(BASE_DIR)
if path not in sys.path:
    sys.path.insert(0, path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "greenway.settings")
django.setup()

from bot.bot_settings import bot, bitrix_24, bitrix_webhook
from bot.keyboards.reply_keyboard import (back_message, get_mydefault_keyboard,
                                          get_state_root_keyboard, get_start_keyboard)
from bot.models import PersonalOrder, TelegramUser, GroupOrder


class GroupOrderState(StatesGroup):
    group_number = State()
    number = State()
    surname = State()
    choose_comment = State()
    comment = State()
    confirm = State()


async def start_order(message: types.Message):
    await bot.send_message(message.chat.id, f'Введите номер групового заказа', reply_markup=get_state_root_keyboard())
    await GroupOrderState.group_number.set()


async def group_order_back_to_start(message: types.Message, state: FSMContext):
    await GroupOrderState.group_number.set()
    await start_order(message)


async def group_order_number(message: types.Message, state: FSMContext):
    await state.update_data(group_order_number=message.text)

    await bot.send_message(message.chat.id, f'Введите номер заказа', reply_markup=get_mydefault_keyboard())
    await GroupOrderState.next()

async def order_back_to_group_number(message: types.Message, state: FSMContext):
    await GroupOrderState.group_number.set()
    await group_order_number(message, state)


async def order_number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)

    await bot.send_message(message.chat.id, 'Введите Фамилию (заказчика)', reply_markup=get_mydefault_keyboard())
    await GroupOrderState.next()


async def order_back_to_surname(message: types.Message, state: FSMContext):
    await GroupOrderState.number.set()
    await order_number(message, state)


async def order_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)

    keyboard = get_mydefault_keyboard()
    button_yes = types.KeyboardButton('Да')
    button_no = types.KeyboardButton('Нет')
    keyboard.add(button_yes, button_no)
    await bot.send_message(message.chat.id, "Хотите оставить коментарий?", reply_markup=keyboard)
    await GroupOrderState.next()


async def order_back_to_choose_comment(message: types.Message, state: FSMContext):
    await GroupOrderState.surname.set()
    await order_surname(message, state)

async def order_choose_comment(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        await bot.send_message(message.chat.id, 'Введите свой комментайрий:', reply_markup=get_mydefault_keyboard())
        await GroupOrderState.next()
    else:
        keyboard = get_mydefault_keyboard()
        user_data = await state.get_data()
        await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
        confirm_text = f"Номер групового заказа: {user_data['group_order_number']}; \n" \
                       f"Номер заказа: {user_data['number']}; \n" \
                       f"Фамилия заказчика: {user_data['surname']}; \n" \
                       f"комментарий: {user_data.get('comment')}; \n"
        button_yes = types.KeyboardButton('Да, информация верна')
        button_no = types.KeyboardButton('Нет, начать заново')
        keyboard.add(button_yes, button_no)
        await bot.send_message(message.chat.id, confirm_text, reply_markup=keyboard)
        await GroupOrderState.confirm.set()


async def order_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)

    keyboard = get_mydefault_keyboard()
    user_data = await state.get_data()
    await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
    confirm_text = f"Номер групового заказа: {user_data['group_order_number']}; \n" \
                   f"Номер заказа: {user_data['number']}; \n" \
                   f"Фамилия заказчика: {user_data['surname']}; \n" \
                   f"комментарий: {user_data.get('comment')}; \n"
    button_yes = types.KeyboardButton('Да, информация верна')
    button_no = types.KeyboardButton('Нет, начать заново')
    keyboard.add(button_yes, button_no)
    await bot.send_message(message.chat.id, confirm_text, reply_markup=keyboard)
    await GroupOrderState.next()



async def order_confirm(message: types.Message, state: FSMContext):
    if message.text == 'Да, информация верна':
        user_data = await state.get_data()
        user_id = message.from_user.id
        await continue_group_order(user_data, user_id)
        await bot.send_message(message.chat.id, 'Заказ подтвержден, менерджер с вами свяжется', reply_markup=get_start_keyboard())
    elif message.text == 'Нет, начать заново':
        await bot.send_message(message.chat.id, 'Начните заново', reply_markup=get_start_keyboard())
    else:
        await bot.send_message(message.chat.id, 'Пожлуйста, используйте клавиатуру для ответа')
    await state.finish()


@sync_to_async
def continue_group_order(user_data, user_id):
    group_order = GroupOrder.objects.get(group_code=user_data['group_order_number'])
    new_order = PersonalOrder.objects.create(
        group_order=group_order,
        code=user_data['number'],
        surname=user_data['surname'],
        tel_number=group_order.tel_number,
        comment=user_data.get('comment'),
        delivery_type=group_order.delivery_type,
        delivery_address=group_order.delivery_address,
        creator_id=user_id,
        delivery_outlet=group_order.delivery_outlet,
        fio=group_order.fio
    )


    split_fio = user_data['surname'].split()
    if new_order.delivery_address:
        bitrix_address = new_order.delivery_address
    else:
        bitrix_address = new_order.delivery_outlet.address

    # create deal in bitrix
    bitrix_last_name = split_fio[0:1][0] if split_fio[0:1] else ''
    bitrix_first_name = split_fio[1:2][0] if split_fio[1:2] else ''
    bitrix_second_name = split_fio[2:3][0] if split_fio[2:3] else ''
    deal_title = f"Груповой заказ №{new_order.group_order.group_code} заказ №{user_data['number']}"
    deal_params = {'fields': {
        'TITLE': deal_title,
        'TYPE_ID': 'GOODS',
        'STAGE_ID': 'NEW',
        'PROBABILITY': None,
        'COMMENTS': 'Коммент1',
        'ASSIGNED_BY_ID': '',
        'IS_NEW': 'N',
        'SOURCE_ID': '2|TELEGRAM',
        'SOURCE_DESCRIPTION': 'Групповой заказ',
        'UF_CRM_6036424E7B4F9': f'{user_id}',
        'UF_CRM_6036424EA0F45': f"{user_data['number']}",
        'UF_CRM_6036424EAE575': user_data.get('comment'),
        'UF_CRM_1614788814025': bitrix_first_name,
        'UF_CRM_1614788843264': bitrix_second_name,
        'UF_CRM_1614788853282': bitrix_last_name,
        'UF_CRM_1614788939007': f"{group_order.tel_number}",
        'UF_CRM_1614789052716': '0|BYN',
        'UF_CRM_603FBACF1563C': new_order.delivery_type,
        'UF_CRM_603FBACF214D4': user_data.get('order_choose_delivery_company'),
        'UF_CRM_1614789073025': bitrix_address}}

    bitrix_deal = f"{bitrix_webhook}crm.deal.add"
    requests.post(bitrix_deal, json=deal_params)

    # create contact in bitrix
    contact_params = {'fields': {
        "LAST_NAME": bitrix_last_name,  # Фамилия
        "NAME": bitrix_first_name,  # Имя
        "SECOND_NAME": bitrix_second_name,  # Отчество
        "TYPE_ID": "CLIENT",
        "SOURCE_ID": "SELF",
        "PHONE": [{"VALUE": group_order.tel_number, }],
        "UF_CRM_1614170717684": user_id,  # telegram ID
    }}
    requests.post(f"https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.contact.add", json=contact_params)

    # get this deal
    r = requests.get(f"https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.deal.list?filter[TITLE]={deal_title}")
    this_deal_id = json.loads(r.text)['result'][0]['ID']

    # get this contact
    r = requests.get(f'https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.contact.list'
                     f'?filter[UF_CRM_1614170717684]={user_id}&filter[LAST_NAME]={bitrix_last_name}'
                     f'&filter[NAME]={bitrix_first_name}&filter[SECOND_NAME]={bitrix_second_name}')
    print(r.text)
    this_contact_id = json.loads(r.text)['result'][-1]['ID']

    # add contact to deal
    params = {'ID': this_deal_id,  # id deal
              'fields':
                  {'CONTACT_ID': this_contact_id  # id contact
                   }}
    r = requests.post(f'https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.deal.contact.add', json=params)
    json.loads(r.text)





def register_group_order(dp: Dispatcher):
    dp.register_message_handler(start_order, text=['🚚 груповой заказ'], state=['*'])
    dp.register_message_handler(start_order, commands=['group_order'], state=['*'])

    dp.register_message_handler(group_order_number, state=[GroupOrderState.group_number])
    dp.register_message_handler(group_order_back_to_start, text=back_message, state=GroupOrderState.number)

    dp.register_message_handler(order_number, state=[GroupOrderState.number])
    dp.register_message_handler(order_back_to_group_number, text=back_message, state=GroupOrderState.surname)

    dp.register_message_handler(order_surname, state=[GroupOrderState.surname])
    dp.register_message_handler(order_back_to_surname, text=back_message, state=GroupOrderState.choose_comment)

    dp.register_message_handler(order_choose_comment,
                                lambda message: message.text in ['Да', 'Нет'],
                                state=GroupOrderState.choose_comment)
    dp.register_message_handler(order_back_to_choose_comment, text=back_message, state=GroupOrderState.comment)
    dp.register_message_handler(order_comment, state=GroupOrderState.comment)



    dp.register_message_handler(order_confirm,
                                lambda message: message.text in ['Да, информация верна'],
                                state=GroupOrderState.confirm)
    dp.register_message_handler(order_back_to_choose_comment, text=back_message, state=GroupOrderState.confirm)




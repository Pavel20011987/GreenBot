import sys
import os
import requests
import json

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

from bot.bot_settings import bot, bitrix_webhook, bitrix_24
from bot.utils.phone_validate import validate_phone
from bot.keyboards.reply_keyboard import (back_message, get_mydefault_keyboard,
                                          get_state_root_keyboard, get_start_keyboard)
from bot.models import (PersonalOrder, TelegramUser,
                        Region, Area, City,
                        DeliveryCompany, OutletLocation,
                        GroupOrder)


class RegisterOrder(StatesGroup):
    choose_delivery = State()
    choose_delivery_company = State()
    choose_region = State()
    choose_area = State()
    choose_city = State()
    choose_outlet_area = State()
    choose_outlet = State()
    address = State()
    house = State()
    # flat = State()
    fio = State()
    phone = State()
    confirm = State()


async def start_order(message: types.Message):
    keyboard = get_state_root_keyboard()
    button_outlet = types.KeyboardButton('До пункта выдачи')
    button_door = types.KeyboardButton('До двери')
    button_courier = types.KeyboardButton('Курьер по г. Минск')
    keyboard.add(button_outlet, button_door)
    keyboard.row(button_courier)
    await bot.send_message(message.chat.id, "Выберите тип доставки", reply_markup=keyboard)
    await RegisterOrder.choose_delivery.set()


async def order_back_to_start(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_delivery.set()
    await start_order(message)


async def order_choose_delivery(message: types.Message, state: FSMContext, region_flag=False):
    if message.text == 'До двери' or region_flag:
        await state.update_data(choose_delivery='to_door')
        regions = await sync_to_async(list)(
            Region.objects.all())  # https://forum.djangoproject.com/t/asynchronous-orm/5925?page=3
        keyboard = get_mydefault_keyboard()
        for region in regions:
            keyboard.add(region.title)
        await bot.send_message(message.chat.id, 'Выберите область', reply_markup=keyboard)
        await RegisterOrder.choose_region.set()

    elif message.text == 'Курьер по г. Минск':
        await bot.send_message(message.chat.id, 'Введите название улицы для доставки',
                               reply_markup=get_mydefault_keyboard())
        await state.update_data(choose_delivery='courier')
        await RegisterOrder.address.set()

    else:
        keyboard = get_mydefault_keyboard()
        companys = await sync_to_async(list)(DeliveryCompany.objects.all())
        for company in companys:
            keyboard.add(company.name)
        await bot.send_message(message.chat.id, 'Выберите курьерскую службу', reply_markup=keyboard)
        if not message.text == back_message:
            await state.update_data(choose_delivery='outlet')
        await RegisterOrder.next()


async def order_back_to_choose_delivery(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_delivery.set()
    await start_order(message)


async def order_choose_delivery_company(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(order_choose_delivery_company=message.text)

    outlet_locations = await sync_to_async(list)(OutletLocation.objects.filter())

    if not len(outlet_locations) > 99:
        keyboard = get_mydefault_keyboard()
        for location in outlet_locations:
            keyboard.add(location.address)
        await bot.send_message(message.chat.id, 'Выберите пункт доставки', reply_markup=keyboard)
        await RegisterOrder.choose_outlet.set()
    else:
        keyboard = get_mydefault_keyboard()
        for location in outlet_locations:
            keyboard.add(location.area)
        await bot.send_message(message.chat.id, 'Выберите место', reply_markup=keyboard)
        await RegisterOrder.choose_outlet_area.set()


async def order_choose_outlet_area(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(order_choose_delivery_company=message.text)

    user_data = await state.get_data()
    print('123413')

    outlet_locations = await sync_to_async(list)(
        OutletLocation.objects.filter(company__name=user_data['order_choose_delivery_company']).filter(
            area=message.text))

    keyboard = get_mydefault_keyboard()
    for location in outlet_locations:
        keyboard.add(location.address)
    await bot.send_message(message.chat.id, 'Выберите пункт доставки', reply_markup=keyboard)
    await RegisterOrder.choose_outlet.set()


async def order_choose_region(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    region = user_data.get('choose_region')
    if not message.text == back_message:
        if not region:
            region = message.text
        await state.update_data(choose_region=region)
    else:
        user_data = await state.get_data()
        region = user_data['choose_region']

    areas = await sync_to_async(list)(Area.objects.filter(region__title=region))
    keyboard = get_mydefault_keyboard()
    for area in areas:
        keyboard.add(area.title)
    await bot.send_message(message.chat.id, 'Выберите район', reply_markup=keyboard)
    await RegisterOrder.next()


async def order_back_to_choose_region(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_delivery.set()
    await order_choose_delivery(message, state, region_flag=True)


async def order_choose_area(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        area = message.text
        await state.update_data(choose_area=area)
        cities = await sync_to_async(list)(City.objects.filter(area__title=area))
        keyboard = get_mydefault_keyboard()
        for city in cities:
            keyboard.add(city.title)
        await bot.send_message(message.chat.id, 'Выберите город', reply_markup=keyboard)
        await RegisterOrder.next()
    else:
        user_data = await state.get_data()
        if user_data['choose_delivery'] != 'courier':
            area = user_data['choose_area']
            cities = await sync_to_async(list)(City.objects.filter(area__title=area))
            keyboard = get_mydefault_keyboard()
            for city in cities:
                keyboard.add(city.title)
            await bot.send_message(message.chat.id, 'Выберите город', reply_markup=keyboard)
            await RegisterOrder.next()

        else:
            await order_back_to_start(message, state)


async def order_back_to_choose_area(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_region.set()
    await order_choose_region(message, state)


async def order_choose_city(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        city = message.text
        await state.update_data(choose_city=city)

    await bot.send_message(message.chat.id, 'Введите улицу для доставки', reply_markup=get_mydefault_keyboard())
    # if not message.text == back_message:
    #     await state.update_data(choose_delivery='to_door')
    await RegisterOrder.address.set()


async def order_back_to_choose_city(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_area.set()
    await order_choose_area(message, state)


async def order_choose_address(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        outlet_address = message.text
        await state.update_data(outlet_address=outlet_address)
        await state.update_data(address=None)
    else:
        user_data = await state.get_data()
        outlet_address = user_data['outlet_address']

    await bot.send_message(message.chat.id, 'Введите фамилию, имя, отчество Получателя',
                           reply_markup=get_mydefault_keyboard())
    await RegisterOrder.fio.set()


async def order_back_to_choose_outlet_address(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_delivery.set()
    await order_choose_delivery(message, state)


async def order_delivery_address(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(address=message.text)
        await state.update_data(choose_outlet=None)

    await bot.send_message(message.chat.id, 'Введите номер дома и квартиру', reply_markup=get_mydefault_keyboard())
    await RegisterOrder.house.set()


async def order_house(message: types.Message, state: FSMContext):
    if message.text != back_message:
        await state.update_data(house=message.text)

    await bot.send_message(message.chat.id, 'Введите фамилию, имя, отчество Получателя')
    await RegisterOrder.fio.set()


async def order_back_to_house(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    if user_data['choose_delivery'] == 'outlet':
        await RegisterOrder.choose_delivery_company.set()
        await order_choose_delivery_company(message, state)
    else:
        await RegisterOrder.address.set()
        await order_delivery_address(message, state)


async def order_back_to_street(message: types.Message, state: FSMContext):
    await RegisterOrder.choose_city.set()
    await order_choose_city(message, state)


async def order_back_to_fio(message: types.Message, state: FSMContext):
    await RegisterOrder.house.set()
    await order_house(message, state)


async def order_fio(message: types.Message, state: FSMContext):
    user_fio = message.text
    await state.update_data(fio=user_fio)

    await bot.send_message(message.chat.id, 'Введите мобильный телефон Получателя в формате +375291234567')
    await RegisterOrder.phone.set()


async def order_back_to_phone(message: types.Message, state: FSMContext):
    await RegisterOrder.fio.set()
    await order_fio(message, state)


async def order_phone(message: types.Message, state: FSMContext):
    if message.text != back_message:
        phone = validate_phone(message.text)
        if not phone:
            await bot.send_message(message.chat.id, f'Некорректный номер: {message.text}')
            message.text = back_message
            await order_back_to_phone(message, state)

        else:
            await state.update_data(phone=phone)
            user_data = await state.get_data()
            await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
            if user_data['choose_delivery'] == 'outlet':
                confirm_text = f"тип доставки: {user_data['choose_delivery']}; \n" \
                               f"курьерская служба: {user_data['order_choose_delivery_company']} \n" \
                               f"адресс пункта самовывоза: {user_data['outlet_address']} \n" \
                               f"ФИО: {user_data['fio']}; \n" \
                               f"Номер телефона: {user_data['phone']}; \n"
            elif user_data['choose_delivery'] == 'to_door':
                confirm_text = f"тип доставки: {user_data['choose_delivery']}; \n" \
                               f"адресс доставки: {user_data['choose_region']} {user_data['choose_area']}" \
                               f" {user_data['choose_city']} {user_data['address']} {user_data['house']} \n" \
                               f"ФИО: {user_data['fio']}; \n" \
                               f"Номер телефона: {user_data['phone']}; \n"
            elif user_data['choose_delivery'] == 'courier':
                confirm_text = f"тип доставки: {user_data['choose_delivery']}; \n" \
                               f"адресс доставки: Минск {user_data['address']} {user_data['house']} \n" \
                               f"ФИО: {user_data['fio']}; \n" \
                               f"Номер телефона: {user_data['phone']}; \n"
            else:
                confirm_text = 'ошибка, начните заново'

            keyboard = get_mydefault_keyboard()
            button_yes = types.KeyboardButton('Получить номер группового заказа')
            button_no = types.KeyboardButton('Нет, начать заново')
            keyboard.row(button_yes)
            keyboard.row(button_no)
            await bot.send_message(message.chat.id, confirm_text, reply_markup=keyboard)
            await RegisterOrder.confirm.set()
    else:
        await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
        user_data = await state.get_data()
        keyboard = get_mydefault_keyboard()
        button_yes = types.KeyboardButton('Получить номер группового заказа')
        button_no = types.KeyboardButton('Нет, начать заново')
        keyboard.row(button_yes)
        keyboard.row(button_no)
        await bot.send_message(message.chat.id, user_data, reply_markup=keyboard)
        await RegisterOrder.confirm.set()


async def order_confirm(message: types.Message, state: FSMContext):
    if message.text == 'Получить номер группового заказа':
        user_data = await state.get_data()
        user_id = message.from_user.id
        bitrix_broup_number = await create_group_order(user_data, user_id)

        await bot.send_message(message.chat.id, f'''Ваш регистрационный номер группового заказа 
{bitrix_broup_number} 
Скопируйте регистрационный номер группового заказа и вставьте его в новый «Групповой заказ»''',
                               reply_markup=get_start_keyboard())
    elif message.text == 'Нет, начать заново':
        await bot.send_message(message.chat.id, 'Начните заново', reply_markup=get_start_keyboard())
    else:
        await bot.send_message(message.chat.id, 'Пожлуйста, используйте клавиатуру для ответа')
    await state.finish()


@sync_to_async
def create_group_order(user_data, user_id, bitrix_broup_number=None):
    outlet_location = None
    delivery_address = None
    if user_data['choose_delivery'] == 'outlet':
        delivery_type = 'Самовывоз'
        outlet_location = OutletLocation.objects.get(address=user_data['outlet_address'])

    elif user_data['choose_delivery'] == 'to_door':
        delivery_type = 'До двери'
        delivery_address = f"{user_data['choose_region']}, {user_data['choose_area']}, {user_data['choose_city']}, {user_data['address']}, {user_data['house']}"

    elif user_data['choose_delivery'] == 'courier':
        delivery_type = 'Курьер по минску'
        delivery_address = f"г. Минск, {user_data['address']}, {user_data['house']}"

    new_group_order = GroupOrder.objects.create(
        # group_code=bitrix_broup_number,
        creator_id=user_id,
        fio=user_data['fio'],
        tel_number=user_data['phone'],
        delivery_type=delivery_type,
        delivery_outlet=outlet_location,
        delivery_address=delivery_address,
        comment=user_data.get('comment')
    )

    split_fio = user_data['fio'].split()
    if new_group_order.delivery_address:
        bitrix_address = new_group_order.delivery_address
    else:
        bitrix_address = outlet_location.address

    # create deal in bitrix
    bitrix_last_name = split_fio[0:1][0] if split_fio[0:1] else ''
    bitrix_first_name = split_fio[1:2][0] if split_fio[1:2] else ''
    bitrix_second_name = split_fio[2:3][0] if split_fio[2:3] else ''
    deal_title = f"Групповой заказ №{new_group_order.id}"
    deal_params = {'fields': {
        'TITLE': deal_title,
        'TYPE_ID': 'GOODS',
        'STAGE_ID': 'NEW',
        'PROBABILITY': None,
        'ASSIGNED_BY_ID': '',
        'COMMENTS': 'Коммент1',
        'IS_NEW': 'N',
        'SOURCE_ID': '2|TELEGRAM',
        'SOURCE_DESCRIPTION': 'Групповой заказ',
        'UF_CRM_6036424E7B4F9': f'{user_id}',
        # 'UF_CRM_6036424EA0F45': f"{user_data['number']}",
        'UF_CRM_6036424EAE575': user_data.get('comment'),
        'UF_CRM_1614788814025': bitrix_first_name,
        'UF_CRM_1614788843264': bitrix_second_name,
        'UF_CRM_1614788853282': bitrix_last_name,
        'UF_CRM_1614788939007': f"{user_data['phone']}",
        'UF_CRM_1614789052716': '0|BYN',
        'UF_CRM_603FBACF1563C': delivery_type,
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
        "PHONE": [{"VALUE": user_data['phone'], }],
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
    this_contact_id = json.loads(r.text)['result'][-1]['ID']

    # add contact to deal
    params = {'ID': this_deal_id,  # id deal
              'fields':
                  {'CONTACT_ID': this_contact_id  # id contact
                   }}
    r = requests.post(f'https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.deal.contact.add', json=params)
    json.loads(r.text)

    new_group_order.group_code = new_group_order.id  # TODO is it right
    new_group_order.save()
    return new_group_order.group_code


def register_group_order_registration(dp: Dispatcher):
    dp.register_message_handler(start_order, text=['🚚 зарегистрировать груповой заказ'], state=['*'])
    dp.register_message_handler(start_order, commands=['register_group_order'], state=['*'])

    dp.register_message_handler(order_choose_delivery,
                                lambda message: message.text in ['До пункта выдачи', 'До двери', 'Курьер по г. Минск'],
                                state=RegisterOrder.choose_delivery)
    dp.register_message_handler(order_back_to_start, text=back_message, state=RegisterOrder.choose_delivery_company)
    dp.register_message_handler(order_back_to_start, text=back_message, state=RegisterOrder.choose_region)

    dp.register_message_handler(order_choose_delivery_company, state=RegisterOrder.choose_delivery_company)

    dp.register_message_handler(order_choose_region, state=RegisterOrder.choose_region)
    dp.register_message_handler(order_back_to_choose_region, text=back_message, state=RegisterOrder.choose_area)

    dp.register_message_handler(order_choose_area, state=RegisterOrder.choose_area)
    dp.register_message_handler(order_back_to_choose_area, text=back_message, state=RegisterOrder.choose_city)

    dp.register_message_handler(order_choose_city, state=RegisterOrder.choose_city)

    dp.register_message_handler(order_back_to_choose_outlet_address,
                                text=back_message,
                                state=RegisterOrder.choose_outlet)
    dp.register_message_handler(order_choose_address, state=RegisterOrder.choose_outlet)

    dp.register_message_handler(order_choose_outlet_area, state=RegisterOrder.choose_outlet_area)

    dp.register_message_handler(order_back_to_choose_city, text=back_message, state=RegisterOrder.address)
    dp.register_message_handler(order_delivery_address, state=RegisterOrder.address)

    dp.register_message_handler(order_back_to_street, text=back_message, state=RegisterOrder.house)
    dp.register_message_handler(order_house, state=RegisterOrder.house)

    dp.register_message_handler(order_back_to_fio, text=back_message, state=RegisterOrder.phone)
    dp.register_message_handler(order_phone, state=RegisterOrder.phone)

    dp.register_message_handler(order_back_to_house, text=back_message, state=RegisterOrder.fio)
    dp.register_message_handler(order_fio, state=RegisterOrder.fio)

    dp.register_message_handler(order_back_to_choose_delivery, text=back_message, state=RegisterOrder.confirm)
    dp.register_message_handler(order_confirm,
                                lambda message: message.text in ['Получить номер группового заказа'],
                                state=RegisterOrder.confirm)

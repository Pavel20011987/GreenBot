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

from bot.bot_settings import bot, bitrix_24, bitrix_webhook
from bot.utils.phone_validate import validate_phone
from bot.keyboards.reply_keyboard import (back_message, get_mydefault_keyboard,
                                          get_state_root_keyboard, get_start_keyboard)
from bot.models import (PersonalOrder, TelegramUser,
                        Region, Area, City,
                        DeliveryCompany, OutletLocation)


class Order(StatesGroup):
    number = State()
    surname = State()
    phone = State()
    choose_comment = State()
    comment = State()
    choose_delivery = State()
    choose_delivery_company = State()
    choose_region = State()
    choose_area = State()
    choose_city = State()
    choose_outlet_area = State()
    choose_outlet = State()
    address = State()
    house = State()
    recipient_phone = State()
    confirm = State()


async def start_order(message: types.Message):
    await Order.number.set()
    await bot.send_message(message.chat.id, f'Введите номер заказа', reply_markup=get_state_root_keyboard())


async def order_back_to_start(message: types.Message, state: FSMContext):
    await Order.number.set()
    await start_order(message)


async def order_number(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(number=message.text)
    await bot.send_message(message.chat.id, 'Введите Фамилию Имя Отчество', reply_markup=get_mydefault_keyboard() )
    await Order.next()


async def order_back_to_number(message: types.Message, state: FSMContext):
    await Order.number.set()
    await order_number(message, state)


async def order_surname(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(surname=message.text)

    await bot.send_message(message.chat.id, 'Введите Ваш номер мобильного телефона в формате +375291234567', reply_markup=get_mydefault_keyboard())
    await Order.next()


async def order_back_to_surname(message: types.Message, state: FSMContext):
    await Order.surname.set()
    await order_surname(message, state)


async def order_phone(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        phone = validate_phone(message.text)
        if not phone:
            await bot.send_message(message.chat.id, f'Некорректный номер: {message.text}')
            message.text = back_message
            await Order.surname.set()
            await order_surname(message, state)

        else:
            await state.update_data(phone=phone)
            keyboard = get_mydefault_keyboard()
            button_yes = types.KeyboardButton('Да')
            button_no = types.KeyboardButton('Нет')
            keyboard.add(button_yes, button_no)
            await bot.send_message(message.chat.id, "Хотите оставить коментарий?", reply_markup=keyboard)
            await Order.next()
    else:
        keyboard = get_mydefault_keyboard()
        button_yes = types.KeyboardButton('Да')
        button_no = types.KeyboardButton('Нет')
        keyboard.add(button_yes, button_no)
        await bot.send_message(message.chat.id, "Хотите оставить коментарий?", reply_markup=keyboard)
        await Order.next()


async def order_back_to_phone(message: types.Message, state: FSMContext):
    await Order.phone.set()
    await order_phone(message, state)


async def order_choose_comment(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        await bot.send_message(message.chat.id, 'Введите свой комментайрий:', reply_markup=get_mydefault_keyboard())
        await Order.next()
    else:
        keyboard = get_mydefault_keyboard()
        button_outlet = types.KeyboardButton('До пункта выдачи')
        button_door = types.KeyboardButton('До двери')
        button_courier = types.KeyboardButton('Курьер по г. Минск')
        keyboard.add(button_outlet, button_door)
        keyboard.row(button_courier)
        if not message.text == back_message:
            await state.update_data(comment=None)
        await bot.send_message(message.chat.id, "Выберите тип доставки", reply_markup=keyboard)
        await Order.choose_delivery.set()


async def order_back_to_choose_comment(message: types.Message, state: FSMContext):
    await Order.choose_comment.set()
    await order_choose_comment(message, state)


async def order_comment(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(comment=message.text)

    keyboard = get_mydefault_keyboard()
    button_outlet = types.KeyboardButton('До пункта выдачи')
    button_door = types.KeyboardButton('До двери')
    button_courier = types.KeyboardButton('Курьер по г. Минск')
    keyboard.add(button_outlet, button_door)
    keyboard.row(button_courier)
    await bot.send_message(message.chat.id, "Выберите тип доставки", reply_markup=keyboard)
    await Order.next()


async def order_choose_delivery(message: types.Message, state: FSMContext, region_flag=False):
    if message.text == 'До двери' or region_flag:
        await state.update_data(choose_delivery='to_door')
        regions = await sync_to_async(list)(
            Region.objects.all())  # https://forum.djangoproject.com/t/asynchronous-orm/5925?page=3
        keyboard = get_mydefault_keyboard()
        for region in regions:
            keyboard.add(region.title)
        await bot.send_message(message.chat.id, 'Выберите область', reply_markup=keyboard)
        await Order.choose_region.set()

    elif message.text == 'Курьер по г. Минск':
        await bot.send_message(message.chat.id, 'Введите название улицы для доставки', reply_markup=get_mydefault_keyboard())
        await state.update_data(choose_delivery='courier')
        await Order.address.set()

    else:
        keyboard = get_mydefault_keyboard()
        companys = await sync_to_async(list)(DeliveryCompany.objects.all())
        for company in companys:
            keyboard.add(company.name)
        await bot.send_message(message.chat.id, 'Выберите курьерскую службу', reply_markup=keyboard)
        if not message.text == back_message:
            await state.update_data(choose_delivery='outlet')
        await Order.choose_delivery_company.set()


async def order_back_to_choose_delivery(message: types.Message, state: FSMContext):
    await Order.comment.set()
    await order_comment(message, state)


async def order_choose_delivery_company(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(order_choose_delivery_company=message.text)

    user_data = await state.get_data()
    company = await sync_to_async(DeliveryCompany.objects.get)(name=user_data['order_choose_delivery_company'])


    outlet_locations = await sync_to_async(list)(OutletLocation.objects.filter(company=company))

    if not len(outlet_locations) > 99:
        keyboard = get_mydefault_keyboard()
        for location in outlet_locations:
            keyboard.add(location.address)
        await bot.send_message(message.chat.id, 'Выберите пункт доставки', reply_markup=keyboard)
        await Order.choose_outlet.set()
    else:
        keyboard = get_mydefault_keyboard()
        for location in outlet_locations:
            keyboard.add(location.area)
        await bot.send_message(message.chat.id, 'Выберите место', reply_markup=keyboard)
        await Order.choose_outlet_area.set()


async def order_choose_outlet_area(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(order_choose_delivery_company=message.text)

    user_data = await state.get_data()
    print('123413')

    outlet_locations = await sync_to_async(list)(OutletLocation.objects.filter(company__name=user_data['order_choose_delivery_company']).filter(area=message.text))

    keyboard = get_mydefault_keyboard()
    for location in outlet_locations:
        keyboard.add(location.address)
    await bot.send_message(message.chat.id, 'Выберите пункт доставки', reply_markup=keyboard)
    await Order.choose_outlet.set()


async def order_choose_region(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    region = user_data.get('choose_region')
    if not message.text == back_message:
        if not region:
            region = message.text
        await state.update_data(choose_region=region)
        user_data = await state.get_data()
        region = user_data['choose_region']
        areas = await sync_to_async(list)(Area.objects.filter(region__title=region))
        keyboard = get_mydefault_keyboard()
        for area in areas:
            keyboard.add(area.title)
        await bot.send_message(message.chat.id, 'Выберите район', reply_markup=keyboard)
        await Order.next()
    else:
        if user_data['choose_delivery'] != 'courier':
            user_data = await state.get_data()
            region = user_data['choose_region']
            areas = await sync_to_async(list)(Area.objects.filter(region__title=region))
            keyboard = get_mydefault_keyboard()
            for area in areas:
                keyboard.add(area.title)
            await bot.send_message(message.chat.id, 'Выберите район', reply_markup=keyboard)
            await Order.next()

        else:
            await Order.comment.set()
            await order_comment(message, state)


async def order_back_to_choose_region(message: types.Message, state: FSMContext):
    await Order.choose_delivery.set()
    await order_choose_delivery(message, state, region_flag=True)


async def order_choose_area(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        area = message.text
        await state.update_data(choose_area=area)
    else:
        user_data = await state.get_data()
        area = user_data['choose_area']

    cities = await sync_to_async(list)(City.objects.filter(area__title=area))
    keyboard = get_mydefault_keyboard()
    for city in cities:
        keyboard.add(city.title)
    await bot.send_message(message.chat.id, 'Выберите город', reply_markup=keyboard)
    await Order.next()


async def order_back_to_choose_area(message: types.Message, state: FSMContext):
    await Order.choose_region.set()
    await order_choose_region(message, state)


async def order_choose_city(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        city = message.text
        await state.update_data(choose_city=city)


    await bot.send_message(message.chat.id, 'Введите название улицы для доставки', reply_markup=get_mydefault_keyboard())
    if not message.text == back_message:
        await state.update_data(choose_delivery='to_door')
    await Order.address.set()


async def order_back_to_choose_city(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    print('test')
    print(user_data.get('order_choose_delivery_company'))
    await Order.choose_area.set()
    await order_choose_area(message, state)


async def order_choose_address(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        outlet_address = message.text
        await state.update_data(outlet_address=outlet_address)
        await state.update_data(address=None)
    else:
        user_data = await state.get_data()
        outlet_address = user_data['outlet_address']
    user_data = await state.get_data()
    await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
    confirm_text = f"Номер заказа: {user_data['number']}; \n" \
                   f"ФИО: {user_data['surname']}; \n" \
                   f"Номер телефона: {user_data['phone']}; \n" \
                   f"комментарий: {user_data.get('comment')}; \n" \
                   f"тип доставки: {user_data['choose_delivery']}; \n" \
                   f"Курьерская служба: {user_data['order_choose_delivery_company']}; \n" \
                   f"адрес пункта самовывоза: {user_data['outlet_address']}"
    keyboard = get_mydefault_keyboard()
    button_yes = types.KeyboardButton('Да, информация верна')
    button_no = types.KeyboardButton('Нет, начать заново')
    keyboard.add(button_yes, button_no)
    await bot.send_message(message.chat.id, confirm_text, reply_markup=keyboard)
    await Order.confirm.set()


async def order_delivery_address(message: types.Message, state: FSMContext):
    if not message.text == back_message:
        await state.update_data(address=message.text)
        await state.update_data(choose_outlet=None)

    await bot.send_message(message.chat.id, 'Введите номер дома и квартира')
    await Order.house.set()


async def order_house(message: types.Message, state: FSMContext):
    if message.text != back_message:
        await state.update_data(house=message.text)

    user_data = await state.get_data()
    await bot.send_message(message.chat.id, 'Подтвердите введенную информацию:')
    if user_data.get('choose_region'):
        address = f"адресс доставки: {user_data.get('choose_region')} {user_data['choose_area']}" \
                       f" {user_data['choose_city']} {user_data['address']} {user_data['house']}"
    else:
        address = f"{user_data['address']} {user_data['house']}"
    confirm_text = f"Номер заказа: {user_data['number']}; \n" \
                   f"ФИО: {user_data['surname']}; \n" \
                   f"Номер телефона: {user_data['phone']}; \n" \
                   f"комментарий: {user_data.get('comment')}; \n" \
                   f"тип доставки: {user_data['choose_delivery']}; \n" \
                   f"{address}"
    keyboard = get_mydefault_keyboard()
    button_yes = types.KeyboardButton('Да, информация верна')
    button_no = types.KeyboardButton('Нет, начать заново')
    keyboard.add(button_yes, button_no)
    await bot.send_message(message.chat.id, confirm_text, reply_markup=keyboard)
    await Order.confirm.set()


async def order_back_to_house(message: types.Message, state: FSMContext):
    await Order.address.set()
    await order_delivery_address(message, state)

async def order_back_to_street(message: types.Message, state: FSMContext):
    await Order.choose_city.set()
    await order_choose_city(message, state)


async def order_confirm(message: types.Message, state: FSMContext):
    if message.text == 'Да, информация верна':
        user_data = await state.get_data()
        user_id = message.from_user.id
        username = message.from_user.username
        await create_order(user_data, user_id, username)

        await bot.send_message(message.chat.id, 'Заказ подтвержден, менерджер с вами свяжется', reply_markup=get_start_keyboard())
    elif message.text == 'Нет, начать заново':
        await bot.send_message(message.chat.id, 'Начните заново', reply_markup=get_start_keyboard())
    else:
        await bot.send_message(message.chat.id, 'Пожлуйста, используйте клавиатуру для ответа')
    await state.finish()


async def order_error(message: types.Message, state: FSMContext):
    return await bot.send_message(message.chat.id, 'Пожалуйста, используйте клавиатуру')


@sync_to_async
def create_order(user_data, user_id, usermame):
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

    new_order = PersonalOrder.objects.create(
        code=user_data['number'],
        tel_number=user_data['phone'],
        comment=user_data['comment'],
        delivery_type=delivery_type,
        delivery_address=delivery_address,
        creator_id=user_id,
        delivery_outlet=outlet_location,
        fio=user_data['surname']
    )
    new_order.save()


    split_fio = user_data['surname'].split()
    if new_order.delivery_address:
        bitrix_address = new_order.delivery_address
    else:
        bitrix_address = outlet_location.address

    # create deal in bitrix
    bitrix_last_name = split_fio[0:1][0] if split_fio[0:1] else ''
    bitrix_first_name = split_fio[1:2][0] if split_fio[1:2] else ''
    bitrix_second_name = split_fio[2:3][0] if split_fio[2:3] else ''
    deal_title = f"Индивидуальный заказ №{user_data['number']}"
    deal_params = {'fields': {
                        'TITLE': deal_title,
                        'TYPE_ID': 'GOODS',
                        'STAGE_ID': 'NEW',
                        'PROBABILITY': None,
                        'ASSIGNED_BY_ID': '',
                        'COMMENTS': 'Коммент1',
                        'IS_NEW': 'N',
                        'SOURCE_ID': '2|TELEGRAM',
                        'SOURCE_DESCRIPTION': 'Индивидуальный заказ',
                        'UF_CRM_6036424E7B4F9': f'{user_id}',
                        'UF_CRM_6036424EA0F45': f"{user_data['number']}",
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
            "PHONE": [ { "VALUE": user_data['phone'], } ],
            "UF_CRM_1614170717684": user_id,  # telegram ID
        }}
    requests.post(f"https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.contact.add", json=contact_params)

    # get this deal
    r = requests.get(f"https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/crm.deal.list?filter[TITLE]={deal_title}")
    list_of_dicts = json.loads(r.text)['result']
    this_deal_id = list(filter(lambda dic: dic['TITLE'] == f"Индивидуальный заказ №{user_data['number']}", list_of_dicts))[0]['ID']

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


def register_individual_order(dp: Dispatcher):
    dp.register_message_handler(start_order, text=['🚚 индивидуальный заказ'], state=['*'])
    dp.register_message_handler(start_order, commands=['order'], state=['*'])

    dp.register_message_handler(order_number, state=[Order.number])
    dp.register_message_handler(order_back_to_start, text=back_message, state=[Order.surname])

    dp.register_message_handler(order_surname, state=[Order.surname])
    dp.register_message_handler(order_back_to_number, text=back_message, state=[Order.phone])

    dp.register_message_handler(order_phone, state=[Order.phone])
    dp.register_message_handler(order_back_to_surname, text=back_message, state=[Order.choose_comment])

    dp.register_message_handler(order_choose_comment,
                                lambda message: message.text in ['Да', 'Нет'],
                                state=Order.choose_comment)
    dp.register_message_handler(order_back_to_choose_comment, text=back_message, state=[Order.comment])

    dp.register_message_handler(order_comment, state=Order.comment)
    dp.register_message_handler(order_back_to_phone, text=back_message, state=[Order.choose_delivery])

    dp.register_message_handler(order_choose_delivery,
                                lambda message: message.text in ['До пункта выдачи', 'До двери', 'Курьер по г. Минск'],
                                state=Order.choose_delivery)
    dp.register_message_handler(order_back_to_choose_area, text=back_message, state=Order.address)
    dp.register_message_handler(order_back_to_choose_delivery, text=back_message, state=Order.choose_delivery_company)

    dp.register_message_handler(order_choose_delivery_company, state=Order.choose_delivery_company)
    dp.register_message_handler(order_back_to_choose_delivery, text=back_message, state=Order.choose_region)

    dp.register_message_handler(order_choose_region, state=Order.choose_region)
    dp.register_message_handler(order_back_to_choose_region, text=back_message, state=Order.choose_area)

    dp.register_message_handler(order_choose_area, state=Order.choose_area)
    dp.register_message_handler(order_back_to_choose_area, text=back_message, state=Order.choose_city)

    dp.register_message_handler(order_choose_city, state=Order.choose_city)
    dp.register_message_handler(order_back_to_choose_delivery, text=back_message, state=Order.choose_outlet)

    dp.register_message_handler(order_choose_outlet_area, state=Order.choose_outlet_area)

    dp.register_message_handler(order_choose_address, state=Order.choose_outlet)

    dp.register_message_handler(order_delivery_address, state=Order.address)
    dp.register_message_handler(order_back_to_street, text=back_message, state=Order.address)

    dp.register_message_handler(order_back_to_street, text=back_message, state=Order.house)
    dp.register_message_handler(order_house, state=Order.house)


    dp.register_message_handler(order_confirm,
                                lambda message: message.text in ['Да, информация верна'],
                                state=Order.confirm)
    dp.register_message_handler(order_back_to_choose_delivery, text=back_message, state=Order.confirm)

    dp.register_message_handler(order_error, state=[Order.confirm, Order.choose_delivery, Order.choose_comment])

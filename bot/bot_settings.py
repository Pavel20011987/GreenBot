from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext

TOKEN = '2128827561:AAFF0afvhyX56EHqgncSfyjJBcc9e5yw2kw'
bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

bitrix_24 = 'https://greenway.bitrix24.by/'
bitrix_webhook = 'https://greenway.bitrix24.by/rest/28/lf8g9h3w7koiuvrz/'

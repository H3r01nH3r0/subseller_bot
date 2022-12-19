from aiogram import Bot, Dispatcher, types, filters, executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils import get_config, save_config, str2file, create_promo
from database import DataBase
from nav import Keyboards
from pyqiwip2p import QiwiP2P
from asyncio import sleep
import asyncio
import random
import time
import pyqiwi
import string

config_filename = 'config.json'
config = get_config(config_filename)
db = DataBase(config['db_file'])
keyboards = Keyboards(db, config['keyboards'])
bot = Bot(token=config['token'], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
owners_filter = filters.IDFilter(user_id=config['owners'])
p2p = QiwiP2P(auth_key=config['QIWI_TOKEN'])
waiting_for_payment = dict()


class Form(StatesGroup):
    mailing = State()
    mailing_markup = State()
    user_id = State()
    promo_time = State()
    promo_uses = State()
    promo_discount = State()
    new_tariff = State()
    new_tariff_channel_id = State()
    new_tariff_price = State()
    new_tariff_time = State()
    change_tariff = State()
    change_name = State()
    change_channel_id = State()
    change_price = State()
    change_time = State()
    qiwi = State()
    user_promo = State()
    channel_name = State()
    set_user_percent = State()
    set_admin_percent = State()
    set_count_of_refs = State()


async def process(users: list, kwargs: dict):
    total = 0
    sent = 0
    unsent = 0
    for user in users:
        kwargs['chat_id'] = user
        try:
            await bot.copy_message(**kwargs)
            sent += 1
        except:
            unsent += 1
        await sleep(config["sleep_time"])
        total += 1
    return total, sent, unsent

async def sub_proc(users: list, kwargs: dict):
    number = len(users) // 5
    t = 0
    s = 0
    u = 0
    for total, sent, unsent in await asyncio.gather(
        process(users[:number], kwargs),
        process(users[number:2 * number], kwargs),
        process(users[2 * number:3 * number], kwargs),
        process(users[3 * number:4 * number], kwargs),
        process(users[4 * number:], kwargs)
    ):
        t += total
        s += sent
        u += unsent
    return t, s, u

async def on_startup():
    try:
        while True:
            await sleep(86400)
            data = db.check_all_subs()
            if data:
                for user in data:
                    for channel, date in data[user]:
                        new_date = date - 1
                        db.update_time_of_subscription(user, channel, new_date)
                        if 0 < new_date <= 3:
                            channel_info = await bot.get_chat(channel)
                            channel_name = channel_info['title']
                            await bot.send_message(user, text=config['texts']['alert'].format(channel_name, new_date))
                        elif new_date == 0:
                            db.del_sub(user, channel)
                            db.change_sub_status(user, False)
                            await bot.kick_chat_member(channel, user)
                            await bot.send_message(user, text=config['texts']['kicked'])
    except Exception as a:
        print(a)


async def on_shutdown(dp: Dispatcher) -> None:
    save_config(config_filename, config)


async def create_url(user_id, chat, date):
    try:
        await bot.unban_chat_member(chat, user_id, True)
        db.change_sub_status(user_id, True)
        link = await bot.create_chat_invite_link(chat, member_limit=1)
        info = db.check_subscription(user_id, chat)
        if info:
            new_date = date + info[0]
            db.update_time_of_subscription(user_id, chat, new_date)
            return False
        else:
            db.add_sub(user_id, chat, link.invite_link, date)
            return link.invite_link
    except Exception as a:
        print(a)


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    try:
        args = message.text.split(' ')[1:]
        if not db.check_user(message.from_user.id):
            if len(args) < 1:
                db.add_user(message.from_user.id, message.from_user.username)
            else:
                args = args[0]
                if args.startswith('__'):
                    link = f'https://t.me/{config["bot_user_name"]}?start={args}'
                    count = db.get_act_adm_ref(link) + 1
                    db.act_adm_ref(link, count)
                    db.add_user(message.from_user.id, message.from_user.username)
                    db.update_user_refer(message.from_user.id, link)
                else:
                    count = db.get_act_user_ref(args) + 1
                    db.act_user_ref(int(args), count)
                    db.update_invited(int(args), count)
                    db.add_user(message.from_user.id, message.from_user.username)
                    db.update_user_refer(message.from_user.id, args)
        await message.answer(
            text=config['texts']['hello'],
            reply_markup=keyboards.menu('main_menu')
        )
    except Exception as a:
        print(a)


@dp.message_handler(owners_filter, commands=["admin"])
async def start_handler(message: types.Message):
    try:
        await message.answer(
            text=config['texts']['hello_admin'],
            reply_markup=keyboards.menu('admin_panel')
        )
    except Exception as a:
        print(a)


@dp.callback_query_handler(state="*")
async def callback_query_hanbler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user = callback_query.from_user.id
        admin_id = 0
        if user in config['owners']:
            admin_id = user

        if callback_query.data == 'support':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user,
                text=config['texts']['support'],
                reply_markup=keyboards.cancel_1()
            )

        elif callback_query.data == 'about':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user, text=config['texts']['about'],
                reply_markup=keyboards.cancel_1()
            )

        elif callback_query.data == 'cabinet':
            user_id = user
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            user_info = db.find_out(user_id)
            if user_info == 'sub':
                subs = ''
                channels = db.info_sub_links(user)
                for link, date in channels:
                    x = '{}\t{} дней\n'.format(link, date)
                    subs += x
                user_info = db.get_user_info(user_id)[0]
                await bot.send_message(user,
                                       text=config['texts']['cabinet'] + config['texts']['sub_info'].format(
                                           user_info[2], user_info[1], subs, user_info[6]),
                                       reply_markup=keyboards.cancel_1())
            elif user_info == 'user':
                info = db.get_user_info(user_id)[0]
                await bot.send_message(user,
                                       text=config['texts']['cabinet'] + config['texts']['user_info'].format(
                                           info[2], info[1], info[6]),
                                       reply_markup=keyboards.cancel_1())

        elif callback_query.data == 'ref_link':
            db.create_user_ref(user)
            need_to_invite = config['need_friends'] - db.get_invited(user)[0]
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            if need_to_invite > 0:
                await bot.send_message(
                    user,
                    text=config['texts']['ref_link'].format(
                        str(config['discount_value']), config['bot_user_name'], user, need_to_invite
                    ),
                    reply_markup=keyboards.cancel_1()
                )
            elif need_to_invite == 0:
                await bot.send_message(
                    user,
                    text=config['texts']['refed'].format(str(config['discount_value']), config['bot_user_name'], user)
                )

        elif callback_query.data == 'tariffs':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user,
                text=config['texts']['subscribes'],
                reply_markup=keyboards.tariffs()
            )

        elif callback_query.data == "YES":
            await Form.user_promo.set()
            await bot.send_message(
                user,
                text=config['texts']['input_promo'],
                reply_markup=keyboards.cancel_1()
            )

        elif callback_query.data == 'NO':
            need_to_invite = config['need_friends'] - db.get_invited(user)[0]
            discount = 0
            if need_to_invite <= 0:
                discount = config['discount_value']
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            tariff = config['tariffs'][waiting_for_payment[user]]
            comment = str(callback_query.from_user.id) + str(random.randint(1000, 9000))
            amount = tariff[2] - (tariff[2] * discount / 100)
            bill = p2p.bill(amount=int(amount), lifetime=config['life_time'], comment=comment)
            db.add_check(callback_query.from_user.id, tariff[2], bill.bill_id)

            await bot.send_message(
                user,
                text=config['texts']['tariff'].format(tariff[3], tariff[2]),
                reply_markup=keyboards.pay_menu(url=bill.pay_url, bill=bill.bill_id)
            )

        elif callback_query.data.startswith('tariff_'):

            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id)

            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['use_promo'],
                reply_markup=keyboards.menu('use_promo')
            )
            waiting_for_payment[user] = callback_query.data

        elif callback_query.data.startswith('check_'):
            bill = callback_query.data.split('_')[1]
            info = db.get_check(bill)
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            if info:
                if str(p2p.check(bill_id=bill).status) == 'PAID':
                    db.delete_check(bill)
                    tariff = waiting_for_payment[user]
                    refer = db.get_user_refer(user)
                    if int(refer):
                        if refer.startswith('https://t.me/'):
                            money = db.get_adm_refs_money(refer)
                            new_money = money + (config['tariffs'][tariff][2] * config['percent_for_admins'] / 100)
                            db.buy_adm_ref(refer, new_money)
                        else:
                            money = db.get_user_refs_money(int(refer))
                            new_money = money + config['tariffs'][tariff][2]
                            db.buy_user_ref(int(refer), new_money)
                    date = config['tariffs'][tariff][3]
                    channel_id = config['tariffs'][tariff][1]
                    url = await create_url(user, channel_id, date)
                    if url:
                        await bot.send_message(
                            user,
                            text=config['texts']['payed'],
                            reply_markup=keyboards.link(url)
                        )
                    else:
                        await bot.send_message(
                            user,
                            text=config['texts']['continued']
                        )
                    del waiting_for_payment[user]
                else:
                    await bot.send_message(
                        user,
                        text=config['texts']['unpayed'],
                        reply_markup=keyboards.pay_menu(False, bill=bill)
                    )
            else:
                await bot.send_message(
                    user,
                    text=config['texts']['cannot_find']
                )

        elif callback_query.data == 'create_ref_link':
            await Form.channel_name.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['insert_channel_name'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'user_cancel':
            await state.finish()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('main_menu')
            )

        elif callback_query.data.startswith('cancel_'):
            bill = callback_query.data.split('_')[1]
            db.delete_check(bill)
            if user in waiting_for_payment.keys():
                del waiting_for_payment[user]
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('main_menu')
            )

        elif callback_query.data == 'count':
            count = db.get_users_count()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['users_count'].format(count),
                reply_markup=keyboards.menu('admin_panel')
            )

        elif callback_query.data == 'count_subs':
            subs_count = db.get_subs_count()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['subs_count'].format(subs_count),
                reply_markup=keyboards.menu('admin_panel')
            )

        elif callback_query.data == 'mail':
            await Form.mailing.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config["texts"]["enter_mailing"],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'create_promo':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['promo_type'],
                reply_markup=keyboards.menu('promo_type')
            )

        elif callback_query.data == 'time_promo':
            await Form.promo_time.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['insert_time'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'uses_promo':
            await Form.promo_uses.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['insert_uses'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'adm_check_balance':
            wallet = pyqiwi.Wallet(config['_token'], config['_number'])
            balance = wallet.balance()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['qiwi_balance'].format(balance),
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'admin_cancel':
            await state.finish()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('admin_panel')
            )

        elif callback_query.data == 'no':
            await state.finish()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('admin_panel')
            )

        elif callback_query.data == 'yes':

            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )

            async with state.proxy() as data:
                time_1 = data["time"]
                price = data["price"]
                channel_id = data["channel_id"]
                name = data["tariff_name"]
                idx = data["tariff_idx"]

            config['tariffs'][idx] = [name, channel_id, price, time_1]
            config['keyboards']['tariffs'][idx] = name
            save_config(config_filename, config)

            await bot.send_message(
                admin_id,
                text=config['texts']['changes_saved']
            )
            await state.finish()

        elif callback_query.data == 'change_qiwi':
            await Form.qiwi.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['choose_qiwi'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'change_tariff':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['create_or_change'],
                reply_markup=keyboards.menu('create_or_change')
            )

        elif callback_query.data == 'create':
            await Form.new_tariff.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['insert_new_tariff'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'change':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['choose_tariff_to_change'],
                reply_markup=keyboards.tariffs(change=True)
            )

        elif callback_query.data.startswith('change_tariff_'):
            data = callback_query.data.split('_')
            tariff = 'tariff_' + data[2]
            tariff_info = config['tariffs'][tariff]
            async with state.proxy() as data:
                data["tariff"] = tariff
            await Form.change_tariff.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['tariff_info'].format(
                    tariff_info[0], tariff_info[1], tariff_info[2], tariff_info[3]
                ),
                reply_markup=keyboards.menu('changing_tariff')
            )

        elif callback_query.data == 'change_go_back' or callback_query.data == 'delete_go_back':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                user,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('main_menu')
            )

        elif callback_query.data == 'change_name':
            await Form.change_name.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['change_name'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'change_channel_id':
            await Form.change_channel_id.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['change_channel_id'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'change_price':
            await Form.change_price.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['change_price'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'change_time':
            await Form.change_time.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['change_time'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'save_changes':
            save_config(config_filename, config)
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['changes_saved']
            )
            await state.finish()

        elif callback_query.data == 'delete':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['choose_tariff_to_delete'],
                reply_markup=keyboards.tariffs(delete=True)
            )

        elif callback_query.data.startswith('delete_tariff_'):
            tariff = callback_query.data.split('_')
            idx = tariff[1] + '_' + tariff[-1]
            del config['tariffs'][idx]
            del config['keyboards']['tariffs'][idx]
            save_config(config_filename, config)

            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['changes_saved']
            )

        elif callback_query.data == "go_back":
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['go_back'],
                reply_markup=keyboards.menu('main_menu')
            )

        elif callback_query.data == 'export_subs':
            msg = await bot.send_message(admin_id, text=config["texts"]["please_wait"])
            file = str2file(" ".join([str(user[0]) for user in db.get_subs()]), "users.txt")
            try:
                await bot.send_document(admin_id, file)
            except:
                await bot.send_message(admin_id, text=config["texts"]["no_users"])
            await msg.delete()

        elif callback_query.data == 'find_out':
            await Form.user_id.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['enter_user_id'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'update_percentage_ind':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['ref_param'],
                reply_markup=keyboards.menu('ref_param')
            )

        elif callback_query.data == 'user_percent':
            await Form.set_user_percent.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['set_user_percent'],
                reply_markup=keyboards.cancel()
            )
        elif callback_query.data == 'user_count_refs':
            await Form.set_count_of_refs.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['set_count_of_refs'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'set_admins_percent':
            await Form.set_admin_percent.set()
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['set_admin_percent'],
                reply_markup=keyboards.cancel()
            )

        elif callback_query.data == 'save':
            async with state.proxy() as data:
                for i in data:
                    if i == "set_count_of_refs":
                        count = data["set_count_of_refs"]
                        config['need_friends'] = count
                    elif i == "set_user_percent":
                        percent = data["set_user_percent"]
                        config['discount_value'] = percent
                    elif i == "set_admin_percent":
                        percent = data["set_admin_percent"]
                        config['percent_for_admins'] = percent
            save_config(config_filename, config)
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['saved'],
                reply_markup=keyboards.menu('admin_panel')
            )
            await state.finish()

        elif callback_query.data == 'not':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            await bot.send_message(
                admin_id,
                text=config['texts']['canceled'],
                reply_markup=keyboards.menu('admin_panel')
            )
            await state.finish()

        elif callback_query.data == 'show_referals':
            await bot.delete_message(
                callback_query.from_user.id,
                callback_query.message.message_id
            )
            users = db.get_users_refs()
            channels = db.get_channels_refs()
            referals = "ПОЛЬЗОВАТЕЛИ\n\n"
            referals = referals + '=' * 100 + '\n\n'
            referals += 'user_id\t\t\t\tactivates\t\t\tmoney\n\n'
            for user_id, act, money in users:
                referals += f'{str(user_id)}\t\t\t{str(act)}\t\t\t\t{str(money)}\n'
            referals = referals + '=' * 100 + '\n\n'
            referals += "КАНАЛЫ\n\n"
            referals = referals + '=' * 100 + '\n\n'
            referals += 'channel\t\t\t\tactivates\t\t\tmoney(к выплате)\n\n'
            for channel, act, money in channels:
                referals += f'{str(channel)}\t\t\t{str(act)}\t\t\t\t{str(money)}\n'
            referals = referals + '=' * 100 + '\n\n'
            file = str2file(referals, 'referals.txt')
            try:
                await bot.send_document(admin_id, file)
            except:
                await bot.send_message(admin_id, text=config["texts"]["no_users"])

    except Exception as a:
        print(a)




@dp.message_handler(content_types=types.ContentType.all(), state=Form.set_user_percent)
async def owners_process_set_user_percent(message: types.Message, state: FSMContext):
    try:
        try:
            percent = int(message.text)
            async with state.proxy() as data:
                data["set_user_percent"] = percent
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['ask_change_user_percent'].format(percent),
                reply_markup=keyboards.menu('save_dont_save')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)

@dp.message_handler(content_types=types.ContentType.all(), state=Form.set_count_of_refs)
async def owners_process_channel_name(message: types.Message, state: FSMContext):
    try:
        try:
            count = int(message.text)
            async with state.proxy() as data:
                data["set_count_of_refs"] = count
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['ask_change_user_count'].format(count),
                reply_markup=keyboards.menu('save_dont_save')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)

@dp.message_handler(content_types=types.ContentType.all(), state=Form.set_admin_percent)
async def owners_process_set_admin_percent(message: types.Message, state: FSMContext):
    try:
        try:
            percent = int(message.text)
            async with state.proxy() as data:
                data["set_admin_percent"] = percent
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['ask_change_admin_percent'].format(percent),
                reply_markup=keyboards.menu('save_dont_save')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)

@dp.message_handler(content_types=types.ContentType.all(), state=Form.channel_name)
async def owners_process_channel_name(message: types.Message, state: FSMContext):
    try:
        channel_name = message.text
        chars = string.ascii_letters + string.digits
        password = '__'
        for i in range(10):
            password += random.choice(chars)
        link = f'https://t.me/{config["bot_user_name"]}?start={password}'
        db.create_adm_ref(channel_name, link)
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['link_generated'].format(config['bot_user_name'], password),
            reply_markup=keyboards.cancel()
        )
        await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.user_promo)
async def owners_process_user_promo(message: types.Message, state: FSMContext):
    try:
        promo = message.text
        if db.check_promo(promo):
            need_to_invite = config['need_friends'] - db.get_invited(message.from_user.id)[0]
            discount_1 = 0
            if need_to_invite <= 0:
                discount_1 = config['discount_value']
            discount = db.get_disc(promo)
            await bot.delete_message(
                message.from_user.id,
                message.message_id
            )
            tariff = config['tariffs'][waiting_for_payment[message.from_user.id]]
            comment = str(message.from_user.id) + str(random.randint(1000, 9000))
            amount = (tariff[2] * (1 - discount[0] / 100)) * (1 - discount_1/100)
            bill = p2p.bill(amount=int(amount), lifetime=config['life_time'], comment=comment)
            db.add_check(message.from_user.id, tariff[2], bill.bill_id)

            await bot.send_message(
                message.from_user.id,
                text=config['texts']['tariff'].format(tariff[3], str(int(amount))),
                reply_markup=keyboards.pay_menu(url=bill.pay_url, bill=bill.bill_id)
            )
            await state.finish()
        else:
            await Form.user_promo.set()
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['no_such_promo'],
                reply_markup=keyboards.cancel_1()
            )
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.new_tariff)
async def owners_process_new_tariff(message: types.Message, state: FSMContext):
    try:
        all_tariffs = sorted(list(config['tariffs']))
        latest_tariff = all_tariffs[-1]
        idx = int(latest_tariff.split('_')[-1]) + 1
        new_tariff_idx = 'tariff_' + str(idx)
        async with state.proxy() as data:
            data["tariff_name"] = message.text
            data["tariff_idx"] = new_tariff_idx
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['insert_new_id'],
            reply_markup=keyboards.cancel()
        )
        await Form.new_tariff_channel_id.set()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.new_tariff_channel_id)
async def owners_process_new_tariff_channel_id(message: types.Message, state: FSMContext):
    try:
        try:
            channel_id = int(message.text)
            async with state.proxy() as data:
                data["channel_id"] = channel_id
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['insert_new_price'],
                reply_markup=keyboards.cancel()
            )
            await Form.new_tariff_price.set()
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.new_tariff_price)
async def owners_process_new_tariff_price(message: types.Message, state: FSMContext):
    try:
        try:
            price = int(message.text)
            async with state.proxy() as data:
                data["price"] = price
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['insert_new_time'],
                reply_markup=keyboards.cancel()
            )
            await Form.new_tariff_time.set()
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.new_tariff_time)
async def owners_process_new_tariff_time(message: types.Message, state: FSMContext):
    try:
        try:
            time_1 = int(message.text)
            async with state.proxy() as data:
                data["time"] = time_1
                price = data["price"]
                channel_id = data["channel_id"]
                name = data["tariff_name"]
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['ask_create_new'].format(name, channel_id, price, time_1),
                reply_markup=keyboards.menu('yes_no')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.change_name)
async def owners_process_change_name(message: types.Message, state: FSMContext):
    try:
        new_tariff_name = message.text
        async with state.proxy() as data:
            tariff = data["tariff"]
        config['tariffs'][tariff][0] = new_tariff_name
        config['keyboards']['tariffs'][tariff] = new_tariff_name
        tariff_info = config['tariffs'][tariff]
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['tariff_info'].format(tariff_info[0], tariff_info[1], tariff_info[2], tariff_info[3]),
            reply_markup=keyboards.menu('changing_tariff')
        )
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.change_price)
async def owners_process_change_price(message: types.Message, state: FSMContext):
    try:
        new_tariff_price = message.text
        try:
            new_tariff_price = int(new_tariff_price)
            async with state.proxy() as data:
                tariff = data["tariff"]
            config['tariffs'][tariff][2] = new_tariff_price
            tariff_info = config['tariffs'][tariff]
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['tariff_info'].format(tariff_info[0], tariff_info[1], tariff_info[2], tariff_info[3]),
                reply_markup=keyboards.menu('changing_tariff')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.change_channel_id)
async def owners_process_change_channel_id(message: types.Message, state: FSMContext):
    try:
        new_tariff_channel_id = message.text
        try:
            new_tariff_channel_id = int(new_tariff_channel_id)
            async with state.proxy() as data:
                tariff = data["tariff"]
            config['tariffs'][tariff][1] = new_tariff_channel_id
            tariff_info = config['tariffs'][tariff]
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['tariff_info'].format(tariff_info[0], tariff_info[1], tariff_info[2], tariff_info[3]),
                reply_markup=keyboards.menu('changing_tariff')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.change_time)
async def owners_process_change_time(message: types.Message, state: FSMContext):
    try:
        new_tariff_time = message.text
        try:
            new_tariff_time = int(new_tariff_time)
            async with state.proxy() as data:
                tariff = data["tariff"]
            config['tariffs'][tariff][3] = new_tariff_time
            tariff_info = config['tariffs'][tariff]
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['tariff_info'].format(tariff_info[0], tariff_info[1], tariff_info[2], tariff_info[3]),
                reply_markup=keyboards.menu('changing_tariff')
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.user_id)
async def owners_process_find_user(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data["user_id"] = message.text
        try:
            user_id = int(data['user_id'])
            user_info = db.find_out(user_id)
            if user_info:
                if user_info == 'sub':
                    subs = ''
                    channels = db.info_sub_channels(user_id)
                    for channel_id, date in channels:
                        x = '{}\t{} дней\n'.format(channel_id, date)
                        subs = subs + x
                    user_info = db.get_user_info(user_id)[0]
                    await bot.send_message(
                        user_id,
                        text=config['texts']['sub_info'].format(
                            user_info[2], user_info[1], subs, user_info[6]
                        ),
                        reply_markup=keyboards.cancel())
                elif user_info == 'user':
                    info = db.get_user_info(user_id)[0]
                    await bot.send_message(
                        message.from_user.id,
                        text=config['texts']['user_info'].format(
                            info[2], info[1], info[6]
                        ),
                        reply_markup=keyboards.cancel()
                    )
            else:
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['no_user']
                )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_user_id']
            )
        await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.promo_time)
async def owners_process_promo_time(message: types.Message, state: FSMContext):
    try:
        promo_time = message.text
        try:
            promo_time = int(promo_time)
            promo = create_promo()
            async with state.proxy() as data:
                data["promo_time"] = promo_time
                data["promo"] = promo
                data["uses"] = False
            await Form.promo_discount.set()
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['insert_discount'],
                reply_markup=keyboards.cancel()
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.promo_uses)
async def owners_process_promo_uses(message: types.Message, state: FSMContext):
    try:
        promo_uses = message.text
        try:
            promo_uses = int(promo_uses)
            promo = create_promo()
            async with state.proxy() as data:
                data["promo_uses"] = promo_uses
                data["promo"] = promo
                data["uses"] = True
            await Form.promo_discount.set()
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['insert_discount'],
                reply_markup=keyboards.cancel()
            )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
            await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.promo_discount)
async def owners_process_promo_discount(message: types.Message, state: FSMContext):
    try:
        promo_discount = message.text
        try:
            promo_discount = int(promo_discount)
            async with state.proxy() as data:
                if data['uses']:
                    uses = data['promo_uses']
                    promo = data['promo']
                    db.add_promo_uses(promo, uses, promo_discount)
                    await bot.send_message(
                        message.from_user.id,
                        text=config['texts']['crated_uses'].format(promo, promo_discount, uses)
                    )
                elif not data['uses']:
                    time_1 = data['promo_time']
                    promo = data['promo']
                    db.add_promo_date(promo, time_1, promo_discount)
                    await bot.send_message(
                        message.from_user.id,
                        text=config['texts']['crated_time'].format(promo, promo_discount, time_1)
                    )
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
        await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.qiwi)
async def owners_process_qiwi(message: types.Message, state: FSMContext):
    try:
        new_qiwi = message.text.split('/')
        if len(new_qiwi) == 3:
            number, qiwiAPI, p2pqiwiAPI = new_qiwi[0], new_qiwi[1], new_qiwi[2]
            if number.startswith('79'):
                config["_number"] = number
                config["_token"] = qiwiAPI
                config["QIWI_TOKEN"] = p2pqiwiAPI
                save_config(config_filename, config)
                await bot.delete_message(
                    message.from_user.id,
                    message.message_id
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['saved']
                )
            else:
                await bot.delete_message(
                    message.from_user.id,
                    message.message_id
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['invalid_number']
                )
        else:
            await bot.delete_message(
                message.from_user.id,
                message.message_id
            )
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['invalid_number']
            )
        await state.finish()
    except Exception as a:
        print(a)


@dp.message_handler(content_types=types.ContentType.all(), state=Form.mailing)
async def owners_process_mailing_handler(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data["message"] = message.to_python()
        await Form.mailing_markup.set()
        await message.answer(
            config["texts"]["enter_mailing_markup"],
            reply_markup=keyboards.cancel()
        )
    except Exception as a:
        print(a)


@dp.message_handler(state=Form.mailing_markup)
async def owners_process_mailing_markup_handler(message: types.Message, state: FSMContext) -> None:

    try:
        if message.text not in ["-", "."]:
            try:
                markup = keyboards.from_str(message.text)
            except:
                await message.answer(
                    text=config["texts"]["incorrect_mailing_markup"],
                    reply_markup=keyboards.cancel()
                )
                return
        else:
            markup = types.InlineKeyboardMarkup()
        markup = markup.to_python()
        async with state.proxy() as data:
            _message = data["message"]

        await state.finish()
        await message.answer(config["texts"]["start_mailing"])
        started = time.time()
        kwargs = {
            "from_chat_id": _message["chat"]["id"],
            "message_id": _message["message_id"],
            "reply_markup": markup
        }
        user_list = [user[0] for user in db.get_users()]

        total, sent, unsent = await sub_proc(user_list, kwargs)

        await message.answer(
            config["texts"]["mailing_stats"].format(
                total=total,
                sent=sent,
                unsent=unsent,
                time=round(time.time() - started, 3)
            )
        )
    except Exception as a:
        print(a)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup())
    executor.start_polling(dispatcher=dp, skip_updates=False, on_shutdown=on_shutdown)

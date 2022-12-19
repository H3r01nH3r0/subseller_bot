from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class Keyboards:
    def __init__(self, db, texts):
        self.db = db
        self.texts = texts

    def menu(self, category):
        markup = InlineKeyboardMarkup()
        for key, value in self.texts[category].items():
            markup.add(InlineKeyboardButton(text=value, callback_data=key))
        return markup

    def tariffs(self, change=False, delete=False):
        if change:
            markup = InlineKeyboardMarkup()
            for key, value in self.texts['tariffs'].items():
                markup.add(InlineKeyboardButton(text=value, callback_data='change_' + key))
            markup.add(InlineKeyboardButton(text="Назад", callback_data="go_back"))
            return markup
        elif delete:
            markup = InlineKeyboardMarkup()
            for key, value in self.texts['tariffs'].items():
                markup.add(InlineKeyboardButton(text=value, callback_data='delete_' + key))
            markup.add(InlineKeyboardButton(text="Назад", callback_data="go_back"))
            return markup
        else:
            markup = InlineKeyboardMarkup()
            for key, value in self.texts['tariffs'].items():
                markup.add(InlineKeyboardButton(text=value, callback_data=key))
            markup.add(InlineKeyboardButton(text="Назад", callback_data="go_back"))
            return markup

    def pay_menu(self, isUrl=True, url='', bill=''):
        markup = InlineKeyboardMarkup()
        if isUrl:
            markup.add(InlineKeyboardButton(text=self.texts['payment']['pay'], url=url))
        markup.add(InlineKeyboardButton(text=self.texts['payment']['check'], callback_data='check_' + bill))
        markup.add(InlineKeyboardButton(text=self.texts['payment']['cancel'], callback_data='cancel_' + bill))
        return markup

    def link(self, URL):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.texts['personal_link'], url=URL))
        return markup

    def cancel(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.texts["cancel"], callback_data="admin_cancel"))
        return markup

    def cancel_1(self) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.texts["cancel"], callback_data="user_cancel"))
        return markup

    @staticmethod
    def from_str(text: str) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        for line in text.split("\n"):
            sign, url = line.split(" - ")
            markup.add(InlineKeyboardButton(text=sign, url=url))
        markup.to_python()
        return markup

import sqlite3
from datetime import datetime
from time import sleep
import threading


class DataBase:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            user_name VARCHAR,
            all_subs VARCHAR,
            sub_status BOOLEAN NOT NULL DEFAULT(FALSE),
            invited INTEGER NOT NULL DEFAULT(0),
            activation_date VARCHAR NOT NULL,
            refer VARCHAR DEFAULT(FALSE)
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo VARCHAR NOT NULL,
            uses INTEGER NOT NULL,
            disc INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT(0)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_name VARCHAR NOT NULL,
            link VARCHAR NOT NULL,
            activated INTEGER NOT NULL DEFAULT(0),
            money INTEGER NOT NULL DEFAULT(0)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activated INTEGER NOT NULL DEFAULT(0),
            money INTEGER NOT NULL DEFAULT(0)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS promo_date (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo VARCHAR NOT NULL,
            date INTEGER NOT NULL,
            disc INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT(0)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            link VARCHAR NOT NULL,
            date INTEGER NOT NULL
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS check_bill (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            money INTEGER NOT NULL,
            bill_id VARCHAR NOT NULL UNIQUE
            )
            """
        )

    def get_disc(self, promo):
        with self.connection:
            result_1 = self.cursor.execute("SELECT disc FROM promo_uses WHERE promo = ?", (promo,)).fetchone()
            result_2 = self.cursor.execute("SELECT disc FROM promo_date WHERE promo = ?", (promo,)).fetchone()
            if result_1:
                uses = self.cursor.execute("SELECT uses FROM promo_uses WHERE promo = ?", (promo,)).fetchone()
                new_uses = uses[0] - 1
                if new_uses > 0:
                    self.cursor.execute("UPDATE promo_uses SET uses = ? WHERE promo = ?", (new_uses, promo,))
                else:
                    self.cursor.execute("DELETE FROM promo_uses WHERE promo = ?", (promo,))
                return result_1
            else:

                return result_2

    def check_promo(self, promo):
        with self.connection:
            result_1 = self.cursor.execute("SELECT * FROM promo_uses WHERE promo = ?", (promo,)).fetchall()
            result_2 = self.cursor.execute("SELECT * FROM promo_date WHERE promo = ?", (promo,)).fetchall()
            if bool(len(result_2)) or bool(len(result_1)):
                return True
            else:
                return False

    def add_promo_uses(self, promo, uses, disc):
        with self.connection:
            return self.cursor.execute("INSERT INTO promo_uses (promo, uses, disc) VALUES (?, ?, ?)", (promo, uses, disc,))

    def timer_f(self, promo, date):
        while date > 0:
            sleep(3600)
            date -= 1
        with self.connection:
            return self.cursor.execute("DELETE FROM promo_date WHERE promo = ?", (promo,))

    def get_invited(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT invited FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return result

    def update_invited(self, user_id, invited):
        with self.connection:
            return self.cursor.execute("UPDATE users SET invited = ? WHERE user_id = ?", (invited, user_id,))

    def create_adm_ref(self, channel, link):
        with self.connection:
            return self.cursor.execute("INSERT INTO admin_refs (channel_name, link) VALUES (?, ?)", (channel, link,))

    def get_act_adm_ref(self, link):
        with self.connection:
            result = self.cursor.execute("SELECT activated FROM admin_refs WHERE link = ?", (link,)).fetchone()
            return result[0]

    def act_adm_ref(self, link, activated):
        with self.connection:
            return self.cursor.execute("UPDATE admin_refs SET activated = ? WHERE link = ?", (activated, link))

    def get_adm_refs_money(self, link):
        with self.connection:
            result = self.cursor.execute("SELECT money FROM admin_refs WHERE link = ?", (link,)).fetchone()
            return result

    def buy_adm_ref(self, link, summa):
        with self.connection:
            return self.cursor.execute("UPDATE admin_refs SET money = ? WHERE link = ?", (summa, link,))

    def get_channels_refs(self):
        with self.connection:
            result = self.cursor.execute("SELECT channel_name, activated, money FROM admin_refs").fetchall()
            return result

    def get_users_refs(self):
        with self.connection:
            result = self.cursor.execute("SELECT user_id, activated, money FROM user_refs").fetchall()
            return result

    def create_user_ref(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT * FROM user_refs WHERE user_id = ?", (user_id,)).fetchall()
            if bool(len(res)):
                return
            else:
                return self.cursor.execute("INSERT INTO user_refs (user_id) VALUES (?)", (user_id,))

    def get_act_user_ref(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT activated FROM user_refs WHERE user_id = ?", (user_id,)).fetchone()
            return result[0]

    def act_user_ref(self, user_id, activated):
        with self.connection:
            return self.cursor.execute("UPDATE user_refs SET activated = ? WHERE user_id = ?", (activated, user_id,))

    def get_user_refs_money(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT money FROM user_refs WHERE user_id = ?", (user_id,)).fetchone()
            return result

    def buy_user_ref(self, user_id, summa):
        with self.connection:
            return self.cursor.execute("UPDATE user_refs SET money = ? WHERE user_id = ?", (summa, user_id,))

    def add_promo_date(self, promo, date, disc):
        with self.connection:
            timer = threading.Thread(target=self.timer_f, args=(promo, date))
            timer.start()
            return self.cursor.execute("INSERT INTO promo_date (promo, date, disc) VALUES (?, ?, ?)", (promo, date, disc,))

    def check_user(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchall()
        return bool(len(result))

    def update_user_refs(self, user_id, activated):
        with self.connection:
            return self.cursor.execute("UPDATE users SET invited = ? WHERE user_id = ?", (activated, user_id,))

    def update_user_refer(self, user_id, refer):
        with self.connection:
            return self.cursor.execute("UPDATE users SET refer = ? WHERE user_id = ?", (refer, user_id,))

    def get_user_refer(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT refer FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return result[0]

    def add_user(self, user_id, user_name):
        dateFormater = "%Y-%m-%d %H:%M:%S"
        date = datetime.now()
        date = date.strftime(dateFormater)
        with self.connection:
            return self.cursor.execute("INSERT INTO users (user_id, user_name, activation_date) VALUES (?, ?, ?)", (user_id, user_name, date))

    def change_sub_status(self, user_id, status):
        with self.connection:
            return self.cursor.execute("UPDATE users SET sub_status = ? WHERE user_id = ?", (status, user_id))

    def get_users_count(self):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM users").fetchall()
            return len(result)

    def get_subs_count(self):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM subs").fetchall()
            return len(result)

    def get_users(self):
        with self.connection:
            result = self.cursor.execute("SELECT user_id FROM users").fetchall()
            return result

    def get_subs(self):
        with self.connection:
            result = self.cursor.execute("SELECT user_id FROM users WHERE sub_status=TRUE").fetchall()
            return result

    def add_check(self, user_id, money, bill_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO check_bill (user_id, money, bill_id) VALUES (?, ?, ?)", (user_id, money, bill_id,))

    def get_check(self, bill_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM check_bill WHERE bill_id = ?", (bill_id,)).fetchmany(1)
            if not bool(len(result)):
                return False
            else:
                return result[0]

    def delete_check(self, bill_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM check_bill WHERE bill_id = ?", (bill_id,))

    def add_sub(self, user_id, channel_id, link, date):
        with self.connection:
            self.cursor.execute("INSERT INTO subs (user_id, channel_id, link, date) VALUES (?, ?, ?, ?)", (user_id, channel_id, link, date,))

    def info_sub_links(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT link, date FROM subs WHERE user_id = ?", (user_id,)).fetchall()
            return result

    def info_sub_channels(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT channel_id, date FROM subs WHERE user_id = ?", (user_id,)).fetchall()
            return result

    def del_sub(self, user_id, channel_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM subs WHERE user_id = ? AND channel_id = ?", (user_id, channel_id,))

    def get_sub_info(self, user_id):
        with self.connection:
            info = self.cursor.execute("SELECT * FROM subs WHERE user_id = ?", (user_id,)).fetchall()
            return info

    def get_user_info(self, user_id):
        with self.connection:
            info = self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchall()
            return info

    def check_subscription(self, user_id, channel_id):
        with self.connection:
            time = self.cursor.execute("SELECT date FROM subs WHERE user_id = ? AND channel_id = ?", (user_id, channel_id,)).fetchone()
            return time

    def update_time_of_subscription(self, user_id, channel_id, new_date):
        with self.connection:
            return self.cursor.execute("UPDATE subs SET date = ? WHERE user_id = ? AND channel_id = ?", (new_date, user_id, channel_id,))

    def check_all_subs(self):
        all_subs = dict()
        with self.connection:
            users = self.cursor.execute("SELECT user_id FROM subs").fetchall()
            if users:
                for user_id in set(users):
                    result = self.cursor.execute("SELECT channel_id, date FROM subs WHERE user_id = ?", (user_id[0],)).fetchall()
                    all_subs[user_id[0]] = set(result)
                return all_subs
            else:
                return False


    def find_out(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT sub_status FROM users WHERE user_id=?", (user_id,)).fetchone()
            try:
                if not result[0]:
                    return 'user'
                elif result[0]:
                    return 'sub'
            except TypeError:
                return False

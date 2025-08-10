"""
兵者TWOW服务端
更新日期：2025-08-10
作者：KirkLee123
"""
import email
import email.utils
import hashlib
import json
import random
import smtplib
from email.mime.text import MIMEText
import os
import socket
import threading
import time



class Server:
    def __init__(self, host, port):
        self.version = "V1.2.3"  # 版本号
        self.protocol_version = 3  # 协议版本
        self.from_email = "TDR_Group@foxmail.com"  # 发邮件用的邮箱
        self.load_email_key()
        self.ema_yzm = {}
        self.online_users = {}
        self.rooms = {}
        self.load()
        self.new_index = 0
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.log(f"服务端启动完成，版本号：{self.version}，协议版本：{self.protocol_version}，监听地址：{self.host}:{self.port}")
        self.debug_mode = True

    def log(self, text):
        t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        text = f"[{t}] {text}"
        print(text)
        t = time.strftime("%Y-%m-%d", time.localtime())
        if not os.path.exists("logs"):
            os.makedirs("logs")
        with open(f"logs/{t}.txt", "a", encoding='utf-8') as f:
            f.write(text + "\n")

    def run(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            self.log(f"收到来自 {client_address} 的新连接")
            threading.Thread(target=self.client_handler, args=(client_socket, client_address, self.new_index)).start()
            self.new_index += 1

    def load_email_key(self):
        if not os.path.isfile("email.key"):
            with open("email.key", "w", encoding='utf-8') as f:
                f.write("xxxxxxxxxxxxxxxx")
            print("未配置邮箱发邮件的授权码，请打开email.key配置!")
            self.email_authentication = ""
        else:
            with open("email.key", "r", encoding='utf-8') as f:
                self.email_authentication = f.read()

    def load(self):
        if not os.path.isfile("users.json"):
            self.users = {}
        else:
            with open("users.json", "r", encoding='utf-8') as f:
                self.users = json.load(f)
        if not os.path.isfile("user_data.json"):
            self.user_data = {}
        else:
            with open("user_data.json", "r", encoding='utf-8') as f:
                self.user_data = json.load(f)
        self.save()

    def save(self):
        with open("users.json", "w", encoding='utf-8') as f:
            json.dump(self.users, f)
        with open("user_data.json", "w", encoding='utf-8') as f:
            json.dump(self.user_data, f)


    def index_user(self, index):
        for i in self.online_users.keys():
            if self.online_users[i]["index"] == index:
                return i
        return None

    def send_email(self, to, head_subject, main_data):
        message = MIMEText(main_data)
        # message['To'] = email.utils.formataddr((user, user))
        message['From'] = email.utils.formataddr(('兵者TWOW', self.from_email))
        message['Subject'] = head_subject
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(self.from_email, self.email_authentication)
        server.set_debuglevel(False)
        try:
            server.sendmail(self.from_email, to, msg=message.as_string())
        finally:
            server.quit()

    def random_card(self, room, player):
        if len(self.rooms[room]["all_cards"]) == 0:
            self.online_users[self.rooms[room]["belongs_to"]]["socket"].send("game end p ".encode())
            self.online_users[self.rooms[room]["belongs_to"]]["socket"].send("game end p ".encode())
            self.log(f"房间 {room} 平局")
            self.remove_room(room)
            self.remove_room(room)
        x = random.choice(self.rooms[room]["all_cards"])
        self.rooms[room]["all_cards"].remove(x)
        for i in range(len(self.rooms[room][player]["hand_cards"])):
            if self.rooms[room][player]["hand_cards"][i] == "0":
                self.rooms[room][player]["hand_cards"][i] = x
                return True
        self.rooms[room]["all_cards"].append(x)
        return False

    def random_remove_card(self, room, player):
        a = []
        for i in self.rooms[room][player]["hand_cards"]:
            if i != "0":
                a.append(i)
        if len(a) == 0:
            return None
        x = random.choice(a)
        index = self.rooms[room][player]["hand_cards"].index(x)
        self.rooms[room][player]["hand_cards"][index] = "0"
        return x

    def room_start(self, room):
        if self.rooms[room]["now"] != 0:
            return
        self.rooms[room]["now"] = 1
        self.rooms[room]["player1"]["energy"] = 4
        self.rooms[room]["player2"]["energy"] = 4
        for i in ["d", "g", "k", "n"]:
            for j in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                self.rooms[room]["all_cards"].append(i + j)
                self.rooms[room]["all_cards"].append(i + j)
                self.rooms[room]["all_cards"].append(i + j)
                self.rooms[room]["all_cards"].append(i + j)
        for i in ["2", "4"]:
            self.rooms[room]["all_cards"].append("w" + i)
            self.rooms[room]["all_cards"].append("w" + i)
            self.rooms[room]["all_cards"].append("w" + i)
            self.rooms[room]["all_cards"].append("w" + i)
        for _ in range(6):
            self.random_card(room, "player1")
            self.random_card(room, "player2")
        return

    def remove_room(self, room):
        if self.rooms[room]["now"] !=3:
            self.rooms[room]["now"] = 3
            return
        if self.rooms[room]["now"] == 3:
            self.online_users[self.rooms[room]["belongs_to"]]["room"] = None
            self.online_users[self.rooms[room]["guest"]]["room"] = None
            self.rooms.pop(room)
            self.log(f"房间 {room} 对局完成，已关闭")
            return

    def room_log(self, user, text1, text2):
        text1 = "game " + text1
        text2 = "game " + text2
        room = self.online_users[user]["room"]
        if user == self.rooms[room]["belongs_to"]:
            self.online_users[self.rooms[room]["belongs_to"]]["socket"].send(text1.encode())
            self.online_users[self.rooms[room]["guest"]]["socket"].send(text2.encode())
            self.log(f"向 {room} 房间的玩家 {self.rooms[room]['belongs_to']} 发送了消息 {text1}")
            self.log(f"向 {room} 房间的玩家 {self.rooms[room]['guest']} 发送了消息 {text2}")
        if user == self.rooms[room]["guest"]:
            self.online_users[self.rooms[room]["belongs_to"]]["socket"].send(text2.encode())
            self.online_users[self.rooms[room]["guest"]]["socket"].send(text1.encode())
            self.log(f"向 {room} 房间的玩家 {self.rooms[room]['belongs_to']} 发送了消息 {text2}")
            self.log(f"向 {room} 房间的玩家 {self.rooms[room]['guest']} 发送了消息 {text1}")
        time.sleep(0.1)

    def room_refresh(self, user):
        r = "game nowinfo"
        if self.rooms[self.online_users[user]["room"]]["belongs_to"] == user:
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["hand_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["passive_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["hand_cards"]:
                if i != "0":
                    r += " " + "b"
                else:
                    r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["passive_cards"]:
                if i != "0":
                    r += " " + "b"
                else:
                    r += " " + i
            if len(self.rooms[self.online_users[user]["room"]]["all_cards"]) > 0:
                r += " " + "b"
            else:
                r += " " + "0"
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["out_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["out_cards"]:
                r += " " + i
            r += " " + str(self.rooms[self.online_users[user]["room"]]["player1"]["energy"])
            r += " " + str(self.rooms[self.online_users[user]["room"]]["player2"]["energy"])
            r += " " + str(len(self.rooms[self.online_users[user]["room"]]["all_cards"]))
            if self.rooms[self.online_users[user]["room"]]["now"] == 1:
                r += " " + "1"
            else:
                r += " " + "0"
            r += " " + self.rooms[self.online_users[user]["room"]]["last_card"]
            if not self.room_panduan(self.online_users[user]["room"], "player1"):
                self.online_users[user]["socket"].send("game end loss ".encode())
                self.log(f"房间 {self.online_users[user]['room']} 玩家 {user} 输了")
                self.remove_room(self.online_users[user]["room"])
                time.sleep(0.1)
            elif not self.room_panduan(self.online_users[user]["room"], "player2"):
                self.online_users[user]["socket"].send("game end win ".encode())
                self.log(f"房间 {self.online_users[user]['room']} 玩家 {user} 赢了")
                self.remove_room(self.online_users[user]["room"])
                time.sleep(0.1)
        else:
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["hand_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["passive_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["hand_cards"]:
                if i != "0":
                    r += " " + "b"
                else:
                    r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["passive_cards"]:
                if i != "0":
                    r += " " + "b"
                else:
                    r += " " + i
            if len(self.rooms[self.online_users[user]["room"]]["all_cards"]) > 0:
                r += " " + "b"
            else:
                r += " " + "0"
            for i in self.rooms[self.online_users[user]["room"]]["player2"]["out_cards"]:
                r += " " + i
            for i in self.rooms[self.online_users[user]["room"]]["player1"]["out_cards"]:
                r += " " + i
            r += " " + str(self.rooms[self.online_users[user]["room"]]["player2"]["energy"])
            r += " " + str(self.rooms[self.online_users[user]["room"]]["player1"]["energy"])
            r += " " + str(len(self.rooms[self.online_users[user]["room"]]["all_cards"]))
            if self.rooms[self.online_users[user]["room"]]["now"] == 2:
                r += " " + "1"
            else:
                r += " " + "0"
            r += " " + self.rooms[self.online_users[user]["room"]]["last_card"]
            if not self.room_panduan(self.online_users[user]["room"], "player2"):
                self.online_users[user]["socket"].send("game end loss ".encode())
                self.log(f"房间 {self.online_users[user]['room']} 玩家 {user} 输了")
                self.remove_room(self.online_users[user]["room"])
                time.sleep(0.1)
            elif not self.room_panduan(self.online_users[user]["room"], "player1"):
                self.online_users[user]["socket"].send("game end win ".encode())
                self.log(f"房间 {self.online_users[user]['room']} 玩家 {user} 赢了")
                self.remove_room(self.online_users[user]["room"])
                time.sleep(0.1)
        r += " "
        self.online_users[user]["socket"].send(r.encode())

    def room_pass(self, user, player, card_index, client_socket):
        if self.rooms[self.online_users[user]["room"]][player]["hand_cards"][card_index] == "0":
            client_socket.send("tip 参数错误(该手牌不存在) ".encode())
            return
        if self.rooms[self.online_users[user]["room"]][player]["hand_cards"][card_index] not in ["d0", "g0", "k0", "n0",
                                                                                                 "w2", "w4"]:
            client_socket.send("tip 参数错误(该手牌不能作为被动卡牌) ".encode())
            return
        for i in range(len(self.rooms[self.online_users[user]["room"]][player]["passive_cards"])):
            if self.rooms[self.online_users[user]["room"]][player]["passive_cards"][i] == "0":
                self.rooms[self.online_users[user]["room"]][player]["passive_cards"][i] = \
                self.rooms[self.online_users[user]["room"]][player]["hand_cards"][card_index]
                self.rooms[self.online_users[user]["room"]][player]["hand_cards"][card_index] = "0"
                self.room_log(user, "log 你放置了一张被动卡牌 ", "log 对方放置了一张被动卡牌 ")
                self.room_refresh(self.rooms[self.online_users[user]["room"]]["belongs_to"])
                self.room_refresh(self.rooms[self.online_users[user]["room"]]["guest"])
                return
        client_socket.send("tip 参数错误(被动卡槽已满) ".encode())
        return

    def room_next(self, room):
        if self.rooms[room]["now"] == 1:
            self.rooms[room]["now"] = 2
            if self.rooms[room]["player2"]["energy"] < 6:
                self.rooms[room]["player2"]["energy"] += 2
                if self.rooms[room]["player2"]["energy"] > 6:
                    self.rooms[room]["player2"]["energy"] = 6
            if not self.rooms[room]["player1"]["used"]:
                self.random_card(room, "player1")
            self.rooms[room]["player1"]["used"] = False
            self.room_refresh(self.rooms[room]["belongs_to"])
            self.room_refresh(self.rooms[room]["guest"])
            return
        if self.rooms[room]["now"] == 2:
            self.rooms[room]["now"] = 1
            if self.rooms[room]["player1"]["energy"] < 6:
                self.rooms[room]["player1"]["energy"] += 2
                if self.rooms[room]["player1"]["energy"] > 6:
                    self.rooms[room]["player1"]["energy"] = 6
            if not self.rooms[room]["player2"]["used"]:
                self.random_card(room, "player2")
            self.rooms[room]["player2"]["used"] = False
            self.room_refresh(self.rooms[room]["belongs_to"])
            self.room_refresh(self.rooms[room]["guest"])
            return
        return

    def room_panduan(self, room, player):
        cnt = 0
        for i in self.rooms[room][player]["hand_cards"]:
            if i != "0":
                cnt += 1
        if cnt == 0:
            if "w2" in self.rooms[room][player]["passive_cards"]:
                self.rooms[room][player]["passive_cards"][self.rooms[room][player]["passive_cards"].index("w2")] = "0"
                self.random_card(room, player)
                self.random_card(room, player)
                text1 = "log 你的被动卡牌被触发了，你摸了两张卡牌继续战斗!"
                text2 = "log 对方被动卡牌被触发了，对方摸了两张卡牌继续战斗!"
                self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1 + " ",
                              text2 + " ")
                return True
            if "w4" in self.rooms[room][player]["passive_cards"]:
                self.rooms[room][player]["passive_cards"][self.rooms[room][player]["passive_cards"].index("w4")] = "0"
                self.random_card(room, player)
                self.random_card(room, player)
                self.random_card(room, player)
                self.random_card(room, player)
                text1 = "log 你的被动卡牌被触发了，你摸了4张卡牌继续战斗!"
                text2 = "log 对方被动卡牌被触发了，对方摸了4张卡牌继续战斗!"
                self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1 + " ",
                              text2 + " ")
                return True
            return False
        return True
    def room_energy(self, room, player, num, text1="log 你打出了一张能量卡牌", text2="log 对方打出了一张能量卡牌"):
        if "n0" in self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"]:
            self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"][self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"].index("n0")] = "0"
            text1 += "，但触发了对方的被动卡牌"
            text2 += "，触发了你的被动卡牌"
            self.room_energy(room, "player1" if player == "player2" else "player2", num, text2, text1)
            return
        self.rooms[room][player]["energy"] += num
        self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1+" ", text2+" ")

    def room_reduce_energy(self, room, player, num, text1="log 对方打出了一张扣能卡牌", text2="log 你打出了一张扣能卡牌"):
        if "k0" in self.rooms[room][player]["passive_cards"]:
            self.rooms[room][player]["passive_cards"][self.rooms[room][player]["passive_cards"].index("k0")] = "0"
            text1 += "，触发了你的被动卡牌"
            text2 += "，但触发了对方的被动卡牌"
            self.room_reduce_energy(room, "player1" if player == "player2" else "player2", num, text2, text1)
            return
        self.rooms[room][player]["energy"] -= num
        self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1+" ", text2+" ")
    def room_defend(self, room, player, card, text1="log 你放置了一张盾牌卡牌", text2="log 对方放置了一张盾牌卡牌"):
        if "d0" in self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"]:
            self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"][
                self.rooms[room]["player1" if player == "player2" else "player2"]["passive_cards"].index("d0")] = "0"
            text1 += "，但触发了对方的被动卡牌"
            text2 += "，触发了你的被动卡牌"
            if not self.room_defend(room, "player1" if player == "player2" else "player2", card, text2, text1):
                return self.room_defend(room, player, card, text1, text2)
            return True
        flag = False
        for i in range(len(self.rooms[room][player]["out_cards"])):
            if self.rooms[room][player]["out_cards"][i] == "0":
                self.rooms[room][player]["out_cards"][i] = card
                flag = True
                self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1+" ", text2+" ")
                break
        return flag

    def room_damage(self, room, player, num, text1="log 对方打出了一张伤害卡牌", text2="log 你打出了一张伤害卡牌"):
        if "g0" in self.rooms[room][player]["passive_cards"]:
            self.rooms[room][player]["passive_cards"][self.rooms[room][player]["passive_cards"].index("g0")] = "0"
            text1 += "，触发了你的被动卡牌"
            text2 += "，但触发了对方的被动卡牌"
            self.room_damage(room, "player1" if player == "player2" else "player2", num, text2, text1)
            return
        flag = True
        for i in range(len(self.rooms[room][player]["out_cards"])):
            while self.rooms[room][player]["out_cards"][i] != "0":
                if not flag:
                    break
                if self.rooms[room][player]["out_cards"][i][1] == "1":
                    self.rooms[room][player]["out_cards"][i] = "0"
                    text1 += "，被你的1点无敌盾牌卡牌抵消了所有伤害"
                    text2 += "，被对方的1点无敌盾牌卡牌抵消了所有伤害"
                    flag = False
                    break
                else:
                    if num > int(self.rooms[room][player]["out_cards"][i][1]):
                        num -= int(self.rooms[room][player]["out_cards"][i][1])
                        self.rooms[room][player]["out_cards"][i] = "0"
                        text1 += "，被你的盾牌卡牌抵消了部分伤害"
                        text2 += "，被对方的盾牌卡牌抵消了部分伤害"
                        break
                    if num == int(self.rooms[room][player]["out_cards"][i][1]):
                        self.rooms[room][player]["out_cards"][i] = "0"
                        text1 += "，被你的盾牌卡牌刚好抵消了伤害"
                        text2 += "，被对方的盾牌卡牌刚好抵消了伤害"
                        flag = False
                        break
                    if num < int(self.rooms[room][player]["out_cards"][i][1]):
                        self.rooms[room][player]["out_cards"][i] = "d" + str(
                            int(self.rooms[room][player]["out_cards"][i][1]) - num)
                        text1 += "，被你的盾牌卡牌完全抵消了伤害"
                        text2 += "，被对方的盾牌卡牌完全抵消了伤害"
                        flag = False
                        break
        if flag:
            for _ in range(num):
                self.random_remove_card(room, player)
            text1 += "，对你造成"+str(num)+"点伤害"
            text2 += "，对对方造成"+str(num)+"点伤害"
        self.room_log(self.rooms[room]["belongs_to" if player == "player1" else "guest"], text1+" ", text2+" ")

    def room_use(self, room, zi, dui, index, client_socket):
        if index < 0 or index >= len(self.rooms[room][zi]["hand_cards"]):
            client_socket.send("tip 参数错误(未知手牌) ".encode())
            return
        c = self.rooms[room][zi]["hand_cards"][index]
        if c == "0":
            client_socket.send("tip 参数错误(该手牌不存在) ".encode())
            return
        if c == "w2":
            self.rooms[room][zi]["hand_cards"][index] = "0"
            self.rooms[room]["last_card"] = c
            self.rooms[room][zi]["used"] = True
            self.random_card(room, zi)
            self.random_card(room, zi)
            self.room_refresh(self.rooms[room]["belongs_to"])
            self.room_refresh(self.rooms[room]["guest"])
            return
        if c == "w4":
            self.rooms[room][zi]["hand_cards"][index] = "0"
            self.rooms[room]["last_card"] = c
            self.rooms[room][zi]["used"] = True
            self.random_card(room, zi)
            self.random_card(room, zi)
            self.random_card(room, zi)
            self.random_card(room, zi)
            self.room_refresh(self.rooms[room]["belongs_to"])
            self.room_refresh(self.rooms[room]["guest"])
            return
        if c[0] == "n":
            self.room_energy(room, zi, int(c[1]))
        if c[0] == "k":
            self.room_reduce_energy(room, dui, int(c[1]))
        if c[0] == "d":
            if self.rooms[room][zi]["energy"] < int(c[1]):
                client_socket.send("tip 参数错误(能量不足) ".encode())
                return
            self.rooms[room][zi]["energy"] -= int(c[1])
            if not self.room_defend(room, zi, c):
                client_socket.send("tip 参数错误(盾牌槽已满) ".encode())
                self.rooms[room][zi]["energy"] += int(c[1])
                return
        if c[0] == "g":
            if self.rooms[room][zi]["energy"] < int(c[1]):
                client_socket.send("tip 参数错误(能量不足) ".encode())
                return
            self.rooms[room][zi]["energy"] -= int(c[1])
            self.room_damage(room, dui, int(c[1]))
            self.rooms[room][zi]["hand_cards"][index] = "0"
            self.rooms[room]["last_card"] = c
            self.rooms[room][zi]["used"] = True
            self.room_next(room)
            return
        self.rooms[room][zi]["hand_cards"][index] = "0"
        self.rooms[room]["last_card"] = c
        self.rooms[room][zi]["used"] = True

        self.room_refresh(self.rooms[room]["belongs_to"])
        self.room_refresh(self.rooms[room]["guest"])
        return




    def client_handler(self, client_socket, client_address, index):
        while True:
            data_raw = client_socket.recv(1024)
            if not data_raw:
                break
            data = data_raw.decode().split()

            if  data[0] == "f**k":
                client_socket.send(f"f**k {data[1]} ".encode())
                continue
            if self.debug_mode: self.log(f"收到来自 {client_address} 的消息：{data_raw.decode()}")
            if data[0] == "login":
                if len(data) != 4:
                    client_socket.send("tip 参数错误(参数数量不是4个) ".encode())
                    continue
                if int(data[1]) != self.protocol_version:
                    client_socket.send(f"loginfail {self.protocol_version} ".encode())
                    continue
                if data[2] in self.users:
                    if hashlib.sha256(data[3].encode()).hexdigest() == self.users[data[2]]["password_hash"]:
                        if data[2] not in self.online_users:
                            client_socket.send("登陆成功!".encode())
                            self.online_users[data[2]] = {"index": index, "socket": client_socket, "room": None}
                            self.log(f"{data[2]} 登陆成功")
                        else:
                            try:
                                self.online_users[data[2]]["socket"].send("重复登陆!".encode())
                            except Exception as e:
                                self.log(f"{data[2]} 原地登陆已下线中发送错误，错误信息：{e}")
                            client_socket.send("登陆成功!".encode())
                            self.online_users[data[2]] = {"index": index, "socket": client_socket, "room": None}
                            self.log(f"{data[2]} 异地登陆成功，原地登陆已下线")
                    else:
                        client_socket.send("账号密码错误!".encode())
                else:
                    client_socket.send("账号密码错误!".encode())
                continue


            if data[0] == "sign":
                if len(data) == 3:
                    if data[1] == "username":
                        if data[2] in self.users:
                            client_socket.send("用户名不可用".encode())
                        else:
                            client_socket.send("*用户名可用*".encode())
                        continue
                    if data[1] == "ema":
                        yzm = str(random.randint(100000, 999999))
                        self.ema_yzm[data[2]] = yzm
                        self.send_email(data[2], "兵者账号注册-邮箱验证", "感谢您注册兵者账号!您本次注册的验证码为 " + yzm + " ,请尽快完成注册!")
                        client_socket.send("sand yzm sucess".encode())
                        self.log(f"发送验证码 {yzm} 到 {data[2]}")
                        continue
                elif len(data) == 6:
                    if data[1] == "up":
                        flag = False
                        for i in self.users.keys():
                            if self.users[i]["email"] == data[4]:
                                flag = True
                                client_socket.send("此邮箱已被绑定!".encode())
                                break
                        if flag:
                            continue
                        if data[4] in self.ema_yzm and self.ema_yzm[data[4]] == data[5]:
                            self.ema_yzm.pop(data[4])
                            self.users[data[2]] = {"password_hash": hashlib.sha256(data[3].encode()).hexdigest(), "email": data[4]}
                            self.user_data[data[2]] = {"money": 0}
                            self.save()
                            self.log(f"{data[2]} 使用邮箱 {data[4]} 注册成功")
                            client_socket.send("注册成功!".encode())
                        else:
                            client_socket.send("验证码错误!".encode())
                        continue
                else:
                    client_socket.send("tip 参数错误(参数数量不对) ".encode())


            if data[0] == "selfinfo":
                zh = self.index_user(index)
                if not zh:
                    client_socket.send("tip 参数错误(未登录) ".encode())
                    continue
                client_socket.send(f"selfinfo {zh} {self.user_data[zh]['money']} {len(self.online_users)} ".encode())
                continue


            if data[0] == "room":
                user = self.index_user(index)
                if not user:
                    client_socket.send("tip 参数错误(未登录) ".encode())
                    continue
                if len(data) == 3:
                    if data[1] == "create":
                        if self.online_users[user]["room"]:
                            client_socket.send("tip 参数错误(已经在房间里) ".encode())
                            continue
                        if self.user_data[user]["money"] < 100:
                            client_socket.send("tip 参数错误(金币不足) ".encode())
                            continue
                        if data[2] in self.rooms:
                            client_socket.send("tip 参数错误(房间名已存在) ".encode())
                            continue
                        self.user_data[user]["money"] -= 100
                        self.save()
                        self.rooms[data[2]] = {
                                            "belongs_to": user,
                                            "guest": None,
                                            "now": 0,
                                            "player1": {
                                                "used": False,
                                                "energy": 0,
                                                "hand_cards": ["0", "0", "0", "0", "0", "0", "0", "0"],
                                                "passive_cards": ["0", "0"],
                                                "out_cards": ["0", "0", "0"]
                                            },
                                            "player2": {
                                                "used": False,
                                                "energy": 0,
                                                "hand_cards": ["0", "0", "0", "0", "0", "0", "0", "0"],
                                                "passive_cards": ["0", "0"],
                                                "out_cards": ["0", "0", "0"]
                                            },
                                            "last_card": "0",
                                            "all_cards": []
                                        }
                        self.online_users[user]["room"] = data[2]
                        self.log(f"{user} 创建了房间 {data[2]} ")
                        client_socket.send(f"CreateRoomSucess {data[2]} ".encode())
                        continue
                    if data[1] == "join":
                        if self.online_users[user]["room"]:
                            client_socket.send("tip 参数错误(已经在房间里) ".encode())
                            continue
                        if data[2] not in self.rooms:
                            client_socket.send("tip 参数错误(房间不存在) ".encode())
                            continue
                        if self.rooms[data[2]]["guest"]:
                            client_socket.send("tip 参数错误(房间已满) ".encode())
                            continue
                        self.rooms[data[2]]["guest"] = user
                        self.online_users[user]["room"] = data[2]
                        self.log(f"{user} 加入了房间 {data[2]} ")
                        client_socket.send(f"JoinRoomSucess {data[2]} ".encode())
                        time.sleep(0.1)
                        client_socket.send(f"game start {self.rooms[data[2]]['belongs_to'] }".encode())
                        self.online_users[self.rooms[data[2]]["belongs_to"]]["socket"].send(f"game start {user} ".encode())
                        continue

                elif len(data) == 2:
                    if data[1] == "r":
                        r = f"nowrooms {len(self.rooms)} "
                        for i in self.rooms.keys():
                            if self.rooms[i]["guest"] is None:
                                r += i + "┄(1/2)###"
                            else:
                                r += i + "┄(2/2)###"
                        client_socket.send(r.encode())
                        continue
                    if data[1] == "exit":
                        if self.online_users[user]["room"] not in self.rooms:
                            client_socket.send("tip 参数错误(房间不存在) ".encode())
                            continue
                        room = self.online_users[user]["room"]
                        self.online_users[user]["room"] = None
                        if self.rooms[room]["belongs_to"] == user:
                            if self.rooms[room]["guest"]:
                                self.online_users[self.rooms[room]["guest"]]["socket"].send(f"game exit ".encode())
                                self.online_users[self.rooms[room]["guest"]]["room"] = None
                                self.log(f"{user} 退出了房间，将 {self.rooms[room]['guest']} 移出房间，房间已关闭")
                            else:
                                self.log(f"{user} 退出了房间，房间已关闭")
                            self.rooms.pop(room)
                            continue
                        if self.rooms[room]["guest"] == user:
                            self.online_users[self.rooms[room]["belongs_to"]]["socket"].send(f"game exit ".encode())
                            self.online_users[self.rooms[room]["belongs_to"]]["room"] = None
                            self.log(f"{user} 退出了房间，将 {self.rooms[room]['guest']} 移出房间，房间已关闭")
                            self.rooms.pop(room)
                            continue
                else:
                    client_socket.send("tip 参数错误(参数数量不是2个或3个) ".encode())
                    continue


            if data[0] == "game":
                user = self.index_user(index)
                if not user:
                    client_socket.send("tip 参数错误(未登录) ".encode())
                    continue
                if not self.online_users[user]["room"]:
                    client_socket.send("tip 参数错误(未在房间中) ".encode())
                    continue
                if self.online_users[user]["room"] not in self.rooms:
                    client_socket.send("tip 参数错误(房间不存在) ".encode())
                    continue
                if data[1] == "start":
                    self.room_start(self.online_users[user]["room"])
                if data[1] == "nowinfo":
                    self.room_refresh(user)
                    continue
                if data[1] == "pass":
                    if self.rooms[self.online_users[user]["room"]]["belongs_to"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 1:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_pass(user, "player1", int(data[2]), client_socket)
                        continue
                    if self.rooms[self.online_users[user]["room"]]["guest"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 2:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_pass(user, "player2", int(data[2]), client_socket)
                        continue
                if data[1] == "next":
                    if self.rooms[self.online_users[user]["room"]]["belongs_to"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 1:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_next(self.online_users[user]["room"])
                        continue
                    if self.rooms[self.online_users[user]["room"]]["guest"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 2:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_next(self.online_users[user]["room"])
                        continue
                if data[1] == "use":
                    if self.rooms[self.online_users[user]["room"]]["belongs_to"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 1:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_use(self.online_users[user]["room"], "player1", "player2", int(data[2]), client_socket)
                        continue
                    if self.rooms[self.online_users[user]["room"]]["guest"] == user:
                        if self.rooms[self.online_users[user]["room"]]["now"] != 2:
                            client_socket.send("tip 参数错误(不是该玩家的回合) ".encode())
                            continue
                        self.room_use(self.online_users[user]["room"], "player2", "player1", int(data[2]), client_socket)
                        continue
                if data[1] == "chat":
                    if len(data) < 3:
                        continue
                    if self.online_users[user]["room"] not in self.rooms:
                        client_socket.send("tip 参数错误(房间不存在) ".encode())
                        continue
                    room = self.online_users[user]["room"]
                    if self.rooms[room]["guest"]:
                        client_socket.send(f"game log {user}:{data[2]} ".encode())
                        self.online_users[
                            self.rooms[room]["guest" if self.rooms[room]["belongs_to"] == user else "belongs_to"]][
                            "socket"].send(f"game log {user}:{data[2]} ".encode())
                    else:
                        client_socket.send(f"game log {user}:{data[2]} ".encode())
                    self.log(f"{user} 在房间 {room} 中说 {data[2]}")
                    continue



            if data[0] == "test":
                if data[1] == "moneyadd1":
                    user = self.index_user(index)
                    if not user:
                        client_socket.send("tip 参数错误(未登录) ".encode())
                        continue
                    self.user_data[user]["money"] += 10
                    self.save()
                    self.log(f"{user} 测试增加10金币")
                    client_socket.send(f"selfinfo {user} {self.user_data[user]['money']} {len(self.online_users) }".encode())
                    continue

        user = self.index_user(index)
        if user:
            room = self.online_users[user]["room"]
            self.online_users.pop(user)
            if room:
                if self.rooms[room]["belongs_to"] == user:
                    if self.rooms[room]["guest"]:
                        self.online_users[self.rooms[room]["guest"]]["socket"].send(f"game exit ".encode())
                        self.online_users[self.rooms[room]["guest"]]["room"] = None
                        self.log(f"{user} 退出了房间，将 {self.rooms[room]['guest']} 移出房间，房间已关闭")
                    else:
                        self.log(f"{user} 所在的房间已关闭")
                    self.rooms.pop(room)
                elif self.rooms[room]["guest"] == user:
                    self.online_users[self.rooms[room]["belongs_to"]]["socket"].send(f"game exit ".encode())
                    self.online_users[self.rooms[room]["belongs_to"]]["room"] = None
                    self.log(f"{user} 退出了房间，将 {self.rooms[room]['guest']} 移出房间，房间已关闭")
                    self.rooms.pop(room)
            self.log(f"{user} 断开连接")

if __name__ == "__main__":
    server = Server("0.0.0.0", 17115)
    server.run()
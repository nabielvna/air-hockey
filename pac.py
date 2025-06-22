import pygame
import sys
import io

import socket
import logging
import json
import base64



# Initialize Pygame
pygame.init()

WIDTH, HEIGHT = 640, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Progjar Mr Pac  Game")

clock = pygame.time.Clock()
FPS = 60
image_size=(64,64)

class ClientInterface:
    def __init__(self,idplayer='1'):
        self.idplayer=idplayer
        self.server_address=('10.21.84.254',55555)

    def get_other_players(self):
        command_str=f"get_all_players"
        hasil = self.send_command(command_str)
        if (hasil['status']=='OK'):
            h = hasil['players']
            return h
        else:
            return False

    def get_players_face(self):
        idplayer = self.idplayer
        command_str=f"get_players_face {idplayer}"
        hasil = self.send_command(command_str)
        if (hasil['status']=='OK'):
            h = hasil['face']
            return h
        else:
            return False

    def send_command(self,command_str=""):
        global server_address
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.server_address)
        logging.warning(f"connecting to {self.server_address}")
        try:
            logging.warning(f"sending message ")
            sock.sendall(command_str.encode())
            # Look for the response, waiting until socket is done (no more data)
            data_received="" #empty string
            while True:
                #socket does not receive all data at once, data comes in part, need to be concatenated at the end of process
                data = sock.recv(16)
                if data:
                    #data is not empty, concat with previous content
                    data_received += data.decode()
                    if "\r\n\r\n" in data_received:
                        break
                else:
                    # no more data, stop the process by break
                    break
            # at this point, data_received (string) will contain all data coming from the socket
            # to be able to use the data_received as a dict, need to load it using json.loads()
            hasil = json.loads(data_received)
            logging.warning("data received from server:")
            return hasil
        except:
            logging.warning("error during data receiving")
            return False

    def set_location(self,x=100,y=100):
        player = self.idplayer
        command_str=f"set_location {player} {x} {y}"
        hasil = self.send_command(command_str)
        if (hasil['status']=='OK'):
            return True
        else:
            return False

    def get_location(self):
        player = self.idplayer
        command_str=f"get_location {player}"
        hasil = self.send_command(command_str)
        if (hasil['status']=='OK'):
            lokasi = hasil['location'].split(',')
            return (int(lokasi[0]),int(lokasi[1]))
        else:
            return False


class Pac:
    def __init__(self,id='1',isremote=False):
        self.id = id
        self.isremote=isremote
        self.direction = "up"
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.speed = 5
        self.client_interface = ClientInterface(self.id)
        self.face = self.client_interface.get_players_face()
        self.image = pygame.image.load(io.BytesIO(base64.b64decode(self.face)))

    def move(self, keys):
        if (self.isremote==False):
            if keys[pygame.K_UP]:
                self.y -= self.speed
                self.direction = "up"
            elif keys[pygame.K_DOWN]:
                self.y += self.speed
                self.direction = "down"
            elif keys[pygame.K_LEFT]:
                self.x -= self.speed
                self.direction = "left"
            elif keys[pygame.K_RIGHT]:
                self.x += self.speed
                self.direction = "right"
            self.client_interface.set_location(self.x, self.y)
        else:
            self.x, self.y = self.client_interface.get_location()

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))

p_number = input("input your number, playa >>> ")
current_player = Pac(p_number)

players = dict()
client = ClientInterface()
other_players = client.get_other_players()
for i in other_players:
    if (i==p_number):
        continue
    players[i]=Pac(i,isremote=True)

while True:
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    current_player.move(keys)
    current_player.draw(screen)

    for i in players:
        players[i].move(keys)
        players[i].draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

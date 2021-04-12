from io import BytesIO
import requests

import pygame

import sys

pygame.init()

FPS = 30
WIDTH, HEIGHT = 650, 450
STEP = 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
coordinates = [48.031431, 46.349672]

params = {"ll": ",".join(map(str, coordinates)), "z": 9, "size": f"{WIDTH},{HEIGHT}", "l": "map"}
photo = None

api_server = "http://static-maps.yandex.ru/1.x/"


def terminate():
    pygame.quit()
    sys.exit()


def update_photo():
    global photo
    response = requests.get(api_server, params=params)
    if not response:
        print("Ошибка выполнения запроса:")
        print(response.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        terminate()
    photo = pygame.image.load(BytesIO(response.content))


def main():
    running = True
    update_photo()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.blit(photo, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


try:
    main()
except FileNotFoundError as e:
    print(e)
    terminate()

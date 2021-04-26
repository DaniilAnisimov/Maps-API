import math
from io import BytesIO
import requests

import pygame

import sys
import os

pygame.init()

FPS = 60
WIDTH, HEIGHT = 600, 520
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
coordinates = [48.031431, 46.349672]

params = {"ll": ",".join(map(str, coordinates)), "z": 9, "size": "400,400", "l": "map"}
photo = None

api_server = "http://static-maps.yandex.ru/1.x/"
geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
search_api_server = "https://search-maps.yandex.ru/v1/"

geocoder_api_key = ""
search_api_key = ""

game_folder = os.path.dirname(__file__)
font_folder = os.path.join(game_folder, "data/fonts")

standard_text = "Нажмите TAB для ввода запроса"
address = ""
postal_code = ""
org_name = ""
org_address = ""
need_postal_code = False
need_input = False
input_text = standard_text


def terminate():
    pygame.quit()
    sys.exit()


class Button:
    def __init__(self, w, h, x, y, message, action=None, f_type="NaturalMonoRegular.ttf", **kwargs):
        self.width, self.height = w, h
        self.x, self.y = x, y
        self.message = message
        self.action, self.parameters = action, kwargs
        self.f_type = f_type
        self.show = True

    # action - функция которую нужно выполнить при нажатии на кнопку
    def draw(self):
        if not self.show:
            return
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        draw_text(self.x, self.y, self.message, size=self.height, f_type=self.f_type)
        if self.x < mouse[0] < self.x + self.width and self.y < mouse[1] < self.y + self.height \
                and click[0] == 1 and self.action:
            self.action(**self.parameters) if self.parameters else self.action()


def draw_text(x, y, text, color=(0, 0, 0), f_type="NaturalMonoRegular.ttf", size=30):
    font = pygame.font.Font(font_folder + "/" + f_type, size)
    text = font.render(text, True, color)
    screen.blit(text, (x, y))


def update_photo():
    global photo
    response = requests.get(api_server, params=params)
    if not response:
        print("Ошибка выполнения запроса:")
        print(response.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        terminate()
    photo = pygame.image.load(BytesIO(response.content))


def change_coordinates(x, y):
    global coordinates
    coordinates = [x, y]
    params["ll"] = ",".join(map(str, coordinates))
    update_photo()


def change_layers(layer="map"):
    params["l"] = layer
    update_photo()


def change_need_postal_code(tof=True):
    global need_postal_code
    need_postal_code = tof


def reset_request():
    global need_input, address, postal_code, org_name, org_address
    need_input = False
    params.pop("pt", None)
    address = ""
    postal_code = ""
    org_name = ""
    org_address = ""
    update_photo()


def lonlat_distance(a, b):
    degree_to_meters_factor = 111 * 1000  # 111 километров в метрах
    a_lon, a_lat = a
    b_lon, b_lat = b

    # Берем среднюю по широте точку и считаем коэффициент для нее.
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    # Вычисляем смещения в метрах по вертикали и горизонтали.
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    # Вычисляем расстояние между точками.
    distance = math.sqrt(dx * dx + dy * dy)

    return distance


def main():
    global need_input, input_text, address, postal_code, coordinates, org_name, org_address
    running = True

    update_photo()

    button_scheme = Button(90, 20, 410, 25, "схема", action=change_layers, layer="map")
    button_satellite = Button(90, 20, 410, 50, "спутник", action=change_layers, layer="sat")
    button_hybrid = Button(90, 20, 410, 75, "гибрид", action=change_layers, layer="sat,skl")
    reset = Button(90, 20, 410, 2, "Сброс", action=reset_request)
    turn_on = Button(50, 16, 410, 375, "вкл", action=change_need_postal_code, tof=True)
    turn_off = Button(50, 16, 410, 390, "выкл", action=change_need_postal_code, tof=False)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if x > 400 or not (30 <= y <= 430):
                    continue
                y -= 30

                nx, ny = coordinates
                k = 2 ** (params["z"] + 8)
                k = 400 / k
                nx -= 200 * k
                ny += 100 * k
                ny -= y * k / 2
                nx += x * k

                reset_request()
                params["pt"] = f"{','.join([str(nx), str(ny)])},flag"

                if event.button == 1:
                    geocoder_params = {
                        "apikey": geocoder_api_key,
                        "geocode": ','.join([str(nx), str(ny)]),
                        "format": "json"}
                    response = requests.get(geocoder_api_server, params=geocoder_params)
                    json_response = response.json()

                    toponym = json_response["response"]["GeoObjectCollection"][
                        "featureMember"][0]["GeoObject"]

                    toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"][
                        "Address"]
                    address = toponym_address["formatted"]

                    if "postal_code" in toponym_address:
                        postal_code = "Почтовый индекс: " + toponym_address["postal_code"]
                    else:
                        postal_code = "Почтовый индекс для данного адреса не обнаружен"
                elif event.button == 3:
                    search_params = {
                        "apikey": search_api_key,
                        "text": "аптека",
                        "lang": "ru_RU",
                        "ll": ','.join([str(nx), str(ny)]),
                        "type": "biz"
                    }
                    response = requests.get(search_api_server, params=search_params)
                    json_response = response.json()

                    # Получаем первую найденную организацию.
                    for organization in json_response["features"]:
                        print(lonlat_distance(([nx, ny]),
                                           tuple(map(float, organization["geometry"]["coordinates"]))))
                        if lonlat_distance(([nx, ny]),
                                           tuple(map(float, organization["geometry"]["coordinates"]))) <= 50:
                            # Название организации.
                            org_name = organization["properties"]["CompanyMetaData"]["name"]
                            # Адрес организации.
                            org_address = organization["properties"]["CompanyMetaData"]["address"]
                            break

                    if not org_name:
                        org_name = "В данном радиусе не было найдено организаций"

                update_photo()
            if need_input and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        geocoder_params = {
                            "apikey": "",
                            "geocode": input_text,
                            "format": "json"}
                        response = requests.get(geocoder_api_server, params=geocoder_params)
                        json_response = response.json()
                        toponym = json_response["response"]["GeoObjectCollection"][
                            "featureMember"][0]["GeoObject"]
                        toponym_coodrinates = toponym["Point"]["pos"]
                        toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")

                        toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"][
                            "Address"]
                        address = toponym_address["formatted"]

                        if "postal_code" in toponym_address:
                            postal_code = "Почтовый индекс: " + toponym_address["postal_code"]
                        else:
                            postal_code = "Почтовый индекс для данного адреса не обнаружен"

                        params["pt"] = f"{','.join([toponym_longitude, toponym_lattitude])},flag"
                        change_coordinates(float(toponym_longitude), float(toponym_lattitude))

                    except Exception as e:
                        print("Ошибка:", e)
                    finally:
                        need_input = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if len(input_text) < 30:
                        input_text += event.unicode
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_PAGEUP:
                    params["z"] = max(2, params["z"] - 1)
                    update_photo()
                elif event.key == pygame.K_PAGEDOWN:
                    params["z"] = min(21, params["z"] + 1)
                    update_photo()
                elif event.key == pygame.K_TAB:
                    need_input = True
                    input_text = ""
                elif event.key == pygame.K_RIGHT:
                    change_coordinates(min(coordinates[0] + 0.00015 * 2 ** (21 - params["z"]), 180), coordinates[1])
                elif event.key == pygame.K_LEFT:
                    change_coordinates(max(coordinates[0] - 0.00015 * 2 ** (21 - params["z"]), -180), coordinates[1])
                elif event.key == pygame.K_UP:
                    change_coordinates(coordinates[0], min(coordinates[1] + 0.00015 * 2 ** (21 - params["z"]), 90))
                elif event.key == pygame.K_DOWN:
                    change_coordinates(coordinates[0], max(coordinates[1] - 0.00015 * 2 ** (21 - params["z"]), -90))
        screen.fill((230, 230, 230))
        screen.blit(photo, (0, 30))

        button_satellite.draw()
        button_scheme.draw()
        button_hybrid.draw()
        turn_on.draw()
        turn_off.draw()
        reset.draw()

        draw_text(2, 2, input_text if need_input else standard_text, size=20)
        draw_text(2, 435, address, size=15)
        if need_postal_code:
            draw_text(2, 455, postal_code, size=15)
        draw_text(405, 360, "Почтовый индекс: вкл" if need_postal_code else "Почтовый индекс: выкл", size=15)
        draw_text(2, 470, org_name, size=15)
        draw_text(2, 490, org_address, size=15)

        pygame.display.flip()
        clock.tick(FPS)


try:
    main()
except FileNotFoundError as e:
    print(e)
    terminate()

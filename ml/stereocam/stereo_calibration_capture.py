import cv2

PATH_LEFT = "test/90d_calib_left_{number}.png"     # путь, куда будем сохранять снятые кадры
PATH_RIGHT = "test/90d_calib_right_{number}.png"   #

import os

# Исправление для Wayland/Hyprland
os.environ["QT_QPA_PLATFORM"] = "xcb"

WIDTH, HEIGHT = 2560, 720   # разрешение стереокамеры
HALF_WIDTH = WIDTH // 2

camera = cv2.VideoCapture(2)    # захват камеры
camera.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
camera.set(1, 6000)

count = 0   # счетчик записанных изображений


while camera.isOpened():
    ret, frame = camera.read()
    if ret:
        imageLeft = frame[:, :HALF_WIDTH, :]    # делим кадр пополам
        imageRight = frame[:, HALF_WIDTH:, :]

        #cv2.imshow("imageLeft", imageLeft)
        #cv2.imshow("imageRight", imageRight)
        #cv2.imshow("frame", frame)
        cv2.imshow("frame", cv2.resize(frame, (1600, 450)))

    key = cv2.waitKey(30)
    if key == ord('q'):     # если нажато Q завершаем работу программы
        break
    elif (key == 0x20) and ret:  # если нажат пробел - сохраняем кадры
        print("Сохранение изображений: ")
        print("Левое: " + PATH_LEFT.format(number=count))
        print("Правое: " + PATH_RIGHT.format(number=count))
        cv2.imwrite(PATH_LEFT.format(number=count), imageLeft)
        cv2.imwrite(PATH_RIGHT.format(number=count), imageRight)

        count += 1

cv2.destroyAllWindows()

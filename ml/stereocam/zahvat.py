import cv2
import os

# Исправление для Wayland/Hyprland
os.environ["QT_QPA_PLATFORM"] = "xcb"

cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("Ошибка: Не удалось открыть камеру")
    exit()

# Устанавливаем разрешение для стерео камеры
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Нажмите 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Ошибка: Не удалось захватить кадр")
        break
    
    # Отображаем общее изображение со стерео камеры
    cv2.imshow('Stereo Camera', frame)
    
    # Выход при нажатии 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
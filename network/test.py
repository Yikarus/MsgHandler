import socket
from PIL import Image
import io
import cv2
import numpy as np
from pyorbbecsdk import Config
from pyorbbecsdk import OBError
from pyorbbecsdk import OBSensorType, OBFormat
from pyorbbecsdk import Pipeline, FrameSet
from pyorbbecsdk import VideoStreamProfile
from utils import frame_to_bgr_image

ESC_KEY = 27
def receive_image(sock):
    image_size = int.from_bytes(sock.recv(4), byteorder='big')  # 接收图像大小
    image_data = b''
    image_size = 640 * 360 * 3
    while len(image_data) < image_size:
        packet = sock.recv(image_size - len(image_data))
        if not packet:
            return None
        image_data += packet
    return image_data

def client_program():
    host = '127.0.0.1'  # 服务器的 IP 地址
    port = 12345  # 端口号必须与服务器相同
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    while True:
        try:
            image = receive_image(client_socket)
            if image is not None:
                height = 360
                width = 640
                image_data  = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
                cv2.imshow("Color Viewer", image_data)
                key = cv2.waitKey(1)  # 显示图像
            else:
                print("Failed to receive complete image.")
                break
        except KeyboardInterrupt:
            break

    client_socket.close()

if __name__ == '__main__':
    client_program()

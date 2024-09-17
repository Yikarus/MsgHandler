import socket
from PIL import Image
import io
import cv2
import numpy as np
import struct

ESC_KEY = 27
# def receive_image(sock):
#     image_size = b''
#     while len(image_size) < 8:
#         packet = sock.recv(8 - len(image_size))
#         if not packet:
#             return (None, None, None)
#         image_size += packet
#     height, width = struct.unpack('!II', image_size)
#     image_data = b''
#     image_size = height * width * 3
#     while len(image_data) < image_size:
#         packet = sock.recv(image_size - len(image_data))
#         if not packet:
#             return (None, None, None)
#         image_data += packet
#     return (height, width, image_data)

def receive_image(sock):
    image_size_buffer = b''
    while len(image_size_buffer) < 8:
        packet = sock.recv(8 - len(image_size_buffer))
        if not packet:
            return None
        image_size_buffer += packet
    print("image_size_buffer:", len(image_size_buffer))
    color_size, depth_size = struct.unpack('!II', image_size_buffer)
    print("recv color jpg size :", color_size)
    print("recv depth jpg size :", depth_size)
    color_data = b''
    while len(color_data) < color_size:
        packet = sock.recv(color_size - len(color_data))
        if not packet:
            return None
        color_data += packet
    depth_data = b''
    while len(depth_data) < depth_size:
        packet = sock.recv(depth_size - len(depth_data))
        if not packet:
            return None
        depth_data += packet
    return (color_data, depth_data)

def client_program():
    host = '192.168.1.5'  # 服务器的 IP 地址
    port = 12345  # 端口号必须与服务器相同
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    while True:
        try:
            color_image, depth_image = receive_image(client_socket)
            if color_image is not None:
                # image_data  = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
                jpg = cv2.imdecode(np.frombuffer(color_image, dtype=np.uint8), cv2.IMREAD_COLOR)
                cv2.imshow("Color Viewer", jpg)
                key = cv2.waitKey(1)  # 显示图像
            else:
                print("Failed to receive complete image.")
                break
            if depth_image is not None:
                # image_data  = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
                jpg = cv2.imdecode(np.frombuffer(depth_image, dtype=np.uint8), cv2.IMREAD_COLOR)
                cv2.imshow("Depth Viewer", jpg)
                key = cv2.waitKey(1)  # 显示图像
            else:
                print("Failed to receive complete image.")
                break
        except KeyboardInterrupt:
            break

    client_socket.close()

if __name__ == '__main__':
    client_program()

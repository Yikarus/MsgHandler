import socket
from PIL import Image
import io
import cv2
import numpy as np
import struct
import threading
from datetime import datetime


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
Take_picture = False
SAVE_PATH = "C:\\Users\\wangxin8\\source\\"

def receive_image(sock):
    image_size_buffer = b''
    while len(image_size_buffer) < 8:
        packet = sock.recv(8 - len(image_size_buffer))
        if not packet:
            return None
        image_size_buffer += packet
    # print("image_size_buffer:", len(image_size_buffer))
    color_size, depth_size = struct.unpack('!II', image_size_buffer)
    # print("recv color jpg size :", color_size)
    # print("recv depth jpg size :", depth_size)
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
    depth_image = np.frombuffer(depth_data, dtype=np.uint16)
    return (color_data, depth_image)

def client_program(sock):
    global Take_picture
    while True:
        try:
            color_image, depth_image = receive_image(client_socket)
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            if color_image is not None:
                # image_data  = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
                jpg = cv2.imdecode(np.frombuffer(color_image, dtype=np.uint8), cv2.IMREAD_COLOR)
                cv2.imshow("Color Viewer", jpg)
                if Take_picture:
                    RGB_PATH = SAVE_PATH + "RGB\\" + current_time + ".jpg"
                    print("taking to RGB, ", RGB_PATH)
                    cv2.imwrite(RGB_PATH, jpg)
                key = cv2.waitKey(1)  # 显示图像
            else:
                print("Failed to receive complete image.")
                break
            if depth_image is not None:
                # image_data  = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
                # jpg = cv2.imdecode(np.frombuffer(depth_image, dtype=np.uint8), cv2.IMREAD_COLOR)
                depth_image = depth_image.reshape((480, 848))
                if Take_picture:
                    Depth_PATH = SAVE_PATH + "Depth\\" + current_time + ".png"
                    print("taking to Depth, ", Depth_PATH)
                    cv2.imwrite(Depth_PATH, depth_image)
                # print("depth image:", depth_image.shape)
                depth_image = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                depth_image = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)
                cv2.imshow("Depth Viewer", depth_image)
                key = cv2.waitKey(1)  # 显示图像
            else:
                print("Failed to receive complete image.")
                break
            if Take_picture:
                Take_picture = False
        except KeyboardInterrupt:
            break

    client_socket.close()

if __name__ == '__main__':
    # global Take_picture
    host = '192.168.5.3'  # 服务器的 IP 地址
    port = 12345  # 端口号必须与服务器相同
    Take_picture = False
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client = threading.Thread(target = client_program, args = (client_socket,))
    client.start()
    while True:
        # 读取键盘输入
        user_input = input("请输入命令 (l 保存图片, exit 退出程序): ")
        if user_input.lower() == 'l':
            Take_picture = True
            print("Taking Photo...")
        elif user_input.lower() == 'exit':
            # 退出程序
            print("退出程序...")
            break
        else:
            # 如果输入既不是 'l' 也不是 'exit'，则提示无效输入
            print("无效的命令，请输入 'l' 或 'exit'。")
    client.join()

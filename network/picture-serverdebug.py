import socket
import time
from PIL import Image
import io

def send_image(sock, image_path):
    with open(image_path, 'rb') as file:
        image_data = file.read()
    sock.sendall(len(image_data).to_bytes(4, byteorder='big'))  # 发送图像大小
    sock.sendall(image_data)  # 发送图像数据

def server_program():
    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 12345  # 初始化端口号
    image_path = '/home/orangepi/Pictures/test.jpg'  # 图片路径
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on port {port}")

    try:
        while True:
            conn, address = server_socket.accept()
            print(f"Got connection from {address}")

            try:
                while True:
                    send_image(conn, image_path)
                    time.sleep(1)  # 等待1秒
            except BrokenPipeError:
                print("Client disconnected")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server_socket.close()

if __name__ == '__main__':
    server_program()
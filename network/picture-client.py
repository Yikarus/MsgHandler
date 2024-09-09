import socket
from PIL import Image
import io

def receive_image(sock):
    image_size = int.from_bytes(sock.recv(4), byteorder='big')  # 接收图像大小
    image_data = b''
    while len(image_data) < image_size:
        packet = sock.recv(image_size - len(image_data))
        if not packet:
            return None
        image_data += packet
    return Image.open(io.BytesIO(image_data))

def client_program():
    host = '127.0.0.1'  # 服务器的 IP 地址
    port = 12345  # 端口号必须与服务器相同
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    while True:
        image = receive_image(client_socket)
        if image is not None:
            image.show()  # 显示图像
        else:
            print("Failed to receive complete image.")
            break

    client_socket.close()

if __name__ == '__main__':
    client_program()
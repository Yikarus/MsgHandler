import cv2
import socket
import pickle
import struct
import time
def send_video_stream(sock, video_capture):
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        data = pickle.dumps(frame)
        message_size = struct.pack("L", len(data))
        sock.sendall(message_size + data)
        time.sleep(0.03)  # 控制帧率

def server_program():
    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 12345  # 初始化端口号
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on port {port}")

    video_capture = cv2.VideoCapture(0)  # 打开摄像头

    try:
        while True:
            conn, address = server_socket.accept()
            print(f"Got connection from {address}")
            send_video_stream(conn, video_capture)
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        video_capture.release()
        server_socket.close()

if __name__ == '__main__':
    server_program()